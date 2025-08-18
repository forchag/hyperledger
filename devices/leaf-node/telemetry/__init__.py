"""Telemetry utilities for ESP32 leaf nodes."""

from .ring_buffer import RingBuffer
from .seq_store import SeqStore
from .summary_store import SummaryStore
from .window import WindowBatcher
from .event_detector import EventDetector

try:  # Optional CRT payload support
    from .payload import build_payload, crt_encoder
except Exception:  # pragma: no cover - fallback when CRT deps missing
    build_payload = crt_encoder = None

__all__ = [
    "RingBuffer",
    "SeqStore",
    "SummaryStore",
    "WindowBatcher",
    "build_payload",
    "crt_encoder",
    "EventDetector",
]
