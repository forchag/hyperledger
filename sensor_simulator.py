import json
import random
import sys
import threading
import time
from datetime import datetime
from pathlib import Path
import math

import os
from urllib.parse import urljoin

import requests
from requests.exceptions import SSLError

# Base URL of the running Flask application. Defaults to the local
# development server but can be overridden via the ``SIMULATOR_URL``
# environment variable so the simulator can target remote instances.
# Using the explicit loopback address avoids hostname mismatches when the
# development TLS certificate lacks a ``localhost`` subject.
BASE_URL = os.environ.get("SIMULATOR_URL", "https://127.0.0.1:8443")

# Path to a certificate authority bundle used to verify TLS connections.  When
# ``SIMULATOR_CERT`` is provided the path is passed directly to ``requests`` so
# self-signed development certificates can be trusted without globally
# disabling verification.  Otherwise verification can be toggled via the
# ``SIMULATOR_VERIFY`` flag.
_CERT_PATH = os.environ.get("SIMULATOR_CERT")

# Whether to verify TLS certificates when contacting the backend.  The value is
# either the CA bundle path or a boolean depending on the environment.
VERIFY = _CERT_PATH or os.environ.get("SIMULATOR_VERIFY", "true").lower() != "false"

GPIO_PINS = [4, 17, 27, 22, 5, 6, 13, 19, 26, 18, 23, 24, 25, 12, 16, 20, 21]

# Common sensor set used when none are specified for a node.  Providing a
# sensible default keeps the simulator resilient to sparse configurations and
# avoids ``N/A`` values in the web interface.
DEFAULT_SENSORS = ["dht22", "light", "ph", "soil", "water"]

# Directory used to persist per-device sequence numbers.  The location can be
# overridden via ``SIMULATOR_STATE_DIR`` so tests or multiple simulator
# instances do not collide.  Each device gets a small file containing the last
# sequence number that was transmitted.
STATE_DIR = Path(os.environ.get("SIMULATOR_STATE_DIR", "simulator_state"))

# Keep track of devices that have already been announced during this simulator
# run.  This prevents duplicate registration requests when threads restart or
# multiple components attempt to announce the same sensor.
ANNOUNCED = set()


# Optional per-sensor profile configuration.  Profiles allow the simulator to
# generate more realistic time series data by combining a baseline, variance,
# diurnal drift, and occasional spikes.  Parameters can be adjusted at runtime
# by editing ``sensor_profiles.json`` (or YAML) without restarting the
# simulator.
PROFILE_PATH = Path(os.environ.get("SENSOR_PROFILE_CONFIG", "sensor_profiles.json"))
_PROFILE_CACHE = {}
_PROFILE_MTIME = 0.0

# Default metric characteristics used when a sensor lacks explicit profile
# configuration.  Values roughly mirror the ranges previously produced by the
# flat ``random.uniform`` calls but allow drift and spikes to be layered on
# top.
DEFAULT_METRICS = {
    "temperature": {"baseline": 22, "variance": 5, "drift": 3},
    "humidity": {"baseline": 60, "variance": 10, "drift": 5},
    "soil_moisture": {"baseline": 40, "variance": 5, "drift": 2},
    "ph": {"baseline": 6.5, "variance": 0.3},
    "light": {"baseline": 500, "variance": 100, "drift": 200},
    "water_level": {"baseline": 50, "variance": 10},
}


def _load_profiles() -> None:
    """Reload the profile configuration if the file has changed."""

    global _PROFILE_CACHE, _PROFILE_MTIME
    try:
        mtime = PROFILE_PATH.stat().st_mtime
    except FileNotFoundError:
        _PROFILE_CACHE = {}
        _PROFILE_MTIME = 0.0
        return
    if mtime == _PROFILE_MTIME:
        return
    try:
        if PROFILE_PATH.suffix in (".yaml", ".yml"):
            import yaml  # type: ignore

            _PROFILE_CACHE = yaml.safe_load(PROFILE_PATH.read_text()) or {}
        else:
            _PROFILE_CACHE = json.loads(PROFILE_PATH.read_text())
    except Exception as exc:  # pragma: no cover - log and fall back to defaults
        print(f"Failed to load profile config: {exc}")
        _PROFILE_CACHE = {}
    _PROFILE_MTIME = mtime


