"""Tests for the enhanced PiGateway."""

import json
import os
import sys
import time

from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding, rsa

# Ensure repository root on path for direct test execution
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from pi_gateway import PiGateway, DeviceRegistry


def sign_packet(packet: dict, key) -> str:
    data = {k: packet[k] for k in packet if k != "sig"}
    payload = json.dumps(data, sort_keys=True, separators=(",", ":")).encode()
    sig = key.sign(payload, padding.PKCS1v15(), hashes.SHA256())
    return sig.hex()


class DummyClient:
    def __init__(self):
        self.submitted = []
        self.tx = 0

    def submit(self, bundle):  # pragma: no cover - simple append
        self.tx += 1
        self.submitted.append(bundle)
        return f"tx{self.tx}"

    def wait_for_commit(self, tx_id):  # pragma: no cover - no-op
        pass


def make_packet(key, seq=1, urgent=False, window=None, key_id="k1"):
    now = int(time.time())
    window_id = window or [now - 60, now]
    pkt = {
        "device_id": "n1",
        "seq": seq,
        "window_id": window_id,
        "payload": {"temperature": 20.0},
        "last_ts": now,
        "urgent": urgent,
        "key_id": key_id,
    }
    pkt["sig"] = sign_packet(pkt, key)
    return pkt


def test_dedupe_and_bundling():
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    client = DummyClient()
    reg = DeviceRegistry()
    reg.add_device("n1", "owner", [], "k1", key.public_key())
    gw = PiGateway(client, reg)

    pkt1 = make_packet(key, seq=1)
    pkt2 = make_packet(key, seq=1)  # duplicate seq
    gw.handle_packet(pkt1)
    # duplicate should raise ValueError
    try:
        gw.handle_packet(pkt2)
    except ValueError:
        pass

    gw.flush_all()
    assert len(client.submitted) == 1
    bundle = client.submitted[0]
    assert bundle["packets"] == [pkt1]


def test_urgent_events_promoted():
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    client = DummyClient()
    reg = DeviceRegistry()
    reg.add_device("n1", "owner", [], "k1", key.public_key())
    gw = PiGateway(client, reg)

    pkt = make_packet(key, seq=1, urgent=True)
    gw.handle_packet(pkt)

    assert len(client.submitted) == 1
    bundle = client.submitted[0]
    assert bundle["type"] == "event"
    assert pkt in bundle["events"]


def test_store_and_forward():
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)

    class FlakyClient(DummyClient):
        def __init__(self):
            super().__init__()
            self.fail = True

        def submit(self, bundle):
            if self.fail:
                self.fail = False
                raise ConnectionError("orderer down")
            return super().submit(bundle)

    client = FlakyClient()
    reg = DeviceRegistry()
    reg.add_device("n1", "owner", [], "k1", key.public_key())
    gw = PiGateway(client, reg)

    pkt = make_packet(key)
    gw.handle_packet(pkt)
    gw.flush_all()  # first submission fails
    assert client.submitted == []
    gw.flush_pending()  # retry succeeds
    assert len(client.submitted) == 1


def test_spoof_and_key_rotation():
    key1 = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    key2 = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    client = DummyClient()
    reg = DeviceRegistry()
    reg.add_device("n1", "owner", [], "k1", key1.public_key())
    gw = PiGateway(client, reg)

    pkt1 = make_packet(key1, seq=1, key_id="k1")
    gw.handle_packet(pkt1)

    spoof = make_packet(key2, seq=2, key_id="k1")
    try:
        gw.handle_packet(spoof)
    except ValueError:
        pass

    reg.rotate_key("n1", "k2", key2.public_key())
    pkt2 = make_packet(key2, seq=2, key_id="k2")
    gw.handle_packet(pkt2)

    gw.flush_all()
    assert len(client.submitted) == 1
    bundle = client.submitted[0]
    assert bundle["packets"] == [pkt1, pkt2]

