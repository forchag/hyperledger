#!/usr/bin/env bash
# Run a full end-to-end demo: start Fabric, bootstrap peer, send sample data and inspect ledger.

set -Eeuo pipefail

REPO_ROOT="$(realpath "$(dirname "$0")")"
cd "$REPO_ROOT"

# 1. Start the local Fabric network and deploy chaincode
./test_network.sh

# 2. Bootstrap the default peer using provided config
if [[ -f bootstrap_config.json ]]; then
  python node_bootstrap.py --config bootstrap_config.json || true
fi

# 3. Emit a few simulated readings (certificate verification disabled for demo)
TMP_CFG=$(mktemp)
cat >"$TMP_CFG" <<'JSON'
{
  "nodes": [
    {"id": "demo-node", "sensors": ["dht22", "light", "ph", "soil", "water"]}
  ]
}
JSON
SIMULATOR_CONFIG="$TMP_CFG" SIMULATOR_VERIFY=false timeout 10 python sensor_simulator.py || true

# 4. Display block height and ledger information
python tools/block_inspector.py --info || true

echo "Dashboard available at https://127.0.0.1:8443/"
