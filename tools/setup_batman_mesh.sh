#!/usr/bin/env bash
# Configure and monitor BATMAN-adv mesh on Raspberry Pi nodes.
# Usage:
#   sudo ./tools/setup_batman_mesh.sh install       # install dependencies and load module
#   sudo ./tools/setup_batman_mesh.sh setup <ip/cidr> [channel] [txpower_mBm]
#   ./tools/setup_batman_mesh.sh monitor            # watch neighbors
#   ./tools/setup_batman_mesh.sh latency <bat-ip>   # measure per-hop latency to neighbor
#   ./tools/setup_batman_mesh.sh failover <bat-ip>  # continuous ping for failover test

set -euo pipefail

IFACE=${IFACE:-wlan1}       # WokFi adapter dedicated to mesh
BATIF=${BATIF:-bat0}        # BATMAN-adv virtual interface
CHANNEL=${CHANNEL:-149}     # 5 GHz channel
TXPOWER_MB=${TXPOWER_MB:-2000}  # 20 dBm in mBm

usage() {
  grep '^#' "$0" | cut -c4-
  exit 1
}

install_deps() {
  sudo apt update
  sudo apt install -y batctl wireless-tools iw
  sudo modprobe batman-adv
}

setup_mesh() {
  local ip=${1:-}
  local chan=${2:-$CHANNEL}
  local power=${3:-$TXPOWER_MB}
  [[ -n "$ip" ]] || { echo "Error: provide bat0 IP (e.g., 192.168.80.1/24)."; exit 1; }

  sudo ip link set "$IFACE" down
  sudo iw dev "$IFACE" set type ibss
  sudo iw dev "$IFACE" set channel "$chan"
  sudo iw dev "$IFACE" set txpower fixed "$power"
  sudo ip link set "$IFACE" up

  sudo batctl if add "$IFACE" || true
  sudo ip link set up dev "$BATIF"
  sudo ip addr flush dev "$BATIF" >/dev/null 2>&1 || true
  sudo ip addr add "$ip" dev "$BATIF"
}

monitor_neighbors() {
  watch -n2 sudo batctl n
}

measure_latency() {
  local target=${1:-}
  [[ -n "$target" ]] || { echo "Error: provide neighbor bat0 IP."; exit 1; }
  sudo batctl ping "$target"
}

failover_test() {
  local target=${1:-}
  [[ -n "$target" ]] || { echo "Error: provide neighbor bat0 IP."; exit 1; }
  echo "Ping $target continuously. Remove a node to test reroute."
  while true; do
    if sudo batctl ping -c1 "$target" >/dev/null 2>&1; then
      printf '.'
    else
      printf 'X'
    fi
    sleep 1
  done
}

cmd=${1:-}
shift || true
case "$cmd" in
  install) install_deps ;;
  setup)   setup_mesh "$@" ;;
  monitor) monitor_neighbors ;;
  latency) measure_latency "$@" ;;
  failover) failover_test "$@" ;;
  *) usage ;;
esac
