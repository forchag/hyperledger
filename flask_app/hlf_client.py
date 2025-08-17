"""Simple placeholder Hyperledger Fabric client."""

from datetime import datetime
import base64
import json
import zlib
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding, rsa
from cryptography.hazmat.primitives import serialization
import threading
import queue
import time
from pathlib import Path
from collections import defaultdict

# This file is a stub demonstrating how a client might interact with
# a Fabric network to invoke the sensor chaincode.
# A real implementation would use the Fabric SDK to submit transactions.

# Keep simple in-memory registries so the Flask app can demonstrate node
# lifecycle events without a real Fabric backend.
DEVICES = []
# Track devices that have been promoted to active status.  In the testing
# environment we automatically activate devices upon registration so sensors
# appear in both the registered and active lists.
ACTIVE_DEVICES = []
from typing import Dict, List

# Mapping of sensor ID to a list of recorded readings
SENSOR_DATA: Dict[str, List[dict]] = {}
# Track the last sequence number seen for each device to enforce monotonic
# ordering and detect duplicates.  This mirrors the behaviour of the actual
# chaincode which stores the most recent sequence value on-chain.
LAST_SEQ: Dict[str, int] = {}
INCIDENTS = []
ATTESTATIONS = []

# Blockchain event log and simple block counter for demo purposes
BLOCK_EVENTS = []
CURRENT_BLOCK = 0

# Directory for persisting readings when the network is unavailable
BACKLOG_DIR = Path(__file__).resolve().parents[1] / "backlog"
BACKLOG_DIR.mkdir(exist_ok=True)
MAX_BACKLOG_AGE = 300  # seconds

# Per-device in-memory queues and worker threads
DEVICE_QUEUES: Dict[str, "queue.Queue"] = {}
DEVICE_THREADS: Dict[str, threading.Thread] = {}
_QUEUE_LOCK = threading.Lock()

# Exponential backoff state per device for retrying backlog flushes
_BACKOFF: Dict[str, float] = defaultdict(lambda: 1.0)

# RSA key pair for encrypting sensor payloads
PRIVATE_KEY = rsa.generate_private_key(public_exponent=65537, key_size=2048)
PUBLIC_KEY = PRIVATE_KEY.public_key()


def log_block_event(message):
    """Record a blockchain operation event with timestamp."""
    BLOCK_EVENTS.append(
        {
            "time": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
            "message": message,
        }
    )
    # Keep last 50 events
    if len(BLOCK_EVENTS) > 50:
        del BLOCK_EVENTS[0]


def encrypt_payload(data: dict) -> str:
    """Encrypt a JSON payload using the RSA public key.

    RSA can only encrypt messages up to a limited size.  We first compress
    the JSON payload with zlib to ensure typical sensor readings fit within
    the RSA block size.  The compressed ciphertext is then RSA encrypted and
    base64 encoded for transport.
    """

    plaintext = zlib.compress(json.dumps(data).encode("utf-8"))
    max_len = PUBLIC_KEY.key_size // 8 - 2 * hashes.SHA256().digest_size - 2
    if len(plaintext) > max_len:
        raise ValueError("Payload too large to encrypt")

    ciphertext = PUBLIC_KEY.encrypt(
        plaintext,
        padding.OAEP(
            mgf=padding.MGF1(algorithm=hashes.SHA256()),
            algorithm=hashes.SHA256(),
            label=None,
        ),
    )
    return base64.b64encode(ciphertext).decode("utf-8")


def decrypt_payload(enc: str) -> dict:
    """Decrypt a base64 encoded payload using the RSA private key."""
    try:
        ciphertext = base64.b64decode(enc.encode("utf-8"))
        plaintext = PRIVATE_KEY.decrypt(
            ciphertext,
            padding.OAEP(
                mgf=padding.MGF1(algorithm=hashes.SHA256()),
                algorithm=hashes.SHA256(),
                label=None,
            ),
        )
        decompressed = zlib.decompress(plaintext)
        return json.loads(decompressed.decode("utf-8"))
    except Exception:
        return {}


def get_block_events():
    """Return recent blockchain events."""
    return BLOCK_EVENTS


