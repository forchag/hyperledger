"""Simple placeholder Hyperledger Fabric client."""

# This file is a stub demonstrating how a client might interact with
# a Fabric network to invoke the sensor chaincode.
# A real implementation would use the Fabric SDK to submit transactions.

# Keep a simple in-memory registry of devices so that the Flask app can
# demonstrate interactions with multiple nodes without a real Fabric backend.
DEVICES = []


def record_sensor_data(id, temperature, humidity, timestamp, cid):
    """Submit RecordSensorData transaction."""
    print(f"[HLF] record {id} {temperature} {humidity} {timestamp} {cid}")


def register_device(id, owner):
    """Register a device with the ledger."""
    if id not in DEVICES:
        DEVICES.append(id)
    print(f"[HLF] register device {id} owner {owner}")


def log_event(device_id, event_type, timestamp):
    """Log a network event on the ledger."""
    print(f"[HLF] event {device_id} {event_type} {timestamp}")


def list_devices():
    """Return a list of registered device IDs."""
    # This would normally query the ledger. We return the in-memory list.
    return DEVICES


def get_sensor_data(sensor_id):
    """Retrieve sensor metadata from the ledger."""
    # In a real client this would query the ledger. Here we mock a response.
    print(f"[HLF] query sensor data for {sensor_id}")
    return {
        "id": sensor_id,
        "temperature": 0,
        "humidity": 0,
        "timestamp": "1970-01-01T00:00:00Z",
        "cid": "QmExampleCID",
    }


def query_blockchain_info():
    """Return basic ledger info such as height and current block hash."""
    print("[HLF] query blockchain info")
    return {"height": 0, "current_hash": "0x0"}


def get_block(block_number):
    """Retrieve a specific block."""
    print(f"[HLF] get block {block_number}")
    return {
        "header": {"number": block_number, "previous_hash": "0x0", "data_hash": "0x0"},
        "data": [],
    }
