"""Simple placeholder Hyperledger Fabric client."""

from datetime import datetime

# This file is a stub demonstrating how a client might interact with
# a Fabric network to invoke the sensor chaincode.
# A real implementation would use the Fabric SDK to submit transactions.

# Keep a simple in-memory registry of devices so that the Flask app can
# demonstrate interactions with multiple nodes without a real Fabric backend.
DEVICES = []
# Mapping of sensor ID to a list of recorded readings
SENSOR_DATA = {}
INCIDENTS = []
ATTESTATIONS = []

# Blockchain event log and simple block counter for demo purposes
BLOCK_EVENTS = []
CURRENT_BLOCK = 0


def log_block_event(message):
    """Record a blockchain operation event with timestamp."""
    BLOCK_EVENTS.append({
        'time': datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ'),
        'message': message,
    })
    # Keep last 50 events
    if len(BLOCK_EVENTS) > 50:
        del BLOCK_EVENTS[0]


def get_block_events():
    """Return recent blockchain events."""
    return BLOCK_EVENTS


def record_sensor_data(id, temperature, humidity, timestamp, cid):
    """Submit RecordSensorData transaction and keep a history of readings."""
    global CURRENT_BLOCK
    CURRENT_BLOCK += 1
    log_block_event(f"Creating block {CURRENT_BLOCK}")
    log_block_event(f"Hashing block {CURRENT_BLOCK}")
    log_block_event(f"Saving block {CURRENT_BLOCK}")
    entry = {
        'id': id,
        'temperature': temperature,
        'humidity': humidity,
        'timestamp': timestamp,
        'cid': cid,
    }
    SENSOR_DATA.setdefault(id, []).append(entry)
    print(f"[HLF] record {id} {temperature} {humidity} {timestamp} {cid}")

def register_device(id, owner):
    """Register a device with the ledger."""
    if id not in DEVICES:
        DEVICES.append(id)
    print(f"[HLF] register device {id} owner {owner}")

def log_event(device_id, event_type, timestamp):
    """Log a network event on the ledger."""
    print(f"[HLF] event {device_id} {event_type} {timestamp}")


def log_security_incident(device_id, description, timestamp):
    """Log a security incident on the ledger."""
    INCIDENTS.append({
        'device_id': device_id,
        'description': description,
        'timestamp': timestamp,
    })
    print(f"[HLF] security incident {device_id} {description} {timestamp}")


def attest_device(device_id, status, timestamp):
    """Record a device attestation result."""
    ATTESTATIONS.append({
        'device_id': device_id,
        'status': status,
        'timestamp': timestamp,
    })
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
        records = [r for r in records if r['timestamp'] >= start]
    if end:
        records = [r for r in records if r['timestamp'] <= end]
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
    return {
        'height': 0,
        'current_hash': '0x0'
    }


def get_block(block_number):
    """Retrieve a specific block."""
    print(f"[HLF] get block {block_number}")
    return {
        'header': {
            'number': block_number,
            'previous_hash': '0x0',
            'data_hash': '0x0'
        },
        'data': []
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
