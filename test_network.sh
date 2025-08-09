#!/bin/bash
# Helper script to launch the Hyperledger Fabric test network with the
# sensor chaincode. Run from the repository root on a Raspberry Pi.
set -e

# Download Fabric samples if not already present
if [ ! -d fabric-samples/test-network ]; then
    echo "Downloading Hyperledger Fabric samples..."
    # The official bootstrap script is hosted behind a URL shortener that may be
    # blocked in restricted environments. Attempt to download and run the script
    # first; if that fails, clone the samples directly from GitHub as a fallback.
    if curl -sSL https://bit.ly/2ysbOFE -o /tmp/fabric-bootstrap.sh \
        && bash /tmp/fabric-bootstrap.sh 2.5.0; then
        echo "Fabric samples downloaded via bootstrap script"
    else
        echo "Bootstrap script failed, cloning from GitHub..."
        git clone --depth 1 https://github.com/hyperledger/fabric-samples.git
    fi
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

