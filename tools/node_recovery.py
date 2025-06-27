#!/usr/bin/env python3
"""Replicate sensor data for a new node joining the network."""

import argparse
import ipfshttpclient
from flask_app import hlf_client


def bootstrap(api_addr: str) -> None:
    """Fetch all known sensor CIDs and pin them locally."""
    client = ipfshttpclient.connect(api_addr)
    for dev in hlf_client.list_devices():
        for record in hlf_client.get_sensor_history(dev):
            cid = record.get('cid')
            if not cid:
                continue
            try:
                client.pin.add(cid)
                print(f"Pinned {cid} for {dev}")
            except Exception as e:
                print(f"Failed to pin {cid}: {e}")


def main():
    p = argparse.ArgumentParser(description="Recover data for a new storage node")
    p.add_argument('--api', default='/dns/localhost/tcp/5001/http',
                   help='IPFS API multiaddress of the new node')
    args = p.parse_args()
    bootstrap(args.api)


if __name__ == '__main__':
    main()
