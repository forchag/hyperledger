#!/bin/bash
# Helper script to launch the Hyperledger Fabric test network with the
# sensor chaincode. Run from the repository root on a Raspberry Pi.
set -e

# Download Fabric samples if not already present
if [ ! -d fabric-samples/test-network ]; then
    echo "Downloading Hyperledger Fabric samples..."
    curl -sSL https://bit.ly/2ysbOFE | bash -s -- 2.5.0
fi

# Vendor Go dependencies so the peer can package the chaincode offline
(cd chaincode/sensor && go mod vendor)
(cd chaincode/agri && go mod vendor)

cd fabric-samples/test-network

# Ensure any previous test network is removed to prevent channel conflicts
./network.sh down

# Start the network and create a channel
./network.sh up createChannel -ca

# Deploy the sensor chaincode from this repository
cp -r ../../chaincode/sensor ./chaincode/
./network.sh deployCC -ccn sensor -ccp ./chaincode/sensor -ccl go
cp -r ../../chaincode/agri ./chaincode/
./network.sh deployCC -ccn agri -ccp ./chaincode/agri -ccl go

