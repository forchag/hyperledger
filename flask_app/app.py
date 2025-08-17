"""Flask interface for the Hyperledger agricultural demo.

This application previously depended on a ``MockBlockchain`` class from the
``nft_traceability`` module. The traceability utilities were later refactored
to expose a real in-memory ledger named :class:`TraceabilityLedger`, and the
mock class was removed. Importing the old name caused ``ImportError`` during
application start-up. The import and the instantiation below are updated to
use ``TraceabilityLedger`` so the application aligns with the current
traceability implementation.
"""

from flask import Flask, request, jsonify, render_template_string, make_response
import json
import base64
from datetime import datetime
import subprocess
import shutil
import hashlib
from pathlib import Path
import io
import sys
import time
import re

# Ensure the project root is on the module search path so local modules
# such as ``incident_responder`` can be imported when running this file
# directly.
sys.path.append(str(Path(__file__).resolve().parents[1]))

# Placeholder for Hyperledger Fabric client imports
import hlf_client
from hlf_client import (
    record_sensor_data,
    register_device,
    log_event,
    get_sensor_data,
    get_sensor_history,
    get_all_sensor_data,
    get_state_on,
    get_latest_readings,
    list_devices,
    get_block,
    get_incidents,
    get_quarantined,
    get_attestations,
    get_block_events,
    log_security_incident,
    attest_device,
)

import threading
from incident_responder import watch as incident_watch
from nft_traceability import AgriNFT, TraceabilityLedger, verify_product
from sensor_simulator import build_mapping
from identity_enrollment import enroll_identity
from channel_block_retrieval import fetch_channel_block

app = Flask(__name__)

# Track whether the Fabric network has been started
BLOCKCHAIN_STARTED = False

# Store recent HTTP access events
ACCESS_LOG = []


TRACE_CHAIN = TraceabilityLedger()
TRACE_CHAIN.add_nft(
    AgriNFT(
        token_id=1,
        produce_type="Tomato",
        harvest_date=20250730,
        zone_ids=[12, 18],
        merkle_roots=["0x3a7f...", "0x8c2d..."],
        quality_score=98,
        storage_conditions="4-8C",
    )
)


@app.before_request
def log_access():
    """Record basic request info for the access log."""
    ACCESS_LOG.append(
        {
            "time": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
            "path": request.path,
        }
    )
    if len(ACCESS_LOG) > 50:
        del ACCESS_LOG[0]


# Mapping of node identifiers to their IP addresses and attached sensors.  The
# structure mirrors the output of ``sensor_simulator.build_mapping`` and is
# populated dynamically when the simulator is launched so that the web
# interface always reflects the active virtual topology.
NODE_MAP = {}


def compute_merkle_root(tx_hashes):
    """Return Merkle root and list of levels for given transaction hashes."""
    if not tx_hashes:
        return "0x0", []
    level = tx_hashes[:]
    tree = [level]
    while len(level) > 1:
        next_level = []
        for i in range(0, len(level), 2):
            left = level[i]
            right = level[i + 1] if i + 1 < len(level) else left
            m = hashlib.sha256((left + right).encode()).hexdigest()
            next_level.append(m)
        level = next_level
        tree.append(level)
    return level[0], tree


def _group_devices(devices):
    """Group individual sensor IDs into Raspberry Pi nodes.

    Sensors are registered using identifiers in the form ``<node>_<sensor>``.
    The dashboard, however, operates at the node level.  This helper collapses
    the flat list of device IDs returned by :func:`list_devices` into a
    structure describing each node and its attached sensors.
    """

    nodes = {}
    for dev in devices:
        if "_" in dev:
            node, sensor = dev.split("_", 1)
        else:
            node, sensor = dev, "unknown"
        nodes.setdefault(node, {})[sensor] = sensor
    return nodes


def _apply_mapping(mapping):
    """Store the simulator mapping for later discovery requests."""
    NODE_MAP.clear()
    NODE_MAP.update(mapping)


def build_csv(sensor_id=None, start=None, end=None):
    """Return CSV bytes and SHA256 hash for the requested data."""
    import csv

    if sensor_id:
        records = get_sensor_history(sensor_id, start, end)
    else:
        records = get_all_sensor_data(start, end)
    records.sort(key=lambda r: r["timestamp"])
    out = io.StringIO()
    writer = csv.DictWriter(
        out, fieldnames=["id", "temperature", "humidity", "timestamp", "payload"]
    )
    writer.writeheader()
    for r in records:
        writer.writerow(r)
    data = out.getvalue().encode("utf-8")
    h = hashlib.sha256(data).hexdigest()
    return data, h


