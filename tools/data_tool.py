import argparse
import json
from datetime import datetime


from flask_app import hlf_client


def upload(sensor_id: str, json_file: str):
    """Upload a JSON sensor payload and record it on-chain."""
    with open(json_file, 'r', encoding='utf-8') as fh:
        payload = json.load(fh)
    payload.setdefault('timestamp', datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ'))
    hlf_client.record_sensor_data(
        sensor_id,
        payload.get('temperature', 0),
        payload.get('humidity', 0),
        payload.get('soil_moisture', 0),
        payload.get('ph', 0),
        payload.get('light', 0),
        payload.get('water_level', 0),
        payload['timestamp'],
        payload,
    )
    print('Uploaded record')


def retrieve(sensor_id: str):
    """Retrieve sensor data from IPFS using the CID stored on-chain."""
    data = hlf_client.get_sensor_data(sensor_id)
    if not data:
        print('No sensor data found')
        return
    payload = hlf_client.decrypt_payload(data['payload'])
    print(json.dumps(payload, indent=2))


def verify(sensor_id: str):
    """Verify that IPFS content matches the on-chain CID."""
    data = hlf_client.get_sensor_data(sensor_id)
    if not data:
        print('No sensor data found')
        return
    payload = hlf_client.decrypt_payload(data['payload'])
    if payload:
        print('Data integrity verified')
    else:
        print('Data integrity check FAILED')


def recover(sensor_id: str):
    """Retrieve and print encrypted payload."""
    data = hlf_client.get_sensor_data(sensor_id)
    if not data:
        print('No sensor data found')
        return
    payload = hlf_client.decrypt_payload(data['payload'])
    print(json.dumps(payload, indent=2))


def main():
    parser = argparse.ArgumentParser(description='Sensor data tool')
    sub = parser.add_subparsers(dest='cmd')

    up = sub.add_parser('upload')
    up.add_argument('sensor_id')
    up.add_argument('json_file')

    sub.add_parser('retrieve').add_argument('sensor_id')
    sub.add_parser('verify').add_argument('sensor_id')
    sub.add_parser('recover').add_argument('sensor_id')

    args = parser.parse_args()

    if args.cmd == 'upload':
        upload(args.sensor_id, args.json_file)
    elif args.cmd == 'retrieve':
        retrieve(args.sensor_id)
    elif args.cmd == 'verify':
        verify(args.sensor_id)
    elif args.cmd == 'recover':
        recover(args.sensor_id)
    else:
        parser.print_help()


if __name__ == '__main__':
    main()

