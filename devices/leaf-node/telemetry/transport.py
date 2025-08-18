from __future__ import annotations

import json
import time
import hmac
import hashlib
from typing import Any, Dict, List, Optional

import requests

try:  # Optional Ed25519 support
    from nacl.signing import SigningKey  # type: ignore
except Exception:  # pragma: no cover - library may be missing
    SigningKey = None  # type: ignore


class PiClient:
    """Transmit signed payloads to Raspberry Pi gateways with failover.

    The client performs a nonce-based handshake with the current target Pi
    before sending data.  Payloads are signed using HMAC by default or
    Ed25519 when a private key is supplied.  Failures increment a counter and
    after ``max_failures`` the client switches to the next Pi in
    ``targets``.
    """

    def __init__(
        self,
        targets: List[str],
        *,
        hmac_key: Optional[bytes] = None,
        ed25519_sk: Optional[bytes] = None,
        max_failures: int = 3,
    ) -> None:
        if not targets:
            raise ValueError("at least one target required")
        self.targets = targets
        self.session = requests.Session()
        self.max_failures = max_failures
        self._current = 0
        self._failures = 0
        self.buffer: List[Dict[str, Any]] = []
        self.last_uplink: Optional[float] = None
        self.seq = 0
        self.event_count = 0

        if ed25519_sk and SigningKey:
            self._signer = SigningKey(ed25519_sk)
            self.kid = "ed25519"
            self._hmac_key = None
        elif hmac_key is not None:
            self._signer = None
            self._hmac_key = hmac_key
            self.kid = "hmac"
        else:
            raise ValueError("hmac_key or ed25519_sk required")

    # ------------------------------------------------------------------
    # Helper methods
    def _sign(self, data: bytes) -> str:
        if self._signer is not None:
            return self._signer.sign(data).signature.hex()
        assert self._hmac_key is not None
        return hmac.new(self._hmac_key, data, hashlib.sha256).hexdigest()

    def _advance_target(self) -> None:
        if len(self.targets) > 1:
            self._current = (self._current + 1) % len(self.targets)
        self._failures = 0

    # ------------------------------------------------------------------
    # Handshake + transmit
    def _handshake(self) -> bool:
        url = self.targets[self._current]
        try:
            r = self.session.get(f"{url}/handshake", timeout=5)
            r.raise_for_status()
            nonce = r.json()["nonce"]
            sig = self._sign(nonce.encode())
            r2 = self.session.post(
                f"{url}/handshake",
                json={"nonce": nonce, "sig": sig, "kid": self.kid},
                timeout=5,
            )
            r2.raise_for_status()
            self._failures = 0
            return True
        except Exception:
            self._failures += 1
            if self._failures >= self.max_failures:
                self._advance_target()
            return False

    def _post(self, payload: Dict[str, Any]) -> bool:
        url = self.targets[self._current]
        try:
            self.session.post(f"{url}/ingest", json=payload, timeout=5)
            self.last_uplink = time.time()
            self._failures = 0
            return True
        except Exception:
            self._failures += 1
            if self._failures >= self.max_failures:
                self._advance_target()
            return False

    # ------------------------------------------------------------------
    def send(self, payload: Dict[str, Any]) -> None:
        """Sign and transmit ``payload`` to the current Pi."""
        self.seq += 1
        payload["seq"] = self.seq
        if payload.get("urgent"):
            self.event_count += 1
        body = json.dumps(payload, separators=(",", ":")).encode()
        payload["sig"] = self._sign(body)
        payload["kid"] = self.kid

        if not self._handshake() or not self._post(payload):
            self.buffer.append(payload)

    def flush(self) -> None:
        """Attempt to send any buffered payloads."""
        if not self.buffer:
            return
        queued = self.buffer[:]
        self.buffer.clear()
        for pkt in queued:
            self.send(pkt)
            if pkt in self.buffer:  # still failed, stop to avoid busy loop
                break

    # ------------------------------------------------------------------
    def status(self) -> Dict[str, Any]:
        """Return current health metrics."""
        return {
            "buffer_depth": len(self.buffer),
            "last_uplink": self.last_uplink,
            "seq": self.seq,
            "event_count": self.event_count,
        }


# ----------------------------------------------------------------------
# Debug web application


def create_debug_app(client: PiClient):
    """Return a minimal Flask app exposing ``/health`` and ``/status``."""
    from flask import Flask, jsonify

    app = Flask(__name__)

    @app.route("/health")
    def health():  # pragma: no cover - simple JSON
        return jsonify({"status": "ok"})

    @app.route("/status")
    def status():  # pragma: no cover - simple JSON
        return jsonify(client.status())

    return app


__all__ = ["PiClient", "create_debug_app"]
