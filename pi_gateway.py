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
import json
import logging
import time
from math import floor
from typing import Dict, List, Protocol, Tuple

from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding, rsa


log = logging.getLogger(__name__)


class BlockchainClient(Protocol):
    """Minimal protocol a blockchain client must satisfy."""

    def submit(self, bundle: Dict) -> None:  # pragma: no cover - interface stub
        """Submit a bundle to the blockchain ledger."""


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
    public_keys: Dict[str, rsa.RSAPublicKey]
    interval: int = 60

    bundles: Dict[Tuple[int, int], List[Dict]] = field(default_factory=dict)
    event_bundle: List[Dict] = field(default_factory=list)
    event_start: float | None = None
    last_seq: Dict[str, int] = field(default_factory=dict)
    pending: List[Dict] = field(default_factory=list)

    # ------------------------------------------------------------------
    # Ingestion

    def validate(self, packet: Dict) -> bool:
        """Verify presence of required fields, signature and sequence order."""

        required = {"device_id", "seq", "sig"}
        if not required.issubset(packet):
            return False
        dev = packet["device_id"]
        if dev not in self.public_keys:
            return False
        if packet["seq"] <= self.last_seq.get(dev, -1):
            # Duplicate or out‑of‑order packet
            return False
        if not verify_signature(packet, self.public_keys[dev]):
            return False
        return True

    def handle_packet(self, packet: Dict) -> None:
        """Process an incoming ESP32 payload."""

        if not self.validate(packet):
            raise ValueError("invalid packet")
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
        if not self.event_bundle:
            self.event_start = now
        self.event_bundle.append(packet)
        # Flush after 60s of accumulation
        if self.event_start and now - self.event_start >= 60:
            self.flush_event_bundle()

    def flush_event_bundle(self, force: bool = False) -> None:
        if not self.event_bundle:
            return
        now = time.time()
        if not force and self.event_start and now - self.event_start < 60:
            return
        bundle = {
            "type": "event",
            "events": list(self.event_bundle),
            "start": self.event_start,
            "end": now,
        }
        self.event_bundle.clear()
        self.event_start = None
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
        self.flush_event_bundle(force=True)

    # ------------------------------------------------------------------
    # Store and forward

    def _submit_bundle(self, bundle: Dict) -> None:
        start = time.time()
        try:
            self.client.submit(bundle)
            latency = time.time() - start
            size = len(bundle.get("packets", bundle.get("events", [])))
            log.info(
                "bundle committed size=%d latency=%.3f type=%s", size, latency, bundle.get("type", "data")
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


__all__ = ["PiGateway", "verify_signature"]

