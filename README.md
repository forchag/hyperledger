# Hyperledger Farm Network

This directory contains a minimal example of integrating Hyperledger Fabric with IPFS and LoRa sensor nodes. The Fabric chaincode stores device registrations, sensor readings and network events.

## Chaincode

`chaincode/sensor/sensor.go` implements a Fabric chaincode that allows:

* Registering devices
* Recording sensor data with IPFS CIDs
* Logging network events
* Sending permissioned messages between devices

## Flask GUI

`flask_app/app.py` exposes a small HTTPS GUI and REST API to register devices, upload files, record sensor data and verify stored information. It expects a local IPFS daemon running on `localhost:5001` and a Fabric gateway configured via the stub `hlf_client` module. The dashboard shows how many nodes are registered and offers options to verify and recover data stored on IPFS.

Start the app with:

```bash
pip install flask ipfshttpclient
openssl req -newkey rsa:2048 -nodes -keyout key.pem -x509 -days 365 -out cert.pem -subj "/CN=farm"
python flask_app/app.py
```

Visit `https://<pi-ip>:8443/` to open the dashboard. Sensor data can also be posted directly to `/sensor`, files to `/upload`, or devices registered at `/register`.

## LoRa examples

`lora_node.py` shows how a sensor node could send readings over LoRa using the `pySX127x` library. `network_monitor.py` periodically logs device heartbeats on-chain.

These scripts are stubs and can be run on a Raspberry Pi with appropriate radio modules attached.

## Running a Fabric network

This repository does not include the full Fabric test network. Refer to the official [Fabric documentation](https://hyperledger-fabric.readthedocs.io/) to bootstrap a network using the `test-network` samples. Deploy the chaincode in `chaincode/sensor` and update `hlf_client.py` to submit transactions via the Fabric SDK.

## Data tools and recovery demo

The `tools/data_tool.py` script provides a command line utility to upload sensor payloads to IPFS and store the resulting CID on chain. It can also retrieve and verify stored data:

```bash
python tools/data_tool.py upload sensor-1 reading.json
python tools/data_tool.py retrieve sensor-1
python tools/data_tool.py verify sensor-1
```

Simulated recovery of lost IPFS blocks is performed with:

```bash
python tools/data_tool.py recover sensor-1
```

These examples assume an IPFS daemon is running locally and that the chaincode has been deployed as described above.
The dashboard offers buttons for verifying and recovering data using the same logic.
