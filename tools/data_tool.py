import argparse
import json
from datetime import datetime

import ipfshttpclient

from flask_app import hlf_client


def upload(sensor_id: str, json_file: str):
    """Upload a JSON sensor payload to IPFS and record metadata on-chain."""
    with open(json_file, 'rb') as fh:
        data = fh.read()
    client = ipfshttpclient.connect('/dns/localhost/tcp/5001/http')
    cid = client.add_bytes(data)
    payload = json.loads(data.decode('utf-8'))
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
        cid,
    )
    print('Uploaded with CID', cid)


def retrieve(sensor_id: str):
    """Retrieve sensor data from IPFS using the CID stored on-chain."""
    data = hlf_client.get_sensor_data(sensor_id)
    if not data:
        print('No sensor data found')
        return
    cid = data['cid']
    client = ipfshttpclient.connect('/dns/localhost/tcp/5001/http')
    content = client.cat(cid)
    print(content.decode('utf-8'))


def verify(sensor_id: str):
    """Verify that IPFS content matches the on-chain CID."""
    data = hlf_client.get_sensor_data(sensor_id)
    if not data:
        print('No sensor data found')
        return
    cid = data['cid']
    client = ipfshttpclient.connect('/dns/localhost/tcp/5001/http')
    content = client.cat(cid)
    new_cid = client.add_bytes(content)
    if cid == new_cid:
        print('Data integrity verified')
    else:
        print('Data integrity check FAILED')


def recover(sensor_id: str):
    """Simulate IPFS node failure and recover content."""
    data = hlf_client.get_sensor_data(sensor_id)
    if not data:
        print('No sensor data found')
        return
    cid = data['cid']
    client = ipfshttpclient.connect('/dns/localhost/tcp/5001/http')
    content = client.cat(cid)
    print('Fetched content, re-adding to IPFS...')
    new_cid = client.add_bytes(content)
    if cid == new_cid:
        print('Recovery successful - CID matches')
    else:
        print('Recovery created new CID:', new_cid)


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