def _profile_for(sensor_id: str) -> dict:
    """Return the profile dictionary for ``sensor_id`` if present."""

    _load_profiles()
    prof = _PROFILE_CACHE.get(sensor_id)
    if not prof and "_" in sensor_id:
        # Allow profiles keyed by sensor type (after the first underscore)
        prof = _PROFILE_CACHE.get(sensor_id.split("_", 1)[1])
    return prof or {}


def _generate_value(cfg: dict, seq: int, mode: str) -> float:
    """Generate a reading using ``cfg`` profile and ``mode`` behaviour."""

    baseline = cfg.get("baseline", 0)
    variance = cfg.get("variance", 0)
    drift_amp = cfg.get("drift", 0)
    now = time.time() % 86400
    drift = drift_amp * math.sin(2 * math.pi * now / 86400)
    val = baseline + drift + random.uniform(-variance, variance)
    spike = cfg.get("spike", {})
    magnitude = spike.get("magnitude", 0)
    probability = spike.get("probability", 0)
    interval = spike.get("interval")
    if mode == "bursty":
        if random.random() < probability:
            val += magnitude
    elif mode == "scheduled":
        if interval and seq % int(interval) == 0:
            val += magnitude
    elif mode == "stress":
        val += random.uniform(-variance, variance)
        if random.random() < max(probability, 0.1):
            val += magnitude
    return round(val, 2)


def _load_sequence(device_id: str) -> int:
    """Return the next sequence number for ``device_id``.

    The simulator stores the last used value in ``STATE_DIR/<device_id>.seq``.
    When no file is present the counter starts at ``1``.  The returned value is
    the number that should be used for the next reading.
    """

    path = STATE_DIR / f"{device_id}.seq"
    try:
        return int(path.read_text()) + 1
    except FileNotFoundError:
        return 1
    except Exception:
        # Corrupt state files should not crash the simulator; start fresh.
        return 1


def _save_sequence(device_id: str, seq: int) -> None:
    """Persist ``seq`` for ``device_id`` to disk."""

    STATE_DIR.mkdir(exist_ok=True)
    (STATE_DIR / f"{device_id}.seq").write_text(str(seq))


def _random_ip(used: set) -> str:
    """Return a unique IP in the ``192.168.0.x`` range.

    The simulator auto assigns addresses when none are supplied.  Using a
    predictable class C network keeps the values realistic while avoiding
    collisions between nodes.
    """

    while True:
        candidate = f"192.168.0.{random.randint(2,254)}"
        if candidate not in used:
            used.add(candidate)
            return candidate


def _normalize_config(config: dict) -> dict:
    """Return a normalized copy of ``config`` with sanity checks.

    The simulator previously assumed every node definition contained an ``id``
    and valid sensor list.  When those fields were omitted the mapping printed
    entries like ``"node1": undefined``.  This helper guarantees that each
    node has a unique identifier and IP address and that sensor names are
    stripped of whitespace.  It prints basic warnings so misconfigurations are
    visible to the user, but always returns a structure the rest of the module
    can safely consume.
    """

    normalized = {"nodes": []}
    used_ids = set()
    used_ips = set()
    used_ports = set()

    for idx, node in enumerate(config.get("nodes", []), start=1):
        node_id = node.get("id") or f"node{idx}"
        if node.get("id") is None:
            print(f"Node {idx} missing id; auto assigning '{node_id}'")

        base_id = node_id
        suffix = 1
        while node_id in used_ids:
            node_id = f"{base_id}_{suffix}"
            suffix += 1
        if node_id != base_id:
            print(f"Duplicate node id '{base_id}' detected; renamed to '{node_id}'")

        used_ids.add(node_id)
        ip = node.get("ip")
        if not ip or ip in used_ips:
            if ip in used_ips:
                print(f"Duplicate IP '{ip}' detected; generating unique address")
            ip = _random_ip(used_ips)
        else:
            used_ips.add(ip)
        port = node.get("port")
        if port in (None, ""):
            port = 8000 + idx
        while port in used_ports:
            port += 1
        used_ports.add(port)
        raw_sensors = node.get("sensors")
        if not raw_sensors:
            print(
                f"Node '{node_id}' has no sensors defined; "
                f"using defaults {', '.join(DEFAULT_SENSORS)}"
            )
        sensors = [s.strip() for s in (raw_sensors or DEFAULT_SENSORS) if s.strip()]

        normalized["nodes"].append(
            {"id": node_id, "ip": ip, "port": port, "sensors": sensors}
        )

    if not normalized["nodes"]:
        raise ValueError("No nodes configured")

    return normalized


