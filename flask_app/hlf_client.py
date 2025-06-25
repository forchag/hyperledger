"""Simple placeholder Hyperledger Fabric client."""

# This file is a stub demonstrating how a client might interact with
# a Fabric network to invoke the sensor chaincode.
# A real implementation would use the Fabric SDK to submit transactions.

def record_sensor_data(id, temperature, humidity, timestamp, cid):
    """Submit RecordSensorData transaction."""
    print(f"[HLF] record {id} {temperature} {humidity} {timestamp} {cid}")

def register_device(id, owner):
    """Register a device with the ledger."""
    print(f"[HLF] register device {id} owner {owner}")

def log_event(device_id, event_type, timestamp):
    """Log a network event on the ledger."""
    print(f"[HLF] event {device_id} {event_type} {timestamp}")


def list_devices():
    """Return a list of registered device IDs."""
    # This would normally query the ledger.
    return ['device-1', 'device-2']


def get_sensor_data(sensor_id):
    """Retrieve sensor metadata from the ledger."""
    # In a real client this would query the ledger. Here we mock a response.
    print(f"[HLF] query sensor data for {sensor_id}")
    return {
        'id': sensor_id,
        'temperature': 0,
        'humidity': 0,
        'timestamp': '1970-01-01T00:00:00Z',
        'cid': 'QmExampleCID'
    }