@app.route("/")
def index():
    devices = list_devices()
    nodes = _group_devices(devices)
    return render_template_string(
        """
        <html>
        <head>
            <link href='https://cdnjs.cloudflare.com/ajax/libs/bootstrap/5.2.3/css/bootstrap.min.css' rel='stylesheet'>
            <style>
            body { padding-top: 20px; }
            </style>
            <script>
            async function loadNodes() {
                try {
                    const res = await fetch('/nodes');
                    const raw = await res.json();
                    const nodes = Array.isArray(raw.nodes) ? raw.nodes : [];
                    document.getElementById('node-count').innerText = raw.count ?? nodes.length;
                    document.getElementById('node-list').innerHTML =
                        nodes.map(n => {
                            const ip = n.ip || n.id || n;
                            const sensors = n.sensors ? n.sensors.join(', ') : '';
                            return `<li>${ip}${sensors ? ' (' + sensors + ')' : ''}</li>`;
                        }).join('');
                } catch (err) {
                    console.error('Load nodes failed:', err);
                    document.getElementById('node-count').innerText = '0';
                    document.getElementById('node-list').innerHTML = '';
                }
            }
            async function showMerkle() {
                const num = document.getElementById('block-num').value;
                if(!num) return;
                const res = await fetch('/merkle/' + num);
                const data = await res.json();
                document.getElementById('merkle-root').innerText = data.root;
                const levels = data.tree.map(l => '<li>' + l.join(', ') + '</li>').join('');
                document.getElementById('merkle-tree').innerHTML = levels;
            }
            async function loadReadings() {
                const res = await fetch('/latest-readings');
                const data = await res.json();
                const rows = Object.entries(data).map(([id,r]) =>
                    `<tr><td>${id}</td><td>${r.temperature}</td><td>${r.humidity}</td><td>${r.timestamp}</td></tr>`
                ).join('');
                document.getElementById('sensor-body').innerHTML = rows;
            }
            async function loadBlocks() {
                const res = await fetch('/block-events');
                const data = await res.json();
                const rows = data.events.map(e =>
                    `<tr><td>${e.time}</td><td>${e.message}</td></tr>`
                ).join('');
                document.getElementById('block-body').innerHTML = rows;
            }
            function formatChainResponse(data){
                let msg = data.started ? 'Blockchain started' : 'Blockchain not running';
                if(!data.started && data.error){ msg += ': ' + data.error; }
                const checks = data.checks.map(c => (c.ok ? '[\u2713] ' : '[x] ') + c.check).join('\n');
                return msg + '\n' + checks;
            }
            async function startChain(){
                const res = await fetch('/start-blockchain', {method:'POST'});
                const data = await res.json();
                const result = document.getElementById('chain-result');
                const alertBox = document.getElementById('chain-alert');
                result.textContent = formatChainResponse(data);
                if(!data.started && data.error){
                    alertBox.textContent = data.error;
                    alertBox.classList.remove('d-none');
                } else {
                    alertBox.classList.add('d-none');
                }
            }
            async function restartChain(){
                const res = await fetch('/restart-blockchain', {method:'POST'});
                const data = await res.json();
                const result = document.getElementById('chain-result');
                const alertBox = document.getElementById('chain-alert');
                result.textContent = formatChainResponse(data);
                if(!data.started && data.error){
                    alertBox.textContent = data.error;
                    alertBox.classList.remove('d-none');
                } else {
                    alertBox.classList.add('d-none');
                }
            }
            function startPolling() {
                loadNodes();
                loadReadings();
                loadBlocks();
                setInterval(loadNodes, 3000);
                setInterval(loadReadings, 3000);
                setInterval(loadBlocks, 3000);
            }
            document.addEventListener('DOMContentLoaded', () => {
                document.getElementById('start-chain-btn').addEventListener('click', startChain);
                document.getElementById('restart-chain-btn').addEventListener('click', restartChain);
                startPolling();
            });
            </script>
        </head>
        <body>
        <header class='bg-dark text-white text-center py-3 mb-4'>
            <h1>AgriCrypt-Chain Farm Dashboard</h1>
        </header>
        <nav class='navbar navbar-expand-lg navbar-light bg-light mb-4'>
            <div class='container-fluid'>
                <ul class='navbar-nav me-auto mb-2 mb-lg-0'>
                    <li class='nav-item'><a class='nav-link' href='/integrity'>Data Integrity</a></li>
                    <li class='nav-item'><a class='nav-link' href='/connect'>Sensor Connection</a></li>
                    <li class='nav-item'><a class='nav-link' href='/status'>Network Status</a></li>
                    <li class='nav-item'><a class='nav-link' href='/tde'>Threat Detection</a></li>
                    <li class='nav-item'><a class='nav-link' href='/history'>Sensor History</a></li>
                    <li class='nav-item'><a class='nav-link' href='/explorer'>Blockchain Explorer</a></li>
                    <li class='nav-item'><a class='nav-link' href='/devices'>Device Management</a></li>
                    <li class='nav-item'><a class='nav-link' href='/storage'>Storage Monitor</a></li>
                    <li class='nav-item'><a class='nav-link' href='/recovery'>Recovery</a></li>
                    <li class='nav-item'><a class='nav-link' href='/diagnostics'>Node Diagnostics</a></li>
                    <li class='nav-item'><a class='nav-link' href='/access-log'>Access Log</a></li>
                </ul>
            </div>
        </nav>
        <main class='container'>
        <div class='row g-4'>
            <div class='col-md-4'>
                <div class='card h-100'>
                    <div class='card-header'>Nodes</div>
                    <div class='card-body'>
                        <p>Registered nodes: <span id='node-count'>{{count}}</span></p>
                        <ul id='node-list' class='mb-0'></ul>
                    </div>
                </div>
            </div>
            <div class='col-md-4'>
                <div class='card h-100'>
                    <div class='card-header'>Blockchain Control</div>
                    <div class='card-body'>
                        <button class='btn btn-success mb-2' id='start-chain-btn'>Start Blockchain</button>
                        <button class='btn btn-warning' id='restart-chain-btn'>Restart Blockchain</button>
                        <div id='chain-alert' class='alert alert-danger d-none mt-2' role='alert'></div>
                        <pre id='chain-result' class='mt-2'></pre>
                    </div>
                </div>
            </div>
            <div class='col-md-8'>
                <div class='card h-100'>
                    <div class='card-header'>Latest Sensor Readings</div>
                    <div class='card-body p-0'>
                        <table class='table table-sm mb-0'>
                            <thead>
                                <tr><th>Sensor</th><th>Temperature</th><th>Humidity</th><th>Timestamp</th></tr>
                            </thead>
                            <tbody id='sensor-body'></tbody>
                        </table>
                    </div>
                </div>
            </div>
            <div class='col-md-6'>
                <div class='card h-100'>
                    <div class='card-header'>Blockchain Events</div>
                    <div class='card-body p-0'>
                        <table class='table table-sm mb-0'>
                            <thead>
                                <tr><th>Time</th><th>Event</th></tr>
                            </thead>
                            <tbody id='block-body'></tbody>
                        </table>
                    </div>
                </div>
            </div>
            <div class='col-md-6'>
                <div class='card h-100'>
                    <div class='card-header'>Merkle Tree</div>
                    <div class='card-body'>
                        <input id='block-num' class='form-control mb-2' placeholder='block number'/>
                        <button class='btn btn-secondary' onclick='showMerkle()'>Show</button>
                        <p class='mt-2'>Root: <span id='merkle-root'></span></p>
                        <ul id='merkle-tree'></ul>
                    </div>
                </div>
            </div>
        </div>
        </main>
        <script src='https://cdnjs.cloudflare.com/ajax/libs/bootstrap/5.2.3/js/bootstrap.bundle.min.js'></script>
        </body>
        </html>
        """,
        count=len(nodes),
    )


