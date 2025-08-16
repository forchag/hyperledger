# Hyperledger Farm Network

This directory contains a minimal example of integrating Hyperledger Fabric with LoRa sensor nodes. The Fabric chaincode stores device registrations, sensor readings and network events.

## Chaincode

`chaincode/sensor/sensor.go` implements a Fabric chaincode that allows:

* Registering devices
* Recording encrypted sensor data for soil moisture, pH, light
  and water level measurements
* Logging network events
* Sending permissioned messages between devices

The chaincode folder contains a `go.mod` file declaring its module path and
dependencies. Hyperledger Fabric requires either Go modules or a `vendor`
directory to package Go chaincode. The provided module file enables dependency
vendoring before deploying the chaincode. The line `module sensor` simply
names the chaincode module; it does not need to point to a real GitHub
repository. The only external dependency is
`github.com/hyperledger/fabric-contract-api-go`, which Go downloads when you
run `go mod vendor`.

### Starting the blockchain and smart contract

Launch the local Fabric network and deploy the sensor chaincode using the
included helper script:

```bash
./test_network.sh
```

The script downloads the Fabric samples if needed, shuts down any previous
instance of the network, then starts the test network and activates the
`sensor` smart contract so other tools can interact with the
blockchain.

Ledger data is written to a host directory specified by the `FABRIC_LEDGER_DIR`
environment variable (default: `~/fabric-ledger`). Subfolders for the orderer,
each peer, and every CouchDB instance are created automatically so ledger
contents survive container restarts.

## Flask GUI

`flask_app/app.py` exposes a small HTTPS GUI and REST API to register devices, upload files, record sensor data and verify stored information. The dashboard shows how many nodes are registered and offers options to inspect stored data.
An additional page available at `/integrity` lets administrators export sensor
data as CSV and verify uploaded datasets against the hashes stored on the
blockchain.

Start the app with:

```bash
pip install flask cryptography
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
every few seconds. By default it sends the readings to the Flask API over HTTP
but it can also transmit them over LoRa or use both channels for redundancy via
the `--mode` option. These scripts are stubs and can be run on a Raspberry Pi
with appropriate radio modules attached.
The chaincode now records all of these metrics so that agronomists can
track detailed conditions directly on the ledger.

## Connecting sensors to a Raspberry Pi

1. **Gather jumper wires and the sensors**
   Each sensor normally has three pins: power (`VCC`), ground (`GND`) and a data
   line. Use female‑to‑male jumper wires so they plug directly onto the Pi's
   GPIO header.

2. **Wire the DHT22 temperature and humidity sensor**
   - Connect `VCC` to pin **1** (5&nbsp;V).
   - Connect `GND` to pin **6**.
   - Connect the data pin to **GPIO&nbsp;4**.
   - Place a 10&nbsp;kΩ resistor between `VCC` and the data pin.

3. **Attach the soil moisture, pH, light and water level sensors**
   - Use any free 5&nbsp;V and GND pins for power.
   - Connect the data pins to **GPIO&nbsp;17**, **GPIO&nbsp;18**,
     **GPIO&nbsp;6** and **GPIO&nbsp;16** respectively.
   - If a sensor outputs an analog signal, route it through an ADC such as the
     MCP3008 before connecting it to the GPIO pin.

4. **Test your wiring**
   Power on the Pi and run:
   ```bash
   python sensor_node.py sensor-1
   ```
   If you see numbers printing every few seconds the sensors are properly
   connected.

## Running a Fabric network locally

The instructions below walk through a complete setup on a small Raspberry Pi cluster. The first Pi is assumed to have the address `192.168.0.163` and additional nodes can use `192.168.0.199` and `192.168.0.200`.

1. **Clone this repository on the first Pi and change into it**
   ```bash
   git clone https://github.com/<your-user>/hyperledger-farm-network.git
   cd hyperledger-farm-network
   ```

2. **Install prerequisites**
   Ensure Docker, Docker Compose, Git and curl are installed. On Debian based systems run:
   ```bash
   sudo apt update
   sudo apt install -y docker.io docker-compose git curl
   sudo usermod -aG docker $USER
   newgrp docker
   ```

3. **Download Fabric samples and binaries** (required once)
   ```bash
   curl -sSL https://bit.ly/2ysbOFE | bash -s -- 2.5.0
   ```
   This creates a `fabric-samples` directory containing the `test-network` sample.

   The Go chaincode in `chaincode/sensor` uses Go modules. Before deploying the
   chaincode, vendor its dependencies so that the Fabric peer does not attempt to
   fetch them from the internet during packaging:
   ```bash
   cd chaincode/sensor
   go mod vendor
   cd ../../
   ```

   Without a `vendor` directory the `peer lifecycle chaincode package` command
   executed by `test_network.sh` fails to create `sensor.tar.gz` and chaincode
   installation stops with `failed to read chaincode package at 'sensor.tar.gz'`.

4. **Make the helper script executable**
   The network script is not executable when cloned. Grant execute permission
   once:
   ```bash
   chmod +x test_network.sh
   ```

5. **Start the network and deploy chaincode**
   From the repository root run:
   ```bash
   ./test_network.sh
   ```
The script automatically changes into `fabric-samples/test-network`,
   stops any running instance of the test network, then brings up a fresh
   network and deploys the `sensor` chaincode.

**Important:** Run this command on only one host. The default
`test-network` uses Docker Compose to launch all Fabric containers on the
local machine. Starting it simultaneously on multiple nodes creates
separate peers and orderers that cannot communicate, leading to timeout
errors during chaincode installation. After the script finishes verify
the peers are running with `docker ps`. For a real multi-host setup you
must edit the compose files under `fabric-samples/test-network` so that
peers and orderers reference the correct remote addresses.

6. **Start supporting services**
   Launch the Flask API from the repository root:
   ```bash
   pip install flask cryptography
   python flask_app/app.py
   ```
7. **Interact with the network**
    Open `https://192.168.0.163:8443/` in your browser to use the dashboard or invoke the tools in the `tools` directory.

