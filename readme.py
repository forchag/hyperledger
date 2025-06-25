"""Setup guide for running the Hyperledger Farm Network on multiple Raspberry Pi's.

This script prints step-by-step instructions for installing dependencies,
setting up a Hyperledger Fabric network, and launching the example
demonstrations across two or more Raspberry Pi boards.
"""

INSTRUCTIONS = r"""
Step 1: Install prerequisites
-----------------------------
Run the following commands on **each** Raspberry Pi:

    sudo apt update
    sudo apt install -y docker.io docker-compose git golang-go python3 python3-pip
    sudo usermod -aG docker $USER
    newgrp docker

Install the Hyperledger Fabric samples and binaries:

    curl -sSL https://bit.ly/2ysbOFE | bash -s -- 2.5.0

This downloads the Fabric binaries and sample networks to `fabric-samples`.

Step 2: Clone this repository
-----------------------------
Clone the repository on one of the Pis (or all, if you plan to develop
on each):

    git clone https://example.com/hyperledger-farm.git
    cd hyperledger-farm

Step 3: Launch the Fabric test network
--------------------------------------
From the `fabric-samples/test-network` directory on a single Pi, start a
basic two organization network:

    cd fabric-samples/test-network
    ./network.sh up createChannel -ca

Deploy the sensor chaincode:

    cp -r /path/to/hyperledger-farm/chaincode/sensor ./chaincode/
    ./network.sh deployCC -ccn sensor -ccp ./chaincode/sensor -ccl go

Step 4: Configure the application
--------------------------------
Edit `flask_app/hlf_client.py` inside the repository so that it connects
using the Fabric SDK to the gateway on the Pi running the network.
Install the required Python packages:

    pip3 install flask ipfshttpclient

Step 5: Start the services
--------------------------
On the Pi hosting the Fabric network run:

    ipfs daemon &
    python3 flask_app/app.py

On each additional Pi that represents a sensor node run:

    python3 lora_node.py
    python3 network_monitor.py

You can test data upload and recovery with:

    python3 tools/data_tool.py upload sensor-1 reading.json
    python3 tools/data_tool.py verify sensor-1
    python3 tools/data_tool.py recover sensor-1

These scripts demonstrate sending sensor readings and logging heartbeat
events through the Flask API and onto the blockchain.

Step 6: Scaling to multiple Pis
-------------------------------
Repeat Step 5 on as many Pis as you like. Ensure that each node's
`hlf_client.py` is configured to reach the Fabric gateway and that the
IPs or hostnames of the nodes are reachable from each other. The test
network can be started on one Pi and the client applications run on the
others, allowing a distributed deployment.
"""

if __name__ == "__main__":
    print(INSTRUCTIONS)