@app.route("/nodes")
def nodes():
    devices = list_devices()
    grouped = _group_devices(devices)
    node_list = []
    for node_id, sensors in grouped.items():
        info = NODE_MAP.get(node_id, {})
        node_list.append(
            {
                "id": node_id,
                "ip": info.get("ip", node_id),
                "sensors": list(sensors.keys()),
            }
        )
    return jsonify({"count": len(node_list), "nodes": node_list})


@app.route("/latest-readings")
def latest_readings():
    """Return most recent sensor readings for all devices."""
    return jsonify(get_latest_readings())


@app.route("/block-events")
def block_events():
    """Return recent blockchain operation events."""
    return jsonify({"events": get_block_events()})


@app.route("/start-blockchain", methods=["POST"])
def start_blockchain_route():
    checks, started, error = start_blockchain()
    return jsonify({"started": started, "checks": checks, "error": error})


@app.route("/restart-blockchain", methods=["POST"])
def restart_blockchain_route():
    checks, started, error = restart_blockchain()
    return jsonify({"started": started, "checks": checks, "error": error})


@app.route("/health")
def health():
    """Simple health probe for monitoring."""
    return jsonify({"status": "ok"}), 200


def ping_node(ip: str) -> bool:
    """Return True if the given IP responds to a single ping."""
    try:
        res = subprocess.run(
            ["ping", "-c", "1", "-W", "1", ip],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        return res.returncode == 0
    except Exception:
        return False


def _has_cmd(cmd: str) -> bool:
    """Return True if ``cmd`` is found on PATH."""
    return shutil.which(cmd) is not None


def _can_run(args) -> bool:
    """Return True if executing ``args`` succeeds."""
    try:
        subprocess.run(
            args, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True
        )
        return True
    except Exception:
        return False


def compose_cmd():
    """Return the Docker Compose command if available."""
    if _has_cmd("docker") and _can_run(["docker", "compose", "version"]):
        return ["docker", "compose"]
    if _has_cmd("docker-compose") and _can_run(["docker-compose", "version"]):
        return ["docker-compose"]
    return None


def _container_running(name: str) -> bool:
    """Return True if the given Docker container is running."""
    try:
        result = subprocess.run(
            ["docker", "inspect", "-f", "{{.State.Running}}", name],
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
            check=False,
        )
        return result.stdout.strip() == "true"
    except Exception:
        return False


def _ledger_height(peer: str):
    """Return the ledger height for ``peer`` on ``mychannel`` or ``None``."""
    try:
        result = subprocess.run(
            [
                "docker",
                "exec",
                peer,
                "peer",
                "channel",
                "getinfo",
                "-c",
                "mychannel",
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
            check=False,
        )
        if result.returncode != 0:
            return None
        match = re.search(r"height: (\d+)", result.stdout)
        return int(match.group(1)) if match else None
    except Exception:
        return None


def _chaincode_committed(name: str) -> bool:
    """Return True if ``name`` chaincode is committed on ``mychannel``."""
    try:
        result = subprocess.run(
            [
                "docker",
                "exec",
                "peer0.org1.example.com",
                "peer",
                "lifecycle",
                "chaincode",
                "querycommitted",
                "-C",
                "mychannel",
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
            check=False,
        )
        return result.returncode == 0 and f"Name: {name}," in result.stdout
    except Exception:
        return False


def ensure_admin_enrollment(net_dir: Path) -> None:
    """Ensure admin identities have valid MSP/TLS credentials."""

    enroll_identity(
        "admin",
        "http://localhost:7054",
        net_dir
        / "organizations/peerOrganizations/org1.example.com/users/Admin@org1.example.com/msp",
        net_dir
        / "organizations/peerOrganizations/org1.example.com/users/Admin@org1.example.com/tls",
        "peer0.org1.example.com:7051",
        "orderer.example.com:7050",
        secret="adminpw",
    )
    enroll_identity(
        "admin",
        "http://localhost:8054",
        net_dir
        / "organizations/peerOrganizations/org2.example.com/users/Admin@org2.example.com/msp",
        net_dir
        / "organizations/peerOrganizations/org2.example.com/users/Admin@org2.example.com/tls",
        "peer0.org2.example.com:9051",
        "orderer.example.com:7050",
        secret="adminpw",
    )


def run_system_checks():
    """Ensure the Fabric test network is running and healthy."""
    checks = []

    docker_ok = _can_run(["docker", "--version"])
    checks.append({"check": "Docker installed", "ok": docker_ok})

    compose_ok = compose_cmd() is not None
    checks.append({"check": "Docker Compose installed", "ok": compose_ok})

    if not docker_ok or not compose_ok:
        return checks, False

    root = Path(__file__).resolve().parent.parent
    net_dir = root / "fabric-samples" / "test-network"
    start_script = root / "test_network.sh"

    # Start network if core containers are not running
    if not _container_running("orderer.example.com"):
        subprocess.run(
            ["bash", str(start_script)],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        time.sleep(3)

    # Verify container health
    orderer_ok = _container_running("orderer.example.com")
    peer1_ok = _container_running("peer0.org1.example.com")
    peer2_ok = _container_running("peer0.org2.example.com")
    ca1_ok = _container_running("ca_org1")
    ca2_ok = _container_running("ca_org2")
    couch0_ok = _container_running("couchdb0")
    couch1_ok = _container_running("couchdb1")
    checks.append({"check": "Orderer reachable", "ok": orderer_ok})
    checks.append({"check": "Peer0.org1 active", "ok": peer1_ok})
    checks.append({"check": "Peer0.org2 active", "ok": peer2_ok})
    checks.append({"check": "CA org1 reachable", "ok": ca1_ok})
    checks.append({"check": "CA org2 reachable", "ok": ca2_ok})
    checks.append(
        {"check": "CouchDB instances reachable", "ok": couch0_ok and couch1_ok}
    )

    try:
        ensure_admin_enrollment(net_dir)
        identities_ok = all(
            [
                (
                    net_dir
                    / "organizations/peerOrganizations/org1.example.com/users/Admin@org1.example.com/msp"
                ).exists(),
                (
                    net_dir
                    / "organizations/peerOrganizations/org2.example.com/users/Admin@org2.example.com/msp"
                ).exists(),
            ]
        )
    except Exception:
        identities_ok = False
    checks.append({"check": "Identities enrolled", "ok": identities_ok})

    # Ensure channel exists
    channel_ok = False
    h1 = _ledger_height("peer0.org1.example.com")
    h2 = _ledger_height("peer0.org2.example.com")
    if h1 is None or h2 is None:
        subprocess.run(
            ["bash", "network.sh", "createChannel", "-c", "mychannel"],
            cwd=net_dir,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        time.sleep(2)
        h1 = _ledger_height("peer0.org1.example.com")
        h2 = _ledger_height("peer0.org2.example.com")
    channel_ok = h1 is not None and h2 is not None
    checks.append({"check": "Channel mychannel exists", "ok": channel_ok})

    # Retrieve the channel configuration block so that subsequent components can
    # join the channel without relying on out-of-band distribution of the
    # genesis file.  Failures are captured in the checks list but do not abort
    # the health run.
    block_ok = False
    if channel_ok:
        ca_cert = (
            net_dir
            / "organizations"
            / "ordererOrganizations"
            / "example.com"
            / "msp"
            / "tlscacerts"
            / "tlsca.example.com-cert.pem"
        )
        dest = net_dir / "channel-artifacts" / "mychannel.block"
        try:
            fetch_channel_block("mychannel", "orderer.example.com:7050", ca_cert, dest)
            block_ok = True
        except Exception:
            block_ok = False
    checks.append({"check": "Channel config block fetched", "ok": block_ok})

    ledger_ok = channel_ok and h1 == h2 and h1 is not None
    checks.append({"check": "Ledger synchronized", "ok": ledger_ok})

    # Ensure required chaincodes are committed
    cc_sensor = _chaincode_committed("sensor")
    if not cc_sensor and (root / "chaincode/sensor").is_dir():
        subprocess.run(
            [
                "bash",
                "network.sh",
                "deployCC",
                "-c",
                "mychannel",
                "-ccn",
                "sensor",
                "-ccl",
                "go",
                "-ccp",
                str(root / "chaincode/sensor"),
            ],
            cwd=net_dir,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        cc_sensor = _chaincode_committed("sensor")
    checks.append({"check": "Chaincode sensor committed", "ok": cc_sensor})

    cc_agri = True
    if (root / "chaincode/agri").is_dir():
        cc_agri = _chaincode_committed("agri")
        if not cc_agri:
            subprocess.run(
                [
                    "bash",
                    "network.sh",
                    "deployCC",
                    "-c",
                    "mychannel",
                    "-ccn",
                    "agri",
                    "-ccl",
                    "go",
                    "-ccp",
                    str(root / "chaincode/agri"),
                ],
                cwd=net_dir,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            cc_agri = _chaincode_committed("agri")
        checks.append({"check": "Chaincode agri committed", "ok": cc_agri})

    all_ok = all(c["ok"] for c in checks)
    return checks, all_ok


def start_blockchain():
    """Run checks and ensure the Fabric test network is ready."""
    global BLOCKCHAIN_STARTED
    checks, ok = run_system_checks()
    if not ok:
        return checks, False, "Baseline checks failed"
    BLOCKCHAIN_STARTED = True
    return checks, True, None


def restart_blockchain():
    """Stop the network and start it again."""
    global BLOCKCHAIN_STARTED
    try:
        net_dir = (
            Path(__file__).resolve().parent.parent / "fabric-samples" / "test-network"
        )
        subprocess.run(["bash", "network.sh", "down"], cwd=net_dir)
    except Exception:
        pass
    BLOCKCHAIN_STARTED = False
    return start_blockchain()


def check_and_start_blockchain():
    """Start the blockchain if at least two devices are registered."""
    if len(list_devices()) >= 2:
        start_blockchain()


@app.route("/announce", methods=["POST"])
def announce():
    """Record a node broadcast of its address."""
    data = request.get_json() or {}
    node_id = data.get("id")
    ip = data.get("ip")
    port = data.get("port")
    if not node_id or not ip or port is None:
        return "Invalid JSON", 400
    info = NODE_MAP.get(node_id, {})
    info.update({"ip": ip, "port": port})
    NODE_MAP[node_id] = info
    return jsonify({"status": "announced"})


@app.route("/upload", methods=["POST"])
def upload_file():
    if "file" not in request.files:
        return "No file provided", 400
    file = request.files["file"]
    data = base64.b64encode(file.read()).decode("utf-8")
    payload = {
        "filename": file.filename,
        "data": data,
    }
    record_sensor_data(
        id=file.filename,
        temperature=0,
        humidity=0,
        soil_moisture=0,
        ph=0,
        light=0,
        water_level=0,
        timestamp=datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
        payload=payload,
    )
    return jsonify({"stored": True})


@app.route("/register", methods=["POST"])
def register():
    data = request.get_json()
    if not data or "id" not in data or "owner" not in data:
        return "Invalid JSON", 400
    if data["id"] not in list_devices():
        register_device(data["id"], data["owner"])
        check_and_start_blockchain()
    return "registered"


@app.route("/retrieve/<device_id>", methods=["GET"])
def retrieve_file(device_id):
    data = get_sensor_data(device_id)
    if not data or "payload" not in data:
        return "No sensor data found", 404
    payload = hlf_client.decrypt_payload(data["payload"])
    return jsonify(payload)


@app.route("/verify/<sensor_id>", methods=["GET"])
def verify(sensor_id):
    data = get_sensor_data(sensor_id)
    if not data or "payload" not in data:
        return "No sensor data found", 404
    payload = hlf_client.decrypt_payload(data["payload"])
    return jsonify({"valid": bool(payload)})


@app.route("/recover/<sensor_id>", methods=["GET"])
def recover(sensor_id):
    data = get_sensor_data(sensor_id)
    if not data or "payload" not in data:
        return "No sensor data found", 404
    payload = hlf_client.decrypt_payload(data["payload"])
    return jsonify(payload)


@app.route("/merkle/<int:block_num>")
def merkle(block_num: int):
    """Return Merkle tree information for a block."""
    block = get_block(block_num)
    tx_hashes = [
        hashlib.sha256(json.dumps(tx).encode()).hexdigest()
        for tx in block.get("data", [])
    ]
    root, tree = compute_merkle_root(tx_hashes)
    return jsonify({"root": root, "tree": tree})


@app.route("/status-data")
def status_data():
    """Return incidents and quarantine information."""
    return jsonify(
        {
            "incidents": get_incidents(),
            "quarantined": get_quarantined(),
            "attestations": get_attestations(),
        }
    )


@app.route("/status")
def status_page():
    """Display current incidents and quarantine status."""
    return render_template_string(
        """
        <html>
        <head>
            <style>
            body { font-family: Arial, sans-serif; padding: 20px; }
            h1 { color: #2c3e50; }
            .counter { font-size: 1.2em; margin-bottom: 10px; }
            #node-list { margin-top: 10px; }
            </style>
            <script>
            async function load() {
                const res = await fetch('/status-data');
                const data = await res.json();
                document.getElementById('incident-count').innerText = data.incidents.length;
                document.getElementById('quarantine-count').innerText = data.quarantined.length;

                const nodeRes = await fetch('/nodes');
                const rawNodes = await nodeRes.json();
                const nodes = Array.isArray(rawNodes.nodes) ? rawNodes.nodes : [];
                document.getElementById('node-count').innerText = nodes.length;
                document.getElementById('node-list').innerHTML =
                    nodes.map(n => {
                        const ip = n.ip || n.id || n;
                        const sensors = n.sensors ? n.sensors.join(', ') : '';
                        return `<li>${ip}${sensors ? ' (' + sensors + ')' : ''}</li>`;
                    }).join('');
            }
            window.onload = load;
            </script>
        </head>
        <body>
            <h1>Network Status</h1>
            <div class="counter">Incidents: <span id="incident-count">0</span></div>
            <div class="counter">Quarantined devices: <span id="quarantine-count">0</span></div>
            <div class="counter">Connected nodes: <span id="node-count">0</span></div>
            <ul id="node-list"></ul>
        </body>
        </html>
        """
    )


@app.route("/connect")
def connect_page():
    """Serve the sensor connection setup page."""
    template = Path(__file__).resolve().parent.parent / "sensor_connection.html"
    return render_template_string(template.read_text())


@app.route("/simulate-ui")
def simulator_page():
    """Serve the sensor simulator page."""
    template = Path(__file__).resolve().parent.parent / "sensor_simulator.html"
    return render_template_string(template.read_text())


@app.route("/simulate", methods=["POST"])
def start_simulation():
    """Launch the sensor simulator with the provided configuration."""
    config = request.get_json() or {}
    root = Path(__file__).resolve().parent.parent
    cfg = root / "simulator_config.json"
    cfg.write_text(json.dumps(config))
    mapping = build_mapping(config)
    _apply_mapping(mapping)
    script = root / "sensor_simulator.py"
    # Use the current Python executable instead of a hard-coded "python" string
    # to avoid FileNotFoundError on systems where only ``python3`` is installed.
    subprocess.Popen([sys.executable, str(script), str(cfg)])
    return jsonify({"status": "started", "mapping": mapping})


@app.route("/simulation-state")
def simulation_state():
    """Return the current simulator mapping if available."""
    root = Path(__file__).resolve().parent.parent
    cfg = root / "simulator_config.json"
    if not cfg.exists():
        return jsonify({"mapping": None})
    try:
        config = json.loads(cfg.read_text())
    except Exception:
        return jsonify({"mapping": None})
    mapping = build_mapping(config)
    _apply_mapping(mapping)
    return jsonify({"mapping": mapping})


@app.route("/tde")
def tde_page():
    """Show threat detection incidents."""
    template = Path(__file__).resolve().parent.parent / "threat_detection.html"
    return render_template_string(template.read_text())


@app.route("/check-pins", methods=["POST"])
def check_pins():
    """Simple stub that pretends to verify pin connections."""
    info = request.get_json() or {}
    node = info.get("node")
    valid = node in list_devices() or ping_node(node)
    msg = "Pins appear connected and data is flowing." if valid else "Node not found."
    return jsonify({"message": msg, "ok": valid})


@app.route("/integrity")
def integrity_page():
    """Serve the data integrity management page."""
    template = Path(__file__).resolve().parent.parent / "data_integrity.html"
    return render_template_string(template.read_text())


@app.route("/export")
def export_data():
    sensor_id = request.args.get("sensor_id")
    start = request.args.get("start")
    end = request.args.get("end")
    data, h = build_csv(sensor_id, start, end)
    resp = make_response(data)
    resp.headers["Content-Type"] = "text/csv"
    resp.headers["Content-Disposition"] = 'attachment; filename="sensor_data.csv"'
    resp.headers["X-Data-Hash"] = h
    return resp


@app.route("/state/<date>")
def state_on(date):
    """Return the last reading for each node on the given YYYY-MM-DD date."""
    info = get_state_on(date)
    return jsonify(info)


@app.route("/verify-data", methods=["POST"])
def verify_data():
    sensor_id = request.form.get("sensor_id")
    start = request.form.get("start")
    end = request.form.get("end")
    if "file" not in request.files:
        return "no file", 400
    uploaded = request.files["file"].read()
    uploaded_hash = hashlib.sha256(uploaded).hexdigest()
    _, expected_hash = build_csv(sensor_id, start, end)
    return jsonify({"verified": uploaded_hash == expected_hash})


@app.route("/backlog")
def backlog_stats():
    """Expose counts of buffered readings per device."""
    return jsonify(hlf_client.get_backlog_stats())


@app.route("/sensor", methods=["POST"])
def record_sensor():
    if request.is_json:
        data = request.get_json()
    else:
        data = request.form.to_dict()
    if not data:
        return "Invalid payload", 400
    data["node_ip"] = request.remote_addr
    if data.get("id") and data["id"] not in list_devices():
        register_device(data["id"], data["node_ip"])
        check_and_start_blockchain()
    data["timestamp"] = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
    seq = int(data.get("seq", 0))
    record_sensor_data(
        data.get("id", "unknown"),
        seq,
        float(data.get("temperature", 0)),
        float(data.get("humidity", 0)),
        float(data.get("soil_moisture", 0)),
        float(data.get("ph", 0)),
        float(data.get("light", 0)),
        float(data.get("water_level", 0)),
        data["timestamp"],
        data,
    )
    return jsonify({"stored": True})


# ----------------- Additional dashboard pages -----------------


@app.route("/history")
def history_page():
    template = Path(__file__).resolve().parent.parent / "history_view.html"
    return render_template_string(template.read_text())


@app.route("/history-data")
def history_data():
    """Return history for a sensor plus the full list of available sensors.

    The list combines registered devices and any sensors that have submitted
    data, ensuring test and simulated sensors are exposed in the UI.
    """
    sensor_id = request.args.get("sensor_id")
    # Include sensors with recorded data even if never formally registered
    all_ids = sorted(set(list_devices()) | set(hlf_client.SENSOR_DATA.keys()))
    if not sensor_id:
        sensor_id = all_ids[0] if all_ids else None
    records = get_sensor_history(sensor_id) if sensor_id else []
    return jsonify({"sensors": all_ids, "records": records})


@app.route("/explorer")
def explorer_page():
    template = Path(__file__).resolve().parent.parent / "block_explorer.html"
    return render_template_string(template.read_text())


@app.route("/blockchain-info")
def blockchain_info():
    return jsonify({"events": get_block_events()})


@app.route("/devices")
def devices_page():
    template = Path(__file__).resolve().parent.parent / "device_management.html"
    return render_template_string(template.read_text())


@app.route("/device-data")
def device_data():
    devices = []
    q = set(get_quarantined())
    for dev in list_devices():
        hist = get_sensor_history(dev)
        last = hist[-1]["timestamp"] if hist else ""
        devices.append({"id": dev, "quarantined": dev in q, "last": last})
    return jsonify({"devices": devices})


@app.route("/quarantine/<device_id>", methods=["POST", "DELETE"])
def quarantine_route(device_id):
    if request.method == "POST":
        hlf_client.quarantine_device(device_id)
    else:
        hlf_client.QUARANTINED.discard(device_id)
    return "ok"


@app.route("/storage")
def storage_page():
    template = Path(__file__).resolve().parent.parent / "storage_monitor.html"
    return render_template_string(template.read_text())


@app.route("/storage-data")
def storage_data():
    out = []
    for dev in list_devices():
        for rec in get_sensor_history(dev):
            payload = rec.get("payload")
            if isinstance(payload, dict):
                cid = payload.get("cid")
            else:
                cid = payload
            out.append({"id": dev, "cid": cid, "timestamp": rec.get("timestamp")})
    return jsonify(out)


@app.route("/recovery")
def recovery_page():
    template = Path(__file__).resolve().parent.parent / "recovery_dashboard.html"
    return render_template_string(template.read_text())


@app.route("/simulate-recovery", methods=["POST"])
def simulate_recovery():
    count = sum(len(get_sensor_history(d)) for d in list_devices())
    return jsonify({"message": f"Replicated {count} records"})


@app.route("/bootstrap")
def bootstrap_page():
    template = Path(__file__).resolve().parent.parent / "bootstrap_status.html"
    return render_template_string(template.read_text())


@app.route("/bootstrap-status")
def bootstrap_status():
    status_file = Path(__file__).resolve().parent.parent / "bootstrap_status.json"
    if status_file.exists():
        return jsonify(json.loads(status_file.read_text()))
    return jsonify({"ready": False})


@app.route("/verify-product/<int:nft_id>")
def verify_product_route(nft_id):
    try:
        result = verify_product(nft_id, TRACE_CHAIN)
    except KeyError:
        return jsonify({"error": "NFT not found"}), 404
    return jsonify({"nft_id": nft_id, "result": result})


@app.route("/diagnostics")
def diagnostics_page():
    template = Path(__file__).resolve().parent.parent / "node_diagnostics.html"
    return render_template_string(template.read_text())


@app.route("/access-log")
def access_log_page():
    template = Path(__file__).resolve().parent.parent / "access_log.html"
    return render_template_string(template.read_text())


@app.route("/access-data")
def access_data():
    return jsonify(ACCESS_LOG)


if __name__ == "__main__":
    # Start background watcher for incidents
    t = threading.Thread(target=incident_watch, daemon=True)
    t.start()
    # Requires cert.pem and key.pem for TLS
    app.run(host="0.0.0.0", port=8443, ssl_context=("cert.pem", "key.pem"))
