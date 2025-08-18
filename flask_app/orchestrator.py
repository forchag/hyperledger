#!/usr/bin/env python3
"""Gateway orchestrator for Raspberry Pi.

This module wires together the various services on a gateway.  It provides
configuration loading, pre‑flight validation, a minimal mesh monitor, packet
ingestion with bundling, a store‑and‑forward queue, a dummy Fabric client and
an HTTP server exposing health and Prometheus metrics.

The implementation here is intentionally lightweight; it is meant to act as a
reference and test harness rather than a production ready daemon.  Components
are structured for dependency injection so tests can exercise them in isolation
or as a whole.
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import threading
import time
from dataclasses import dataclass, field, asdict
from http import HTTPStatus
from pathlib import Path
from typing import Dict, List, Optional

from flask import Flask, Response
from prometheus_client import (
    CollectorRegistry,
    Counter,
    Gauge,
    Histogram,
    generate_latest,
)

log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

REQUIRED_KNOBS = [
    "UPLINK_PERIOD_MIN",
    "EVENT_COALESCE_SEC",
    "EVENT_RATE_LIMIT_PER_PI",
    "FABRIC_GATEWAY_URL",
    "FABRIC_CHANNEL",
    "FABRIC_CHAINCODE",
    "MESH_IFACE",
    "MESH_CHECK_INTERVAL_SEC",
    "STORE_MAX_AGE_HOURS",
    "STORE_DIR",
    "LOG_LEVEL",
]


@dataclass
class Settings:
    """Typed configuration settings for the gateway."""

    uplink_period_min: int = 15
    event_coalesce_sec: int = 30
    event_rate_limit_per_pi: int = 60
    fabric_gateway_url: str = "grpc://localhost:7051"
    fabric_channel: str = "mychannel"
    fabric_chaincode: str = "sensor"
    mesh_iface: str = "bat0"
    mesh_check_interval_sec: int = 30
    store_max_age_hours: int = 24
    store_dir: str = "./store"
    log_level: str = "INFO"
    dry_run: bool = False


class ConfigService:
    """Load configuration from env/CLI/file in a deterministic order."""

    def __init__(self, argv: Optional[List[str]] = None) -> None:
        self.argv = argv

    def load(self) -> Settings:
        parser = argparse.ArgumentParser(description="Gateway orchestrator")
        parser.add_argument("--config", default="config/gateway_config.yaml")
        parser.add_argument("--log-level")
        parser.add_argument("--dry-run", action="store_true")
        args = parser.parse_args(self.argv)

        cfg_path = Path(args.config)
        file_data: Dict[str, object] = {}
        if cfg_path.exists():
            try:
                with cfg_path.open() as fh:
                    file_data = json.load(fh)
            except Exception:
                try:
                    import yaml  # type: ignore

                    with cfg_path.open() as fh:
                        file_data = yaml.safe_load(fh) or {}
                except Exception:
                    log.warning("could not parse %s", cfg_path)
        else:
            cfg_path.parent.mkdir(parents=True, exist_ok=True)
            sample = {
                "UPLINK_PERIOD_MIN": 15,
                "EVENT_COALESCE_SEC": 30,
                "EVENT_RATE_LIMIT_PER_PI": 60,
                "FABRIC_GATEWAY_URL": "grpc://localhost:7051",
                "FABRIC_CHANNEL": "mychannel",
                "FABRIC_CHAINCODE": "sensor",
                "MESH_IFACE": "bat0",
                "MESH_CHECK_INTERVAL_SEC": 30,
                "STORE_MAX_AGE_HOURS": 24,
                "STORE_DIR": "./store",
                "LOG_LEVEL": "INFO",
            }
            with cfg_path.open("w") as fh:
                json.dump(sample, fh, indent=2)
            raise SystemExit(f"create/adjust {cfg_path} and rerun")

        values: Dict[str, object] = {}
        for key in REQUIRED_KNOBS:
            env_val = os.getenv(key)
            if env_val is not None:
                values[key] = env_val
                continue
            if getattr(args, key.lower(), None) is not None:
                values[key] = getattr(args, key.lower())
                continue
            if key in file_data:
                values[key] = file_data[key]

        missing = [k for k in REQUIRED_KNOBS if k not in values]
        if missing:
            raise SystemExit(f"missing config keys: {', '.join(missing)}")

        settings = Settings(
            uplink_period_min=int(values["UPLINK_PERIOD_MIN"]),
            event_coalesce_sec=int(values["EVENT_COALESCE_SEC"]),
            event_rate_limit_per_pi=int(values["EVENT_RATE_LIMIT_PER_PI"]),
            fabric_gateway_url=str(values["FABRIC_GATEWAY_URL"]),
            fabric_channel=str(values["FABRIC_CHANNEL"]),
            fabric_chaincode=str(values["FABRIC_CHAINCODE"]),
            mesh_iface=str(values["MESH_IFACE"]),
            mesh_check_interval_sec=int(values["MESH_CHECK_INTERVAL_SEC"]),
            store_max_age_hours=int(values["STORE_MAX_AGE_HOURS"]),
            store_dir=str(values["STORE_DIR"]),
            log_level=str(values["LOG_LEVEL"]),
            dry_run=bool(args.dry_run),
        )
        return settings


# ---------------------------------------------------------------------------
# Pre‑flight validation
# ---------------------------------------------------------------------------


def _check_json(path: Path, required: List[str]) -> Optional[str]:
    try:
        data = json.loads(path.read_text())
    except Exception:
        return f"{path} is not valid JSON"
    missing = [k for k in required if k not in data]
    if missing:
        return f"{path} missing keys: {', '.join(missing)}"
    return None


def preflight() -> None:
    """Validate that all required build artifacts exist."""

    errors: List[str] = []

    leaf_cfg = Path("devices/leaf-node/config/leaf_config.json")
    if not leaf_cfg.exists():
        leaf_cfg.parent.mkdir(parents=True, exist_ok=True)
        sample = {
            "device_id": "leaf01",
            "sensors": ["temp"],
            "sample_period_sec": 60,
            "uplink_period_sec": 300,
            "pi_targets": ["localhost"],
            "hmac_key": "changeme",
            "thresholds": {},
        }
        leaf_cfg.write_text(json.dumps(sample, indent=2))
        errors.append(f"created sample {leaf_cfg}; adjust and rerun")
    else:
        err = _check_json(
            leaf_cfg,
            [
                "device_id",
                "sensors",
                "sample_period_sec",
                "uplink_period_sec",
                "pi_targets",
                "hmac_key",
                "thresholds",
            ],
        )
        if err:
            errors.append(err)

    payload_doc = Path("devices/leaf-node/docs/payload.md")
    if not payload_doc.exists():
        payload_doc.parent.mkdir(parents=True, exist_ok=True)
        payload_doc.write_text("# Payload\n\nDocument payload keys here including optional crt:{m[],r[]}")
        errors.append(f"created placeholder {payload_doc}; document payload and rerun")

    seq_store = Path("devices/leaf-node/telemetry/seq_store")
    if not seq_store.exists():
        seq_store.parent.mkdir(parents=True, exist_ok=True)
        seq_store.write_text("0")
        errors.append(f"created stub {seq_store}; replace with real store")

    if errors:
        for e in errors:
            log.error("preflight: %s", e)
        raise SystemExit(1)
    log.info("preflight complete \u2705")


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------


@dataclass
class NormalizedReading:
    device_id: str
    seq: int
    window_id: str
    stats: Dict[str, float]
    last_ts: float
    sensor_set: List[str]
    urgent: bool = False
    residues_hash: Optional[str] = None
    sig_verified: bool = False


@dataclass
class IntervalBundle:
    window_id: str
    readings: List[NormalizedReading]
    started_at: float
    closes_at: float


@dataclass
class EventBundle:
    start: float
    end: float
    events: List[NormalizedReading]


# ---------------------------------------------------------------------------
# Metrics registry
# ---------------------------------------------------------------------------


REGISTRY = CollectorRegistry(auto_describe=True)
ingress_packets_total = Counter(
    "ingress_packets_total", "Total packets received", registry=REGISTRY
)
duplicates_total = Counter(
    "duplicates_total", "Duplicate payloads ignored", registry=REGISTRY
)
bundles_submitted_total = Counter(
    "bundles_submitted_total", "Bundles submitted", ["type"], registry=REGISTRY
)
submit_commit_seconds = Histogram(
    "submit_commit_seconds", "Submit to commit latency", registry=REGISTRY
)
mesh_neighbors_gauge = Gauge(
    "mesh_neighbors", "Number of BATMAN neighbors", registry=REGISTRY
)
store_backlog_files = Gauge(
    "store_backlog_files", "Store and forward backlog", registry=REGISTRY
)
events_rate_limited_total = Counter(
    "events_rate_limited_total", "Events dropped due to rate limiting", registry=REGISTRY
)


# ---------------------------------------------------------------------------
# Mesh monitor
# ---------------------------------------------------------------------------


class MeshMonitor(threading.Thread):
    """Very small BATMAN neighbor monitor."""

    def __init__(self, settings: Settings) -> None:
        super().__init__(daemon=True)
        self.settings = settings
        self._stop = threading.Event()
        self.neighbors: List[str] = []

    def run(self) -> None:  # pragma: no cover - monitoring loop
        while not self._stop.wait(self.settings.mesh_check_interval_sec):
            self.check()

    def stop(self) -> None:
        self._stop.set()

    def check(self) -> None:
        cmd = f"batctl n {self.settings.mesh_iface} 2>/dev/null"
        try:
            out = os.popen(cmd).read().strip().splitlines()
            self.neighbors = [line.split()[0] for line in out if line]
        except Exception:
            self.neighbors = []
        mesh_neighbors_gauge.set(len(self.neighbors))

    def healthy(self) -> bool:
        return bool(self.neighbors)


# ---------------------------------------------------------------------------
# Fabric client (dummy)
# ---------------------------------------------------------------------------


class FabricClient:
    """Very small stub of a Fabric client used for tests."""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.connected = True
        self.last_commit_time: Optional[float] = None
        self.submits: List[Dict] = []

    def submit_reading_bundle(self, bundle: IntervalBundle) -> None:
        self._submit(bundle, "interval")

    def submit_event_bundle(self, bundle: EventBundle) -> None:
        self._submit(bundle, "event")

    def _submit(self, bundle, btype: str) -> None:
        start = time.time()
        if not self.connected or self.settings.dry_run:
            raise RuntimeError("fabric unavailable")
        # simulate network delay
        time.sleep(0.01)
        self.last_commit_time = time.time()
        self.submits.append({"type": btype, "bundle": bundle})
        bundles_submitted_total.labels(type=btype).inc()
        submit_commit_seconds.observe(self.last_commit_time - start)


# ---------------------------------------------------------------------------
# Store and forward
# ---------------------------------------------------------------------------


class StoreAndForward:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.dir = Path(settings.store_dir)
        self.dir.mkdir(parents=True, exist_ok=True)
        self.queue: List[Dict] = []

    def persist(self, bundle: Dict) -> None:
        ts = int(time.time()*1000)
        path = self.dir / f"bundle_{ts}.json"
        data = bundle
        if not isinstance(bundle, dict):
            try:
                data = asdict(bundle)
            except Exception:
                data = dict(bundle)  # type: ignore
        path.write_text(json.dumps(data))
        self.queue.append({"path": path, "bundle": bundle})
        store_backlog_files.set(len(self.queue))

    def flush(self, client: FabricClient) -> None:
        remaining: List[Dict] = []
        for item in list(self.queue):
            bundle = item["bundle"]
            try:
                if isinstance(bundle, EventBundle) or (isinstance(bundle, dict) and bundle.get("type") == "event"):
                    client.submit_event_bundle(bundle)  # type: ignore[arg-type]
                else:
                    client.submit_reading_bundle(bundle)  # type: ignore[arg-type]
                item["path"].unlink(missing_ok=True)
            except Exception:
                remaining.append(item)
        self.queue = remaining
        store_backlog_files.set(len(self.queue))


# ---------------------------------------------------------------------------
# Bundler & Ingress
# ---------------------------------------------------------------------------


class Bundler:
    def __init__(self, settings: Settings, store: StoreAndForward, client: FabricClient):
        self.settings = settings
        self.store = store
        self.client = client
        self.readings: Dict[str, List[NormalizedReading]] = {}
        self.event_buffer: List[NormalizedReading] = []
        self.event_window_end = 0.0
        self.event_rate_count = 0
        self.seen: Dict[str, int] = {}

    def ingest(self, reading: NormalizedReading) -> None:
        ingress_packets_total.inc()
        key = f"{reading.device_id}:{reading.seq}"
        if key in self.seen:
            duplicates_total.inc()
            return
        self.seen[key] = 1
        if reading.urgent:
            self._handle_event(reading)
        else:
            self._handle_interval(reading)

    # interval
    def _handle_interval(self, reading: NormalizedReading) -> None:
        window = reading.window_id
        self.readings.setdefault(window, []).append(reading)

    # events
    def _handle_event(self, reading: NormalizedReading) -> None:
        now = time.time()
        if self.event_rate_count >= self.settings.event_rate_limit_per_pi:
            events_rate_limited_total.inc()
            return
        if now > self.event_window_end:
            self.event_buffer = []
            self.event_window_end = now + self.settings.event_coalesce_sec
        self.event_buffer.append(reading)
        self.event_rate_count += 1

    def close_event_window(self) -> Optional[EventBundle]:
        if self.event_buffer and time.time() > self.event_window_end:
            bundle = EventBundle(
                start=self.event_window_end - self.settings.event_coalesce_sec,
                end=self.event_window_end,
                events=list(self.event_buffer),
            )
            self.event_buffer = []
            self.event_rate_count = 0
            return bundle
        return None

    def pop_closed_windows(self) -> List[IntervalBundle]:
        now = time.time()
        bundles: List[IntervalBundle] = []
        for window_id, readings in list(self.readings.items()):
            start, end = map(int, window_id.split("-"))
            if now >= end:
                bundle = IntervalBundle(
                    window_id=window_id,
                    readings=readings,
                    started_at=start,
                    closes_at=end,
                )
                bundles.append(bundle)
                del self.readings[window_id]
        return bundles

    def submit_bundle(self, bundle) -> None:
        try:
            if isinstance(bundle, EventBundle):
                self.client.submit_event_bundle(bundle)
            else:
                self.client.submit_reading_bundle(bundle)
        except Exception:
            self.store.persist(bundle)

    def flush_store(self) -> None:
        self.store.flush(self.client)


# ---------------------------------------------------------------------------
# Scheduler
# ---------------------------------------------------------------------------


class Scheduler(threading.Thread):
    def __init__(self, settings: Settings, bundler: Bundler):
        super().__init__(daemon=True)
        self.settings = settings
        self.bundler = bundler
        self._stop = threading.Event()

    def run(self) -> None:  # pragma: no cover - thread loop
        period = self.settings.uplink_period_min * 60
        while not self._stop.wait(1):
            # event bundles
            ev = self.bundler.close_event_window()
            if ev:
                self.bundler.submit_bundle(ev)
            # interval bundles
            for bundle in self.bundler.pop_closed_windows():
                self.bundler.submit_bundle(bundle)
            # periodic flush
            if time.time() % period < 1:
                for bundle in self.bundler.pop_closed_windows():
                    self.bundler.submit_bundle(bundle)
            # store and forward retry
            self.bundler.flush_store()

    def stop(self) -> None:
        self._stop.set()


# ---------------------------------------------------------------------------
# Ingress service
# ---------------------------------------------------------------------------


class IngressService:
    def __init__(self, bundler: Bundler, registry: Dict[str, str]):
        self.bundler = bundler
        self.registry = registry  # device_id -> hmac_key

    def ingest(self, packet: Dict) -> None:
        dev = packet["device_id"]
        seq = int(packet["seq"])
        key = self.registry.get(dev)
        body = {k: packet[k] for k in packet if k != "sig"}
        payload = json.dumps(body, sort_keys=True).encode()
        expected = hmac_sha256(key, payload)
        if packet.get("sig") != expected:
            raise ValueError("bad signature")
        reading = NormalizedReading(
            device_id=dev,
            seq=seq,
            window_id=packet.get("window_id", derive_window(seq, self.bundler.settings)).replace(":", "-"),
            stats=packet.get("stats", {}),
            last_ts=packet.get("last_ts", time.time()),
            sensor_set=packet.get("sensor_set", []),
            urgent=bool(packet.get("urgent")),
            sig_verified=True,
        )
        self.bundler.ingest(reading)


def derive_window(seq: int, settings: Settings) -> str:
    period = settings.uplink_period_min * 60
    start = int(time.time() // period * period)
    end = start + period
    return f"{start}-{end}"


def hmac_sha256(key: str, payload: bytes) -> str:
    import hmac, hashlib

    return hmac.new(key.encode(), payload, hashlib.sha256).hexdigest()


# ---------------------------------------------------------------------------
# Health server
# ---------------------------------------------------------------------------


class HealthServer(threading.Thread):
    def __init__(self, settings: Settings, mesh: MeshMonitor, client: FabricClient):
        super().__init__(daemon=True)
        self.settings = settings
        self.mesh = mesh
        self.client = client
        self.app = Flask(__name__)
        self._setup_routes()

    def _setup_routes(self) -> None:
        app = self.app

        @app.route("/metrics")
        def metrics() -> Response:
            return Response(generate_latest(REGISTRY), mimetype="text/plain")

        @app.route("/healthz")
        def healthz() -> Response:
            ok = self.mesh.healthy()
            status = HTTPStatus.OK if ok else HTTPStatus.SERVICE_UNAVAILABLE
            return Response(b"OK" if ok else b"degraded", status=status)

        @app.route("/readyz")
        def readyz() -> Response:
            ok = bool(self.client.last_commit_time and time.time() - self.client.last_commit_time < 300)
            status = HTTPStatus.OK if ok else HTTPStatus.SERVICE_UNAVAILABLE
            return Response(b"READY" if ok else b"stale", status=status)

    def run(self) -> None:  # pragma: no cover - server loop
        self.app.run(host="0.0.0.0", port=9102, threaded=True)


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------


def main(argv: Optional[List[str]] = None) -> None:
    cfg = ConfigService(argv).load()
    logging.basicConfig(level=getattr(logging, cfg.log_level.upper(), logging.INFO))
    log.info("config: %s", cfg)
    preflight()

    mesh = MeshMonitor(cfg)
    client = FabricClient(cfg)
    store = StoreAndForward(cfg)
    bundler = Bundler(cfg, store, client)

    # registry derived from leaf config
    leaf_cfg = json.loads(Path("devices/leaf-node/config/leaf_config.json").read_text())
    registry = {leaf_cfg["device_id"]: leaf_cfg.get("hmac_key", "")}
    ingress = IngressService(bundler, registry)

    scheduler = Scheduler(cfg, bundler)
    health = HealthServer(cfg, mesh, client)

    mesh.start()
    scheduler.start()
    health.start()

    try:
        while True:
            time.sleep(3600)
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":  # pragma: no cover - manual execution
    main()