def _record_sensor_data_direct(
    id,
    seq,
    temperature,
    humidity,
    soil_moisture,
    ph,
    light,
    water_level,
    timestamp,
    payload,
):
    """Internal synchronous implementation of the sensor data write."""
    global CURRENT_BLOCK
    CURRENT_BLOCK += 1
    log_block_event(f"Creating block {CURRENT_BLOCK}")
    log_block_event(f"Hashing block {CURRENT_BLOCK}")
    log_block_event(f"Saving block {CURRENT_BLOCK}")
    # Reject out-of-order sequences and allow idempotent re-submissions of the
    # same payload.  Each sensor keeps its own sequence counter so readings can
    # be uniquely identified.
    history = SENSOR_DATA.setdefault(id, [])
    for existing in history:
        if existing.get("seq") == seq:
            # If the payload matches exactly treat it as a successful repeat,
            # otherwise raise an error to simulate chaincode rejection.
            if (
                existing.get("temperature") == temperature
                and existing.get("humidity") == humidity
                and existing.get("soil_moisture") == soil_moisture
                and existing.get("ph") == ph
                and existing.get("light") == light
                and existing.get("water_level") == water_level
                and existing.get("payload")
                == (encrypt_payload(payload) if isinstance(payload, dict) else payload)
            ):
                return
            raise ValueError("duplicate sequence number")

    last = LAST_SEQ.get(id, 0)
    if seq <= last:
        raise ValueError("sequence out of order")

    entry = {
        "id": id,
        "seq": seq,
        "temperature": temperature,
        "humidity": humidity,
        "soil_moisture": soil_moisture,
        "ph": ph,
        "light": light,
        "water_level": water_level,
        "timestamp": timestamp,
        "payload": encrypt_payload(payload) if isinstance(payload, dict) else payload,
    }
    history.append(entry)
    LAST_SEQ[id] = seq
    print(
        f"[HLF] record {id} {temperature} {humidity} {soil_moisture} {ph} {light} {water_level} {timestamp}"
    )


def _store_backlog(device_id: str, record: tuple) -> None:
    """Persist a failed record to disk for later retry."""
    BACKLOG_DIR.mkdir(exist_ok=True)
    path = BACKLOG_DIR / f"{device_id}.jsonl"
    entry = {"time": time.time(), "args": record}
    with path.open("a") as fh:
        fh.write(json.dumps(entry) + "\n")


def _flush_backlog(device_id: str) -> bool:
    """Attempt to flush the backlog for a device.

    Returns ``True`` if the backlog was fully processed, ``False`` otherwise.
    """
    path = BACKLOG_DIR / f"{device_id}.jsonl"
    if not path.exists():
        _BACKOFF[device_id] = 1.0
        return True
    remaining = []
    with path.open() as fh:
        lines = fh.readlines()
    for line in lines:
        data = json.loads(line)
        if time.time() - data.get("time", 0) > MAX_BACKLOG_AGE:
            # Drop stale entry
            continue
        try:
            _record_sensor_data_direct(*data["args"])
        except Exception:
            remaining.append(data)
            break
    if remaining:
        with path.open("w") as fh:
            for item in remaining:
                fh.write(json.dumps(item) + "\n")
        _schedule_retry(device_id)
        return False
    path.unlink()
    _BACKOFF[device_id] = 1.0
    return True


def _schedule_retry(device_id: str) -> None:
    """Schedule a retry for the given device using exponential backoff."""
    delay = _BACKOFF[device_id]
    timer = threading.Timer(delay, _flush_backlog, args=(device_id,))
    timer.daemon = True
    timer.start()
    _BACKOFF[device_id] = min(delay * 2, 60)


def _worker(device_id: str) -> None:
    """Process a device's queue serially."""
    q = DEVICE_QUEUES[device_id]
    while True:
        record = q.get()
        try:
            _record_sensor_data_direct(*record)
            _flush_backlog(device_id)
        except Exception:
            _store_backlog(device_id, record)
            _schedule_retry(device_id)
        q.task_done()


def record_sensor_data(
    id,
    seq,
    temperature,
    humidity,
    soil_moisture,
    ph,
    light,
    water_level,
    timestamp,
    payload,
):
    """Enqueue sensor data for serial processing per device."""
    with _QUEUE_LOCK:
        q = DEVICE_QUEUES.setdefault(id, queue.Queue())
        if id not in DEVICE_THREADS or not DEVICE_THREADS[id].is_alive():
            t = threading.Thread(target=_worker, args=(id,), daemon=True)
            DEVICE_THREADS[id] = t
            t.start()
    q.put((id, seq, temperature, humidity, soil_moisture, ph, light, water_level, timestamp, payload))