### Adding another Raspberry Pi

Clone this repository on the new Pi (for example `192.168.0.199` or `192.168.0.200`) and repeat the dependency installation. Launch the Flask app:

```bash
ipfs daemon
python flask_app/app.py
```

Visit `https://<new-pi-ip>:8443/` to access the dashboard of that node. Once two or more nodes are registered the first Pi automatically starts the Fabric network.

**Important:** Do **not** run `./test_network.sh` or attempt to deploy the chaincode from additional nodes. The sample test network is designed to run on a single machine. Starting it again on another Pi will spin up a second set of peers and orderers that cannot communicate with the first, causing "chaincode failed" errors during installation. Only the first node should host the Fabric containers. Other nodes simply run the Flask dashboard so they can talk to the blockchain through the gateway on the first Pi.

8. **Stop the network**
   ```bash
   cd fabric-samples/test-network
   ./network.sh down
   ```

The `tools/data_tool.py` script provides a command line utility to upload sensor payloads directly to the blockchain and retrieve them:

```bash
python tools/data_tool.py upload sensor-1 reading.json
python tools/data_tool.py retrieve sensor-1
python tools/data_tool.py verify sensor-1
```

These examples assume the chaincode has been deployed as described above. The dashboard offers buttons for verifying and recovering data using the same logic.

## Starting the Fabric network at boot

The `systemd/fabric-network@.service` unit lets any Linux user launch the Fabric test network automatically after reboot.

1. Link the unit so your user picks up updates from this repository:
   ```bash
   systemctl --user link $(pwd)/systemd/fabric-network@.service
   systemctl --user daemon-reload
   ```
2. Enable the service for the directory name where this repository resides (replace `$(basename "$PWD")` if needed):
   ```bash
   systemctl --user enable --now fabric-network@$(basename "$PWD").service
   ```
3. Allow the service to run without an active login:
   ```bash
   loginctl enable-linger $USER
   ```

The unit runs `start_network.sh` from the repository and passes `FABRIC_LEDGER_DIR` (default `~/fabric-ledger`) to persist the ledger. Adjust the directory name or ledger path with `systemctl --user edit` if your layout differs.

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

### Block characteristics

Blocks in the default test network are cut when either 10 transactions
accumulate or about two seconds pass.  A block typically stays under
2&nbsp;MB in size but the absolute maximum is 10&nbsp;MB.  Every
transaction is hashed with **SHA-256** before inclusion and the block
header stores the Merkle root of all transaction hashes.  Communication
between nodes is protected with TLS but the on-disk ledger itself is not
encrypted.  Because only a small transaction descriptor is stored on the
ledger, roughly a few hundred sensor events comfortably fit into a
single block.

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

## Security monitoring

`threat_detection.py` continuously checks recent sensor readings for
abnormal values. When it detects suspicious behaviour it records a
security incident on the blockchain using the `LogSecurityIncident`
chaincode function. `incident_responder.py` watches the ledger for such
events and automatically quarantines affected devices via the stubbed
`hlf_client` API.

The Flask dashboard also exposes a `/status` page showing the number of
recorded security incidents and how many devices are currently quarantined.
This information is refreshed live from the in-memory data maintained by
`hlf_client` while `incident_responder` runs in the background when the
web server starts.

## Threat Detection Engine (TDE)

The Threat Detection Engine is the heart of the cybersecurity layer and is
deployed directly on the Edge Gateway Node (e.g., Raspberry Pi). This engine
continuously monitors device behavior to detect anomalies that may signify
malicious activity.

### Behavioral Baseline and Profiling

Each sensor or actuator device has an expected pattern of behavior—defined by
transmission intervals, data ranges, and communication protocols. The TDE builds
a real-time behavioral model using a rolling average and standard deviation.

### Lightweight Machine Learning

For more advanced scenarios, a decision-tree classifier or anomaly detection
algorithm like Isolation Forest is embedded in the gateway to learn patterns
over time.

Normal behavior: Regular sensor data within expected frequency

Anomaly: Sudden surge of messages, invalid payloads, command injections

These models continuously score each device with a Suspicion Score (0–1).
Scores above a configurable threshold (e.g., 0.8) are treated as incidents.

### Incident Generation

Once a behavior is flagged, the engine generates a Security Incident Report
(SIR) with metadata including:

* Device ID
* Type of anomaly
* Time of detection
* Suspicion score
* Payload snapshot (optional)

The report is serialized in JSON and forwarded to the blockchain via the smart
contract interface.

## Data storage and recovery

All sensor data is now stored directly on the blockchain.  Before being
committed each payload is encrypted with an RSA public key so that only
nodes possessing the private key can decode it.  The helper script
`tools/node_recovery.py` prints the encrypted payloads for auditing
purposes.

## Extended dashboard

Several additional pages provide deeper insight into the running system:

* **Sensor History** (`/history`) &ndash; plots past readings as an interactive chart.
* **Blockchain Explorer** (`/explorer`) &ndash; lists recent block events.
* **Device Management** (`/devices`) &ndash; shows devices with quarantine controls.
* **Storage Monitor** (`/storage`) &ndash; displays stored CIDs and timestamps.
* **Recovery Dashboard** (`/recovery`) &ndash; simulates replication of existing data.
* **User Access Log** (`/access-log`) &ndash; exposes recent HTTP requests.

These pages rely on the stubbed `hlf_client` module for demo data and are
served by `flask_app/app.py`.
