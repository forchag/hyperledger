#!/usr/bin/env bash
# Launch Hyperledger Fabric test network and deploy chaincode(s) from THIS repo.
# Run from the repository root (NO sudo). Works with Docker (snap or apt).
set -Eeuo pipefail
trap 'echo "❌ Error on line $LINENO. Exiting."; exit 1' ERR

########################
# Basic safety checks  #
########################
if [[ "${PWD}" =~ [[:space:]] ]]; then
  echo "Error: repository path contains spaces. Move the project to a directory with no spaces."
  exit 1
fi
if [[ "${EUID}" -eq 0 ]]; then
  echo "Error: do NOT run this script with sudo."
  exit 1
fi
command -v docker >/dev/null 2>&1 || { echo "Error: docker not found in PATH."; exit 1; }

########################
# Docker connectivity  #
########################
if ! docker info >/dev/null 2>&1; then
  if [[ "${DOCKER_HOST:-}" != "" ]]; then
    echo "⚠️  docker not reachable via DOCKER_HOST=${DOCKER_HOST}. Trying default socket…"
    unset DOCKER_HOST || true
  fi
fi
docker info >/dev/null 2>&1 || { echo "Error: cannot talk to Docker. Is the daemon running?"; exit 1; }

# Ensure Docker starts on boot
if ! systemctl is-enabled --quiet docker; then
  echo "🔧 Enabling Docker to start on boot..."
  sudo systemctl enable docker
fi

########################################
# Paths                                 #
########################################
REPO_ROOT="$(realpath "$(dirname "$0")")"
TEST_NET_DIR="${REPO_ROOT}/fabric-samples/test-network"
CC_SENSOR="${REPO_ROOT}/chaincode/sensor"         # Go chaincode path (absolute)
CC_AGRI="${REPO_ROOT}/chaincode/agri"             # optional
[[ -d "${CC_SENSOR}" ]] || { echo "Error: ${CC_SENSOR} does not exist."; exit 1; }

########################################
# Fabric image tags (match 2.5/1.5)     #
########################################
export IMAGE_TAG="${IMAGE_TAG:-2.5}"
export CA_IMAGE_TAG="${CA_IMAGE_TAG:-1.5}"

