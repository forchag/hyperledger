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

`lora_node.py` shows how a sensor node can send sensor readings or periodic
heartbeat packets over LoRa using the `pySX127x` library. The companion
`network_monitor.py` listens for these heartbeats, logs them on the blockchain
and prints a list of discovered nodes every minute.

`sensor_node.py` polls a DHT22, soil moisture, pH, light and water level sensor
every few seconds, stores the data on the blockchain and can optionally forward
the payload over LoRa. These scripts are stubs and can be run on a Raspberry Pi
with appropriate radio modules attached.

## Running a Fabric network locally

Follow the steps below to launch a small Fabric network and deploy the sensor chaincode on a single machine.

1. **Install prerequisites**
   Ensure Docker, Docker Compose, Git and curl are installed. On Debian based systems run:
   ```bash
   sudo apt update
   sudo apt install -y docker.io docker-compose git curl
   sudo usermod -aG docker $USER
   newgrp docker
   ```

2. **Download Fabric samples and binaries** (required once):
   ```bash
   curl -sSL https://bit.ly/2ysbOFE | bash -s -- 2.5.0
   ```
   This creates a `fabric-samples` directory containing the `test-network` sample.

3. **Start the network and deploy chaincode**
   From the repository root run:
   ```bash
   ./test_network.sh
   ```
   The script starts the Fabric network and deploys the `sensor` chaincode.

4. **Start supporting services**
   Open a new terminal and run:
   ```bash
   ipfs daemon
   ```
   In another terminal launch the Flask API:
   ```bash
   pip install flask ipfshttpclient
   python flask_app/app.py
   ```

5. **Interact with the network**
   Visit `https://localhost:8443/` to use the dashboard or invoke the tools in the `tools` directory.

To stop the network run:
```bash
cd fabric-samples/test-network
./network.sh down
```

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

## Blockchain design

This project uses **Hyperledger Fabric**, a permissioned blockchain platform. Peers
endorse transactions and store the ledger, while an ordering service
creates blocks using the RAFT consensus algorithm. Each block contains a
header with the number, the hash of the previous block, and the hash of
its transaction data. This hash chaining makes the ledger immutable –
any change would break the chain of hashes.

Sensor readings and heartbeat events are submitted through chaincode
(`sensor.go`). Each transaction is endorsed, ordered into a block, and
committed to all peers. Clients can query the ledger to retrieve device
information or verify data integrity.

### Inspecting and verifying blocks

The Fabric CLI can display high level ledger information:

```bash
peer channel getinfo -c mychannel
```

Specific blocks may be fetched and decoded using the CLI or the Python
`tools/block_inspector.py` utility:

```bash
python tools/block_inspector.py --info
python tools/block_inspector.py --block 2
```

The inspector prints the block header including `previous_hash` and
`data_hash`, allowing you to differentiate one block from another and
view the stored transactions.
