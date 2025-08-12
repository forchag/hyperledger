#!/usr/bin/env bash
# Launch Hyperledger Fabric test network and deploy chaincode(s) from THIS repo.
# Run from the repository root (no sudo). Works with Docker (snap or apt).
set -Eeuo pipefail

###############
# Nice errors #
###############
trap 'echo "❌ Error on line $LINENO. Exiting."; exit 1' ERR

########################
# Basic safety checks  #
########################
if [[ "${PWD}" =~ [[:space:]] ]]; then
  echo "Error: repository path contains spaces. Move the project to a directory with no spaces."
  exit 1
fi

if [[ "${EUID}" -eq 0 ]]; then
  echo "Error: do NOT run this script with sudo. It creates root-owned files and breaks Go packaging."
  exit 1
fi

command -v docker >/dev/null 2>&1 || { echo "Error: docker not found in PATH."; exit 1; }
command -v go >/dev/null 2>&1 || { echo "Error: Go not installed (need Go 1.20+)."; exit 1; }

########################
# Docker connectivity  #
########################
# Prefer the standard socket; if DOCKER_HOST points to a dead snap socket, unset it.
if ! docker info >/dev/null 2>&1; then
  if [[ "${DOCKER_HOST:-}" != "" ]]; then
    echo "⚠️  docker not reachable via DOCKER_HOST=${DOCKER_HOST}. Trying default socket…"
    unset DOCKER_HOST || true
  fi
fi

# Final check
docker info >/dev/null 2>&1 || { echo "Error: cannot talk to Docker. Is the daemon running?"; exit 1; }

########################################
# Resolve absolute paths & chaincodes  #
########################################
REPO_ROOT="$(realpath "$(dirname "$0")")"
TEST_NET_DIR="${REPO_ROOT}/fabric-samples/test-network"

CC_SENSOR="${REPO_ROOT}/chaincode/sensor"   # Go chaincode path (absolute)
CC_AGRI="${REPO_ROOT}/chaincode/agri"       # Optional second chaincode

[[ -d "${CC_SENSOR}" ]] || { echo "Error: ${CC_SENSOR} does not exist."; exit 1; }

########################################
# Align Fabric image versions (optional
# but recommended; matches local 2.5)  #
########################################
# You can override these before running the script if you want different tags.
export IMAGE_TAG="${IMAGE_TAG:-2.5}"
export CA_IMAGE_TAG="${CA_IMAGE_TAG:-1.5}"

########################################
# Get fabric-samples if missing        #
########################################
if [[ ! -d "${TEST_NET_DIR}" ]]; then
  echo "📦 fabric-samples/test-network not found — fetching samples…"
  if curl -sSL https://bit.ly/2ysbOFE -o /tmp/fabric-bootstrap.sh \
     && bash /tmp/fabric-bootstrap.sh 2.5.0; then
    echo "✅ Downloaded fabric-samples via bootstrap."
  else
    echo "⚠️  Bootstrap script failed; cloning fabric-samples from GitHub…"
    git clone --depth 1 https://github.com/hyperledger/fabric-samples.git "${REPO_ROOT}/fabric-samples"
  fi
fi

########################################
# Vendor Go deps for deterministic pkg #
########################################
echo "🔧 Vendoring Go dependencies for sensor chaincode…"
pushd "${CC_SENSOR}" >/dev/null
go mod tidy
# Make module cache group-writable to avoid future permission issues
export GOFLAGS=-modcacherw
go mod vendor
popd >/dev/null

if [[ -d "${CC_AGRI}" ]]; then
  echo "🔧 Vendoring Go dependencies for agri chaincode…"
  pushd "${CC_AGRI}" >/dev/null
  go mod tidy
  export GOFLAGS=-modcacherw
  go mod vendor
  popd >/dev/null
fi

########################################
# Bring network down cleanly           #
########################################
pushd "${TEST_NET_DIR}" >/dev/null
echo "🧹 Bringing any existing test network down…"
./network.sh down

########################################
# Bring network up + create channel    #
########################################
echo "🚀 Bringing network up with CAs and creating channel…"
./network.sh up createChannel -ca

########################################
# Deploy chaincode(s) with ABS paths   #
########################################
echo "📦 Deploying sensor chaincode from: ${CC_SENSOR}"
./network.sh deployCC \
  -c mychannel \
  -ccn sensor \
  -ccl go \
  -ccp "${CC_SENSOR}"

if [[ -d "${CC_AGRI}" ]]; then
  echo "📦 Deploying agri chaincode from: ${CC_AGRI}"
  ./network.sh deployCC \
    -c mychannel \
    -ccn agri \
    -ccl go \
    -ccp "${CC_AGRI}"
fi

echo "✅ All done. Peers and orderer are up, channel 'mychannel' created, chaincode(s) deployed."
popd >/dev/null

