#!/usr/bin/env bash
# Start Hyperledger Fabric test network after a reboot.
# Ensures Docker daemon is running, brings network up, and redeploys chaincode
# found in this repository.

set -Eeuo pipefail
trap 'echo "❌ Error on line $LINENO. Exiting."; exit 1' ERR

# ---- Docker daemon ----
if ! systemctl is-active --quiet docker; then
  echo "🔧 Starting Docker daemon..."
  sudo systemctl start docker
fi

# Ensure Docker is reachable (handle stray DOCKER_HOST)
if ! docker info >/dev/null 2>&1; then
  if [[ -n "${DOCKER_HOST:-}" ]]; then
    echo "⚠️  Docker not reachable via DOCKER_HOST=${DOCKER_HOST}. Trying default socket..."
    unset DOCKER_HOST || true
  fi
fi

docker info >/dev/null 2>&1 || { echo "Error: cannot talk to Docker. Is the daemon running?"; exit 1; }

# ---- Paths ----
REPO_ROOT="$(realpath "$(dirname "$0")")"
TEST_NET_DIR="${REPO_ROOT}/fabric-samples/test-network"
CC_SENSOR="${REPO_ROOT}/chaincode/sensor"
CC_AGRI="${REPO_ROOT}/chaincode/agri"

# ---- Bring network up ----
pushd "${TEST_NET_DIR}" >/dev/null
./network.sh up
popd >/dev/null

# ---- Deploy chaincode(s) if paths exist ----
if [[ -d "${CC_SENSOR}" ]]; then
  pushd "${TEST_NET_DIR}" >/dev/null
  ./network.sh deployCC -c mychannel -ccn sensor -ccl go -ccp "${CC_SENSOR}"
  popd >/dev/null
fi

if [[ -d "${CC_AGRI}" ]]; then
  pushd "${TEST_NET_DIR}" >/dev/null
  ./network.sh deployCC -c mychannel -ccn agri -ccl go -ccp "${CC_AGRI}"
  popd >/dev/null
fi

echo "✅ Fabric test network started with chaincode."
