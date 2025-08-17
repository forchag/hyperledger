# Getting Started

Follow these steps to set up the Hyperledger Farm Network on a new Linux node using a Python virtual environment.

## Quick one-click demo

To exercise the full workflow automatically, run:

```bash
./one_click_test.sh
```

Or open the simulator dashboard and click **Run One-Click Demo**.
The script launches Fabric, bootstraps a peer, sends a few simulated readings and prints ledger info. Use the manual steps below for a step-by-step walk-through.

## 1. Clone the repository
```bash
git clone https://github.com/<your-user>/hyperledger-farm-network.git
cd hyperledger-farm-network
```

## 2. Create and activate a virtual environment
```bash
python3 -m venv venv
source venv/bin/activate
```

## 3. Install Python dependencies
Install all required packages:
```bash
pip install -r requirements.txt
```

## 4. Start the local Fabric network
The project includes a helper script that downloads the Fabric samples and launches the test network:
```bash
./test_network.sh
```

## 5. Launch the Flask dashboard
Generate a self-signed certificate and start the web interface:
```bash
openssl req -newkey rsa:2048 -nodes -keyout key.pem -x509 -days 365 -out cert.pem -subj "/CN=farm"
python flask_app/app.py
```
The dashboard will be available at `https://<host-ip>:8443/`.

## 6. Run the sensor simulator
Use the simulator to send fake readings to the dashboard and ledger:
```bash
# Trust the self-signed certificate generated above
export SIMULATOR_CERT=cert.pem
# Override the default URL or disable verification if necessary
# export SIMULATOR_URL=https://<host-ip>:8443
# export SIMULATOR_VERIFY=false
python sensor_simulator.py
```
The script prompts for the number of nodes and sensors, then continuously emits sample data.

You can now explore the dashboard and verify that sensor updates appear in real time. Once you are comfortable on Linux, repeat the steps on a Raspberry Pi to deploy the system to hardware.

## 7. Onboard additional peers

Bring a fresh node into the network by executing the bootstrap scripts in sequence:

1. `python identity_enrollment.py` – enroll the node with the certificate authority and write its MSP materials.
2. `python channel_block_retrieval.py` – fetch the latest `mychannel` block from an existing peer.
3. `python peer_join_sync.py` – join the channel and download the current ledger state. When the script exits the peer is synchronized and ready.

## 8. Register simulator devices

Run `python sensor_simulator.py` again and supply a device count. The simulator calls the Flask API at `/register` to create device entries and then posts periodic sensor readings to `/sensor`.

## 9. Verify data on the ledger

Use the helper tools to confirm that readings were committed:

```bash
python tools/block_inspector.py --info
python tools/block_inspector.py --block 2  # show a specific block
peer channel getinfo -c mychannel         # query height via the Fabric CLI
```

The dashboard also exposes `/history` and `/integrity` pages for browsing and exporting stored data.

## 10. Interpret metrics

The web UI provides additional insight during tests:

- `/explorer` – recent block activity
- `/storage` – ledger growth
- `/status` – device and incident counts

Scripts such as `network_monitor.py` print detected LoRa nodes, while `bootstrap_status.html` summarizes the onboarding state of each peer.

## Troubleshooting

- **Certificate errors** – ensure the simulator trusts the self-signed certificate (`SIMULATOR_CERT`) or disable verification with `SIMULATOR_VERIFY=false`.
- **Channel join failures** – confirm the peer can reach the orderer and that the fetched channel block matches the target channel.
- **No data appearing** – check the Flask server logs and that the simulator is pointing at the correct URL.
