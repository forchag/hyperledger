# Getting Started

Follow these steps to set up the Hyperledger Farm Network on a new Linux node using a Python virtual environment.

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
Install the packages needed by the dashboard and simulator:
```bash
pip install flask cryptography
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
python sensor_simulator.py
```
The script prompts for the number of nodes and sensors, then continuously emits sample data.

You can now explore the dashboard and verify that sensor updates appear in real time. Once you are comfortable on Linux, repeat the steps on a Raspberry Pi to deploy the system to hardware.
