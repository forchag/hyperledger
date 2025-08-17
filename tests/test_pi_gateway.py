
import time

from pi_gateway import PiGateway, compute_checksum


class DummyClient:
    def __init__(self) -> None:
        self.submitted = []

    def submit(self, packet):  # pragma: no cover - simple append
        self.submitted.append(packet)


def make_packet(anomaly: bool = False):
    payload = {"temperature": 20.0}
    packet = {
        "source_id": "n1",
        "timestamp": time.time(),
        "payload": payload,
        "anomaly": anomaly,
    }
    packet["checksum"] = compute_checksum("n1", packet["timestamp"], payload)
    return packet


def test_normal_packets_buffered():
    client = DummyClient()
    gw = PiGateway(client)
    pkt = make_packet(anomaly=False)
    gw.handle_packet(pkt)
    assert gw.buffer == [pkt]
    assert client.submitted == []


def test_anomaly_submitted_immediately():
    client = DummyClient()
    gw = PiGateway(client)
    pkt = make_packet(anomaly=True)
    gw.handle_packet(pkt)
    assert gw.buffer == []
    assert client.submitted == [pkt]


def test_flush_buffer_sends_all():
    client = DummyClient()
    gw = PiGateway(client)
    pkt1 = make_packet()
    pkt2 = make_packet()
    gw.handle_packet(pkt1)
    gw.handle_packet(pkt2)
    gw.flush_buffer()
    assert gw.buffer == []
    assert client.submitted == [pkt1, pkt2]
