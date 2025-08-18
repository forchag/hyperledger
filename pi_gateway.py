"""Pi gateway ingestion and bundling utilities.

This module extends the reference gateway to handle signed ESP32 payloads and
aggregate them into bundles for submission to Hyperledger Fabric.  Key
capabilities include:

* Signature verification using per device RSA public keys.
* De‑duplication based on ``(device_id, seq)`` pairs.
* Interval based bundling keyed by ``window_id``.
* Promotion of urgent payloads to separate event bundles that override the
  normal schedule (coalescing alerts over a short window).
* Basic store‑and‑forward when the orderer is unreachable.
* Metric logging for bundle size, commit latency and event counts.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
import json
import logging
import time
from typing import Dict, List, Optional, Protocol, Tuple
import threading

from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding, rsa


log = logging.getLogger(__name__)


@dataclass
class DeviceRecord:
    """Registry entry for a sensor device."""

    owner: str
    sensors: List[str]
    keys: Dict[str, rsa.RSAPublicKey]
    active: str


class DeviceRegistry:
    """In-memory mapping of device metadata and keys."""

    def __init__(self) -> None:
        self.devices: Dict[str, DeviceRecord] = {}

    def add_device(
        self,
        device_id: str,
        owner: str,
        sensors: List[str],
        key_id: str,
        key: rsa.RSAPublicKey,
    ) -> None:
        self.devices[device_id] = DeviceRecord(owner, sensors, {key_id: key}, key_id)

    def rotate_key(self, device_id: str, key_id: str, key: rsa.RSAPublicKey) -> None:
        dev = self.devices[device_id]
        dev.keys[key_id] = key
        dev.active = key_id

    def get_active_key(self, device_id: str) -> Optional[rsa.RSAPublicKey]:
        dev = self.devices.get(device_id)
        if not dev:
            return None
        return dev.keys.get(dev.active)

    def get_active_key_id(self, device_id: str) -> Optional[str]:
        dev = self.devices.get(device_id)
        if not dev:
            return None
        return dev.active

    def get_key(self, device_id: str, key_id: str) -> Optional[rsa.RSAPublicKey]:
        dev = self.devices.get(device_id)
        if not dev:
            return None
        return dev.keys.get(key_id)


class BlockchainClient(Protocol):
    """Minimal protocol a blockchain client must satisfy."""

    def submit(self, bundle: Dict) -> str:  # pragma: no cover - interface stub
        """Submit a bundle to the blockchain ledger and return a transaction id."""

    def wait_for_commit(self, tx_id: str) -> None:  # pragma: no cover - interface stub
        """Block until ``tx_id`` is committed and the relevant key is readable."""


# ---------------------------------------------------------------------------
# Helpers


def _serialize_for_sig(packet: Dict) -> bytes:
    """Return canonical JSON bytes of ``packet`` minus the ``sig`` field."""
    data = {k: packet[k] for k in packet if k != "sig"}
    return json.dumps(data, sort_keys=True, separators=(",", ":")).encode()


def verify_signature(packet: Dict, pub: rsa.RSAPublicKey) -> bool:
    """Verify RSA signature on a packet."""

    try:
        signature = bytes.fromhex(packet["sig"])
    except Exception:
        return False
    payload = _serialize_for_sig(packet)
    try:
        pub.verify(signature, payload, padding.PKCS1v15(), hashes.SHA256())
        return True
    except Exception:
        return False


# ---------------------------------------------------------------------------
# Gateway


@dataclass
class PiGateway:
    """Validate, bundle and forward ESP32 payloads."""

    client: BlockchainClient
    registry: DeviceRegistry
    interval_minutes: int = 60

    bundles: Dict[Tuple[int, int], List[Dict]] = field(default_factory=dict)
    last_seq: Dict[str, int] = field(default_factory=dict)
    pending: List[Dict] = field(default_factory=list)

    def __post_init__(self) -> None:
        if not 30 <= self.interval_minutes <= 120:
            raise ValueError("interval_minutes must be between 30 and 120")
        # Convert to seconds for internal use
        self.interval = self.interval_minutes * 60

    # ------------------------------------------------------------------
    # Ingestion

    def validate(self, packet: Dict) -> bool:
        """Verify presence of required fields, signature and sequence order."""

        required = {"device_id", "seq", "sig", "key_id"}
        if not required.issubset(packet):
            return False
        dev = packet["device_id"]
        key_id = packet["key_id"]
        record = self.registry.devices.get(dev)
        if not record or record.active != key_id:
            return False
        pub = record.keys.get(key_id)
        if not pub:
            return False
        if packet["seq"] <= self.last_seq.get(dev, -1):
            # Duplicate or out‑of‑order packet
            return False
        if not verify_signature(packet, pub):
            return False
        return True

    def handle_packet(self, packet: Dict) -> None:
        """Process an incoming ESP32 payload."""

        if not self.validate(packet):
            raise ValueError("invalid packet")
        if "residues_hash" not in packet:
            blob = json.dumps(packet.get("payload", {}), sort_keys=True, separators=(",", ":")).encode()
            packet["residues_hash"] = hashlib.sha256(blob).hexdigest()
        dev = packet["device_id"]
        self.last_seq[dev] = packet["seq"]

        if packet.get("urgent"):
            self._handle_urgent(packet)
        else:
            self._handle_normal(packet)

        # Resubmit any pending bundles opportunistically
        if self.pending:
            self.flush_pending()

    # ------------------------------------------------------------------
    # Normal bundling

    def _handle_normal(self, packet: Dict) -> None:
        window_id = tuple(packet.get("window_id", self._derive_window(packet)))
        self.bundles.setdefault(window_id, []).append(packet)

    def _derive_window(self, packet: Dict) -> Tuple[int, int]:
        ts = int(packet.get("last_ts", time.time()))
        start = ts - (ts % self.interval)
        return start, start + self.interval

    # ------------------------------------------------------------------
    # Urgent events

    def _handle_urgent(self, packet: Dict) -> None:
        now = time.time()
        bundle = {
            "type": "event",
            "events": [packet],
            "start": now,
            "end": now,
        }
        self._submit_bundle(bundle)

    # ------------------------------------------------------------------
    # Flushing

    def flush_ready(self) -> None:
        """Flush bundles whose window has closed."""

        now = time.time()
        ready = [wid for wid in self.bundles if wid[1] <= now]
        for wid in ready:
            packets = self.bundles.pop(wid)
            bundle = {"window_id": wid, "packets": packets}
            self._submit_bundle(bundle)

    def flush_all(self) -> None:
        """Flush all buffered bundles and events."""

        for wid, packets in list(self.bundles.items()):
            bundle = {"window_id": wid, "packets": packets}
            self._submit_bundle(bundle)
        self.bundles.clear()

    # ------------------------------------------------------------------
    # Store and forward

    def _submit_bundle(self, bundle: Dict) -> None:
        start = time.time()
        try:
            tx_id = self.client.submit(bundle)
            self.client.wait_for_commit(tx_id)
            latency = time.time() - start
            size = len(bundle.get("packets", bundle.get("events", [])))
            log.info(
                "bundle committed size=%d latency=%.3f type=%s",
                size,
                latency,
                bundle.get("type", "data"),
            )
        except Exception as exc:  # pragma: no cover - network errors
            log.warning("store-and-forward bundle: %s", exc)
            self.pending.append(bundle)

    def flush_pending(self) -> None:
        if not self.pending:
            return
        bundles = list(self.pending)
        self.pending.clear()
        for b in bundles:
            self._submit_bundle(b)

    def run_scheduler(self, stop: threading.Event) -> None:
        """Periodically flush ready bundles until ``stop`` is set."""
        while not stop.wait(self.interval):
            self.flush_ready()


__all__ = ["PiGateway", "verify_signature"]