def _simulate_sensor(sensor_id: str, node_ip: str, gpio_pin: int) -> None:
    """Send periodic fake readings for a single sensor.

    ``node_ip`` represents the endpoint of the simulated node.  It is recorded
    as the device owner so the dashboard can display reachable IP addresses for
    diagnostics.
    """

    register_url = urljoin(BASE_URL, "/register")
    sensor_url = urljoin(BASE_URL, "/sensor")

    # Announce the device only once even if the simulator thread restarts.
    if sensor_id not in ANNOUNCED:
        try:
            requests.post(
                register_url,
                json={"id": sensor_id, "owner": node_ip},
                timeout=5,
                verify=VERIFY,
            )
            ANNOUNCED.add(sensor_id)
        except SSLError as exc:
            if VERIFY:
                # Development setups often rely on self-signed certificates.
                # Retry the request without TLS verification so the simulator
                # continues to function without manual configuration.
                try:
                    requests.post(
                        register_url,
                        json={"id": sensor_id, "owner": node_ip},
                        timeout=5,
                        verify=False,
                    )
                    ANNOUNCED.add(sensor_id)
                    print(
                        f"TLS verification failed for {sensor_id}; proceeding without verification"
                    )
                except Exception as exc2:
                    print(f"register_device failed for {sensor_id}: {exc2}")
            else:
                print(f"register_device failed for {sensor_id}: {exc}")
        except Exception as exc:
            print(f"register_device failed for {sensor_id}: {exc}")

    seq = _load_sequence(sensor_id)

    while True:
        profile = _profile_for(sensor_id)
        mode = profile.get("mode", "steady")
        metrics = profile.get("metrics", {})

        temperature = _generate_value(metrics.get("temperature", DEFAULT_METRICS["temperature"]), seq, mode)
        humidity = _generate_value(metrics.get("humidity", DEFAULT_METRICS["humidity"]), seq, mode)
        soil_moisture = _generate_value(metrics.get("soil_moisture", DEFAULT_METRICS["soil_moisture"]), seq, mode)
        ph = _generate_value(metrics.get("ph", DEFAULT_METRICS["ph"]), seq, mode)
        light = _generate_value(metrics.get("light", DEFAULT_METRICS["light"]), seq, mode)
        water_level = _generate_value(metrics.get("water_level", DEFAULT_METRICS["water_level"]), seq, mode)
        ts = datetime.utcnow().isoformat()
        payload = {
            "id": sensor_id,
            "device_id": sensor_id,
            "seq": seq,
            "temperature": temperature,
            "humidity": humidity,
            "soil_moisture": soil_moisture,
            "ph": ph,
            "light": light,
            "water_level": water_level,
            "timestamp": ts,
            "gpio": gpio_pin,
            "simulated": True,
        }

        submit_dt = datetime.utcnow()
        try:
            requests.post(sensor_url, json=payload, timeout=5, verify=VERIFY)
        except SSLError as exc:
            if VERIFY:
                try:
                    requests.post(sensor_url, json=payload, timeout=5, verify=False)
                    print(
                        f"TLS verification failed for {sensor_id}; proceeding without verification"
                    )
                except Exception as exc2:
                    print(f"record_sensor_data failed for {sensor_id}: {exc2}")
            else:
                print(f"record_sensor_data failed for {sensor_id}: {exc}")
        except Exception as exc:
            print(f"record_sensor_data failed for {sensor_id}: {exc}")

        commit_record = None
        for _ in range(10):
            try:
                resp = requests.get(
                    urljoin(BASE_URL, "/latest-readings"), timeout=5, verify=VERIFY
                )
                latest = resp.json()
                rec = latest.get(sensor_id)
                if rec and int(rec.get("seq", 0)) == seq:
                    commit_record = rec
                    break
            except Exception:
                pass
            time.sleep(0.5)

        if commit_record:
            commit_ts = commit_record.get("timestamp")
            try:
                info = requests.get(
                    urljoin(BASE_URL, "/blockchain-info"), timeout=5, verify=VERIFY
                ).json()
                height = info.get("height")
            except Exception:
                height = None
            try:
                commit_dt = datetime.fromisoformat(commit_ts.replace("Z", "+00:00"))
                latency = (commit_dt - submit_dt).total_seconds()
            except Exception:
                latency = None
            latency_s = f"{latency:.3f}s" if latency is not None else "unknown"
            print(
                f"[latency] {sensor_id} seq {seq} submit {submit_dt.isoformat()} "
                f"commit {commit_ts} height {height} latency {latency_s}"
            )
        else:
            print(f"[latency] {sensor_id} seq {seq} commit not confirmed")

        _save_sequence(sensor_id, seq)
        seq += 1

        print(
            f"{sensor_id} GPIO{gpio_pin} -> T:{temperature} H:{humidity} "
            f"Soil:{soil_moisture} pH:{ph} Light:{light} Water:{water_level}"
        )
        time.sleep(5)