def get_backlog_stats() -> Dict[str, int]:
    """Return the number of queued readings per device."""
    stats: Dict[str, int] = {}
    if not BACKLOG_DIR.exists():
        return stats
    for path in BACKLOG_DIR.glob("*.jsonl"):
        try:
            with path.open() as fh:
                count = sum(1 for _ in fh)
            if count:
                stats[path.stem] = count
        except FileNotFoundError:
            continue
    return stats


def register_device(id, owner):
    """Register a device with the ledger."""
    if id not in DEVICES:
        DEVICES.append(id)
    activate_device(id)
    print(f"[HLF] register device {id} owner {owner}")


def activate_device(id):
    """Mark a device as active if not already present."""
    if id not in ACTIVE_DEVICES:
        ACTIVE_DEVICES.append(id)


def list_active_devices():
    """Return a list of currently active device IDs."""
    return ACTIVE_DEVICES


def log_event(device_id, event_type, timestamp):
    """Log a network event on the ledger."""
    print(f"[HLF] event {device_id} {event_type} {timestamp}")


def log_security_incident(
    device_id, description, timestamp, *, score=None, payload=None
):
    """Log a security incident on the ledger."""
    incident = {
        "device_id": device_id,
        "description": description,
        "timestamp": timestamp,
    }
    if score is not None:
        incident["score"] = score
    if payload is not None:
        incident["payload"] = payload
    INCIDENTS.append(incident)
    print(
        f"[HLF] security incident {device_id} {description} {timestamp} score={score}"
    )


def attest_device(device_id, status, timestamp):
    """Record a device attestation result."""
    ATTESTATIONS.append(
        {
            "device_id": device_id,
            "status": status,
            "timestamp": timestamp,
        }
    )
    print(f"[HLF] attestation {device_id} {status} {timestamp}")


def get_attestations():
    """Return recorded device attestations."""
    return ATTESTATIONS


def list_devices():
    """Return a list of registered device IDs."""
    # This would normally query the ledger. We return the in-memory list.
    return DEVICES


def get_incidents():
    """Return all recorded security incidents."""
    return INCIDENTS


def get_sensor_data(sensor_id):
    """Retrieve the latest sensor metadata for the given device."""
    print(f"[HLF] query sensor data for {sensor_id}")
    records = SENSOR_DATA.get(sensor_id)
    if not records:
        return None
    return records[-1]


def get_sensor_history(sensor_id, start=None, end=None):
    """Return all recorded readings for a device optionally filtered by date."""
    records = SENSOR_DATA.get(sensor_id, [])
    if start:
        records = [r for r in records if r["timestamp"] >= start]
    if end:
        records = [r for r in records if r["timestamp"] <= end]
    return records


def get_all_sensor_data(start=None, end=None):
    """Return readings for all devices."""
    result = []
    for dev in DEVICES:
        result.extend(get_sensor_history(dev, start, end))
    return result


def get_latest_readings():
    """Return the most recent reading for each device."""
    result = {}
    for dev in DEVICES:
        records = SENSOR_DATA.get(dev)
        if records:
            result[dev] = records[-1]
    return result


def get_state_on(date: str):
    """Return the last recorded reading for each device on the given YYYY-MM-DD date."""
    result = {}
    start = date + "T00:00:00Z"
    end = date + "T23:59:59Z"
    for dev in DEVICES:
        records = get_sensor_history(dev, start, end)
        if records:
            result[dev] = records[-1]
    return result


def query_blockchain_info():
    """Return basic ledger info such as height and current block hash."""
    print("[HLF] query blockchain info")
    # ``CURRENT_BLOCK`` tracks the number of commits performed by the in-memory
    # ledger used in the test environment.  Exposing it here allows external
    # callers such as the sensor simulator to retrieve a monotonically
    # increasing ledger height similar to ``peer channel getinfo`` in a real
    # Fabric network.
    return {"height": CURRENT_BLOCK, "current_hash": "0x0"}


def get_block(block_number):
    """Retrieve a specific block."""
    print(f"[HLF] get block {block_number}")
    return {
        "header": {"number": block_number, "previous_hash": "0x0", "data_hash": "0x0"},
        "data": [],
    }


QUARANTINED = set()


def quarantine_device(device_id):
    """Mark a device as quarantined."""
    QUARANTINED.add(device_id)
    print(f"[HLF] device {device_id} quarantined")


def is_quarantined(device_id):
    """Return True if the device is quarantined."""
    return device_id in QUARANTINED


def get_quarantined():
    """Return a list of quarantined device IDs."""
    return list(QUARANTINED)
