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

# Ensure Docker starts on boot
if ! systemctl is-enabled --quiet docker; then
  echo "🔧 Enabling Docker to start on boot..."
  sudo systemctl enable docker
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

# Ensure compose override is available and always used
OVERRIDE_COMPOSE="${TEST_NET_DIR}/compose/docker-compose-test-net-override.yaml"
cp "${REPO_ROOT}/docker-compose-test-net-override.yaml" "${OVERRIDE_COMPOSE}" 2>/dev/null || true
NETWORK_SCRIPT="${TEST_NET_DIR}/network.sh"
if [[ -f "${NETWORK_SCRIPT}" ]] && ! grep -q "docker-compose-test-net-override.yaml" "${NETWORK_SCRIPT}"; then
  cp "${NETWORK_SCRIPT}" "${NETWORK_SCRIPT}.bak"
  sed -i '/COMPOSE_FILES="/s/"$/ -f compose\/docker-compose-test-net-override.yaml"/' "${NETWORK_SCRIPT}"
fi

# ---- Ledger storage ----
LEDGER_DIR="${FABRIC_LEDGER_DIR:-${HOME}/fabric-ledger}"
mkdir -p "${LEDGER_DIR}"/{orderer.example.com,peer0.org1.example.com,peer0.org2.example.com,couchdb0,couchdb1,ca_org1,ca_org2,ca_orderer}
uid="${SUDO_UID:-$(id -u)}"
gid="${SUDO_GID:-$(id -g)}"
chown -R "${uid}:${gid}" "${LEDGER_DIR}"
export FABRIC_LEDGER_DIR="${LEDGER_DIR}"

COMPOSE_TEST_NET="${TEST_NET_DIR}/compose/compose-test-net.yaml"
COMPOSE_COUCH="${TEST_NET_DIR}/compose/compose-couch.yaml"
ldir_esc=${LEDGER_DIR//\//\\}
if [[ -f "${COMPOSE_TEST_NET}" ]]; then
  sed -i "s|orderer.example.com:/var/hyperledger/production/orderer|${ldir_esc}/orderer.example.com:/var/hyperledger/production/orderer|" "${COMPOSE_TEST_NET}"
  sed -i "s|peer0.org1.example.com:/var/hyperledger/production|${ldir_esc}/peer0.org1.example.com:/var/hyperledger/production|" "${COMPOSE_TEST_NET}"
  sed -i "s|peer0.org2.example.com:/var/hyperledger/production|${ldir_esc}/peer0.org2.example.com:/var/hyperledger/production|" "${COMPOSE_TEST_NET}"
fi
if [[ -f "${COMPOSE_COUCH}" ]]; then
  if ! grep -q "${ldir_esc}/couchdb0" "${COMPOSE_COUCH}"; then
    sed -i "/container_name: couchdb0/a\    volumes:\n      - ${ldir_esc}/couchdb0:/opt/couchdb/data" "${COMPOSE_COUCH}"
  fi
  if ! grep -q "${ldir_esc}/couchdb1" "${COMPOSE_COUCH}"; then
    sed -i "/container_name: couchdb1/a\    volumes:\n      - ${ldir_esc}/couchdb1:/opt/couchdb/data" "${COMPOSE_COUCH}"
  fi
fi

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