def build_mapping(config: dict) -> dict:
    """Return mapping of nodes to sensors, GPIO pins, and IP addresses.

    Exposed as a public function so the web application can reuse the same
    logic when presenting GPIO assignments to the user before launching the
    simulator.  Each entry has the form ``{id: {"ip": ip, "sensors": {...}}}``
    to make node endpoints visible for diagnostics.  The input configuration is
    normalized to avoid ``undefined`` node identifiers.
    """

    config = _normalize_config(config)
    mapping = {}
    for node in config.get("nodes", []):
        node_id = node["id"]
        sensors = {}
        for idx, sensor in enumerate(node.get("sensors", [])):
            gpio = GPIO_PINS[idx % len(GPIO_PINS)]
            sensors[sensor] = gpio
        mapping[node_id] = {
            "ip": node.get("ip", node_id),
            "port": node.get("port"),
            "sensors": sensors,
        }
    return mapping


def main() -> None:
    if len(sys.argv) > 1:
        cfg_path = Path(sys.argv[1])
        raw_config = json.loads(cfg_path.read_text())
    else:
        nodes = int(input("How many nodes? "))
        raw_config = {"nodes": []}
        for i in range(nodes):
            sensors = input(
                f"Enter sensors for node {i + 1} (comma separated): "
            ).split(",")
            raw_config["nodes"].append(
                {
                    "id": f"node{i + 1}",
                    "sensors": [s.strip() for s in sensors if s.strip()],
                }
            )

    try:
        mapping = build_mapping(raw_config)
    except ValueError as exc:
        print(f"Configuration error: {exc}")
        return
    print("GPIO mapping:")
    print(json.dumps(mapping, indent=2))

    threads = []
    for node_id, info in mapping.items():
        sensors = info["sensors"]
        node_ip = info["ip"]
        for sensor_name, gpio_pin in sensors.items():
            sensor_id = f"{node_id}_{sensor_name}"
            t = threading.Thread(
                target=_simulate_sensor,
                args=(sensor_id, node_ip, gpio_pin),
                daemon=True,
            )
            t.start()
            threads.append(t)

    # Keep main thread alive
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
