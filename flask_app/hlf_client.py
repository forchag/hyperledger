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