########################################
# Helper: compare Go versions           #
########################################
ver_ge() { # ver_ge 1.20 1.18 -> true
  # simple semver (major.minor[.patch]) compare
  local IFS=.
  local -a A=($1) B=($2)
  for ((i=${#A[@]}; i<3; i++)); do A[i]=0; done
  for ((i=${#B[@]}; i<3; i++)); do B[i]=0; done
  (( A[0]>B[0] )) || { (( A[0]<B[0] )) && return 1; }
  (( A[0]==B[0] )) && { (( A[1]>B[1] )) || { (( A[1]<B[1] )) && return 1; }
    (( A[1]==B[1] )) && { (( A[2]>=B[2] )) || return 1; }; }
  return 0
}

########################################
# Auto-install/upgrade Go if needed     #
########################################
ensure_go() {
  # find highest required go version from chaincodes' go.mod
  local need="1.20" v
  for dir in "${CC_SENSOR}" "${CC_AGRI}"; do
    [[ -d "$dir" && -f "$dir/go.mod" ]] || continue
    v="$(grep -Eo '^go[[:space:]]+[0-9]+\.[0-9]+' "$dir/go.mod" | awk '{print $2}' | head -n1 || true)"
    [[ -n "$v" ]] && ver_ge "$v" "$need" && need="$v"
  done

  # detect current go version (if any)
  local have=""
  if command -v go >/dev/null 2>&1; then
    have="$(go version | awk '{print $3}' | sed 's/^go//')"
  fi

  if [[ -z "$have" || ! $(ver_ge "$have" "$need"; echo $?) -eq 0 ]]; then
    echo "🔧 Go toolchain upgrade: need >= ${need}${have:+, found $have}"
    # install locally (no sudo) under ~/.local/go and put it on PATH for this session
    local GO_VER="${GO_VER_OVERRIDE:-$need}"
    # use an official recent patch for the needed minor (e.g., 1.20 -> 1.20.14). Default to latest known if not provided.
    case "$GO_VER" in
      1.20) GO_VER="1.20.14" ;;
      1.21) GO_VER="1.21.13" ;;
      1.22) GO_VER="1.22.5" ;;
      1.23) GO_VER="1.23.0" ;;  # adjust as needed
      *)    GO_VER="$GO_VER" ;;
    esac
    local ARCH="linux-amd64" # your machine is x86_64; change if needed
    local TARBALL="go${GO_VER}.${ARCH}.tar.gz"
    local DEST="${HOME}/.local"
    mkdir -p "${DEST}"
    echo "⬇️  Downloading Go ${GO_VER}…"
    curl -fsSL "https://go.dev/dl/${TARBALL}" -o "/tmp/${TARBALL}"
    echo "📦 Installing to ${DEST}/go …"
    rm -rf "${DEST}/go"
    tar -C "${DEST}" -xzf "/tmp/${TARBALL}"
    export PATH="${DEST}/go/bin:${PATH}"
    hash -r
    go version || { echo "Error: Go install failed."; exit 1; }
    echo "✅ Using $(go version)"
  else
    echo "✅ Go $(go version | awk '{print $3}') satisfies requirement (>= ${need})"
  fi

  # make module cache writeable (prevents future permission hiccups)
  go env -w GOMODCACHE="${HOME}/go/pkg/mod"
  go env -w GOTOOLCHAIN=local || true   # avoid auto-download surprises
  export GOFLAGS=-modcacherw
}

ensure_go

########################################
# Get fabric-samples if missing         #
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

# Ensure compose override is available and included
OVERRIDE_COMPOSE="${TEST_NET_DIR}/compose/docker-compose-test-net-override.yaml"
cp "${REPO_ROOT}/docker-compose-test-net-override.yaml" "${OVERRIDE_COMPOSE}" 2>/dev/null || true
if ! grep -q "docker-compose-test-net-override.yaml" "${TEST_NET_DIR}/network.sh"; then
  sed -i '/COMPOSE_FILES="-f compose\/${COMPOSE_FILE_BASE} -f compose\/${CONTAINER_CLI}\/${CONTAINER_CLI}-${COMPOSE_FILE_BASE}"/a\  COMPOSE_FILES="${COMPOSE_FILES} -f compose/docker-compose-test-net-override.yaml"' "${TEST_NET_DIR}/network.sh"
fi

# ---- Ledger storage ----
LEDGER_DIR="${FABRIC_LEDGER_DIR:-${HOME}/fabric-ledger}"
mkdir -p "${LEDGER_DIR}"/{orderer.example.com,peer0.org1.example.com,peer0.org2.example.com,couchdb0,couchdb1,ca_org1,ca_org2,ca_orderer}
uid="$(id -u)"
gid="$(id -g)"
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

########################################
# Vendor Go deps                        #
########################################
echo "🔧 Vendoring Go dependencies for sensor chaincode…"
pushd "${CC_SENSOR}" >/dev/null
go mod tidy
go mod vendor
popd >/dev/null

if [[ -d "${CC_AGRI}" ]]; then
  echo "🔧 Vendoring Go dependencies for agri chaincode…"
  pushd "${CC_AGRI}" >/dev/null
  go mod tidy
  go mod vendor
  popd >/dev/null
fi

########################################
# Bring network down/up & deploy        #
########################################
pushd "${TEST_NET_DIR}" >/dev/null
echo "🧹 Bringing any existing test network down…"
./network.sh down

echo "🚀 Bringing network up with CAs and creating channel…"
./network.sh up createChannel -ca

echo "📦 Deploying sensor chaincode from: ${CC_SENSOR}"
./network.sh deployCC -c mychannel -ccn sensor -ccl go -ccp "${CC_SENSOR}"

if [[ -d "${CC_AGRI}" ]]; then
  echo "📦 Deploying agri chaincode from: ${CC_AGRI}"
  ./network.sh deployCC -c mychannel -ccn agri -ccl go -ccp "${CC_AGRI}"
fi

echo "✅ All done. Channel 'mychannel' created, chaincode(s) deployed."
popd >/dev/null
