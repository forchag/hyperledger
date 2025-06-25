# Hyperledger Farm Network

This directory contains a minimal example of integrating Hyperledger Fabric with IPFS and LoRa sensor nodes. The Fabric chaincode stores device registrations, sensor readings and network events.

## Chaincode

`chaincode/sensor/sensor.go` implements a Fabric chaincode that allows:

* Registering devices
* Recording sensor data with IPFS CIDs
* Logging network events
* Sending permissioned messages between devices

## Flask GUI

`flask_app/app.py` exposes a small GUI and REST API to register devices, upload files, record sensor data and verify stored information. It expects a local IPFS daemon running on `localhost:5001` and a Fabric gateway configured via the stub `hlf_client` module.

Start the app with:

```bash
pip install flask ipfshttpclient
python app.py
```

Then POST sensor data in JSON format to `/sensor`, upload a file to `/upload` or register a device at `/register`.

## LoRa examples

`lora_node.py` shows how a sensor node could send readings over LoRa using the `pySX127x` library. `network_monitor.py` periodically logs device heartbeats on-chain.

These scripts are stubs and can be run on a Raspberry Pi with appropriate radio modules attached.

## Running a Fabric network

This repository does not include the full Fabric test network. Refer to the official [Fabric documentation](https://hyperledger-fabric.readthedocs.io/) to bootstrap a network using the `test-network` samples. Deploy the chaincode in `chaincode/sensor` and update `hlf_client.py` to submit transactions via the Fabric SDK