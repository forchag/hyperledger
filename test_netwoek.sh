#!/bin/bash
# Helper script to launch the Hyperledger Fabric test network with the
# sensor chaincode. Run from the repository root on a Raspberry Pi.
set -e

# Download Fabric samples if not already present
if [ ! -d fabric-samples/test-network ]; then
    echo "Downloading Hyperledger Fabric samples..."
    curl -sSL https://bit.ly/2ysbOFE | bash -s -- 2.5.0
fi

cd fabric-samples/test-network

# Start the network and create a channel
./network.sh up createChannel -ca

# Deploy the sensor chaincode from this repository
cp -r ../../chaincode/sensor ./chaincode/
./network.sh deployCC -ccn sensor -ccp ./chaincode/sensor -ccl go

echo "Fabric test network started with sensor chaincode deployed."
