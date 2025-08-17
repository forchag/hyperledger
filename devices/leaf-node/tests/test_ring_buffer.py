import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))
from telemetry.ring_buffer import RingBuffer


def test_ring_buffer_capacity_overwrite():
    buf = RingBuffer(capacity=5)
    for i in range(7):
        buf.append(i)
    assert len(buf) == 5
    assert list(buf) == [2, 3, 4, 5, 6]


def test_ring_buffer_default_capacity():
    buf = RingBuffer()
    assert buf.capacity >= 180
    for i in range(buf.capacity):
        buf.append(i)
    assert len(buf) == buf.capacity
