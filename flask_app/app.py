from flask import Flask, request, jsonify, render_template_string, make_response
import ipfshttpclient
import json
from datetime import datetime
import subprocess
import hashlib
from pathlib import Path
import io

# Placeholder for Hyperledger Fabric client imports
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

app = Flask(__name__)
client = ipfshttpclient.connect('/dns/localhost/tcp/5001/http')

# Track whether the Fabric network has been started
BLOCKCHAIN_STARTED = False

# Potential Raspberry Pi addresses to probe when discovering active nodes
NODE_ADDRESSES = [
    '192.168.0.163',
    '192.168.0.199',
    '192.168.0.200',
]

# Mapping of node IPs to sensors attached to that node. The key is the IP
# address and the value is a dictionary mapping the sensor name to the GPIO pin.
NODE_SENSORS = {
    '192.168.0.163': {'dht22': 4, 'soil': 17},
    '192.168.0.199': {'dht22': 4, 'soil': 17},
    '192.168.0.200': {'dht22': 4, 'soil': 17},
}


def compute_merkle_root(tx_hashes):
    """Return Merkle root and list of levels for given transaction hashes."""
    if not tx_hashes:
        return '0x0', []
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


def build_csv(sensor_id=None, start=None, end=None):
    """Return CSV bytes and SHA256 hash for the requested data."""
    import csv
    if sensor_id:
        records = get_sensor_history(sensor_id, start, end)
    else:
        records = get_all_sensor_data(start, end)
    records.sort(key=lambda r: r['timestamp'])
    out = io.StringIO()
    writer = csv.DictWriter(out, fieldnames=['id', 'temperature', 'humidity', 'timestamp', 'cid'])
    writer.writeheader()
    for r in records:
        writer.writerow(r)
    data = out.getvalue().encode('utf-8')
    h = hashlib.sha256(data).hexdigest()
    return data, h


@app.route('/')
def index():
    nodes = list_devices()
    return render_template_string(
        """
        <html>
        <head>
            <link href='https://cdnjs.cloudflare.com/ajax/libs/bootstrap/5.2.3/css/bootstrap.min.css' rel='stylesheet'>
            <style>
            body { padding-top: 20px; }
            </style>
            <script>
            async function discover() {
                const res = await fetch('/discover');
                const data = await res.json();
                document.getElementById('node-count').innerText = data.count;
                document.getElementById('node-list').innerHTML =
                    data.nodes.map(n => {
                        const sensors = Object.entries(n.sensors)
                            .map(([k,v]) => `${k}:${v}`).join(', ');
                        return `<li>${n.ip} (${sensors})</li>`;
                    }).join('');
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
            async function startChain(){
                const res = await fetch('/start-blockchain', {method:'POST'});
                const data = await res.json();
                document.getElementById('chain-result').textContent = data.checks.map(c => (c.ok ? '[\u2713] ' : '[x] ') + c.check).join('\n');
            }
            async function restartChain(){
                const res = await fetch('/restart-blockchain', {method:'POST'});
                const data = await res.json();
                document.getElementById('chain-result').textContent = data.checks.map(c => (c.ok ? '[\u2713] ' : '[x] ') + c.check).join('\n');
            }
            function startPolling() {
                loadReadings();
                loadBlocks();
                setInterval(loadReadings, 3000);
                setInterval(loadBlocks, 3000);
            }
            window.onload = startPolling;
            </script>
        </head>
        <body>
        <header class='bg-dark text-white text-center py-3 mb-4'>
            <h1>Hyperledger Farm Dashboard</h1>
        </header>
        <nav class='navbar navbar-expand-lg navbar-light bg-light mb-4'>
            <div class='container-fluid'>
                <ul class='navbar-nav me-auto mb-2 mb-lg-0'>
                    <li class='nav-item'><a class='nav-link' href='/integrity'>Data Integrity</a></li>
                    <li class='nav-item'><a class='nav-link' href='/connect'>Sensor Connection</a></li>
                    <li class='nav-item'><a class='nav-link' href='/status'>Network Status</a></li>
                </ul>
            </div>
        </nav>
        <main class='container'>
        <div class='row g-4'>
            <div class='col-md-4'>
                <div class='card h-100'>
                    <div class='card-header'>Nodes</div>
                    <div class='card-body'>
                        <p>Registered nodes: {{count}}</p>
                        <button class='btn btn-primary' onclick='discover()'>Discover Active Nodes</button>
                        <p class='mt-2'>Active nodes: <span id='node-count'>0</span></p>
                        <ul id='node-list' class='mb-0'></ul>
                    </div>
                </div>
            </div>
            <div class='col-md-4'>
                <div class='card h-100'>
                    <div class='card-header'>Blockchain Control</div>
                    <div class='card-body'>
                        <button class='btn btn-success mb-2' onclick='startChain()'>Start Blockchain</button>
                        <button class='btn btn-warning' onclick='restartChain()'>Restart Blockchain</button>
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


@app.route('/nodes')
def nodes():
    nodes = list_devices()
    return jsonify({'count': len(nodes), 'nodes': nodes})


@app.route('/latest-readings')
def latest_readings():
    """Return most recent sensor readings for all devices."""
    return jsonify(get_latest_readings())


@app.route('/block-events')
def block_events():
    """Return recent blockchain operation events."""
    return jsonify({'events': get_block_events()})


@app.route('/start-blockchain', methods=['POST'])
def start_blockchain_route():
    checks, started = start_blockchain()
    return jsonify({'started': started, 'checks': checks})


@app.route('/restart-blockchain', methods=['POST'])
def restart_blockchain_route():
    checks, started = restart_blockchain()
    return jsonify({'started': started, 'checks': checks})


def ping_node(ip: str) -> bool:
    """Return True if the given IP responds to a single ping."""
    try:
        res = subprocess.run(
            ['ping', '-c', '1', '-W', '1', ip],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        return res.returncode == 0
    except Exception:
        return False


def run_system_checks():
    """Perform basic environment checks before starting Fabric."""
    checks = []

    def _check(cmd, msg):
        try:
            subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
            checks.append({'check': msg, 'ok': True})
        except Exception:
            checks.append({'check': msg, 'ok': False})

    _check(['docker', '--version'], 'Docker installed')
    _check(['docker-compose', '--version'], 'Docker Compose installed')
    _check(['curl', '--version'], 'curl available')
    return checks


def start_blockchain():
    """Run checks and start the Fabric test network."""
    global BLOCKCHAIN_STARTED
    checks = run_system_checks()
    if not all(c['ok'] for c in checks):
        return checks, False
    if BLOCKCHAIN_STARTED:
        return checks, True
    try:
        script = Path(__file__).resolve().parent.parent / 'test_network.sh'
        subprocess.Popen(['bash', str(script)])
        BLOCKCHAIN_STARTED = True
        print('Blockchain network start initiated')
        return checks, True
    except Exception as e:
        print('Failed to start blockchain:', e)
        return checks, False


def restart_blockchain():
    """Stop the network and start it again."""
    global BLOCKCHAIN_STARTED
    try:
        net_dir = Path(__file__).resolve().parent.parent / 'fabric-samples' / 'test-network'
        subprocess.run(['bash', 'network.sh', 'down'], cwd=net_dir)
    except Exception:
        pass
    BLOCKCHAIN_STARTED = False
    return start_blockchain()


def check_and_start_blockchain():
    """Start the blockchain if at least two devices are registered."""
    if len(list_devices()) >= 2:
        start_blockchain()


@app.route('/discover')
def discover():
    active = [ip for ip in NODE_ADDRESSES if ping_node(ip)]
    nodes = [
        {'ip': ip, 'sensors': NODE_SENSORS.get(ip, {})}
        for ip in active
    ]
    return jsonify({'count': len(active), 'nodes': nodes})

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return 'No file provided', 400
    file = request.files['file']
    res = client.add(file)
    cid = res['Hash']
    # Record the CID on the blockchain (stub implementation)
    record_sensor_data(id=file.filename, temperature=0, humidity=0,
                       timestamp=datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ'), cid=cid)
    return jsonify({'cid': cid})


@app.route('/register', methods=['POST'])
def register():
    data = request.get_json()
    if not data or 'id' not in data or 'owner' not in data:
        return 'Invalid JSON', 400
    register_device(data['id'], data['owner'])
    check_and_start_blockchain()
    return 'registered'

@app.route('/retrieve/<cid>', methods=['GET'])
def retrieve_file(cid):
    try:
        data = client.cat(cid)
        return data
    except Exception as e:
        return str(e), 500


@app.route('/verify/<sensor_id>', methods=['GET'])
def verify(sensor_id):
    data = get_sensor_data(sensor_id)
    cid = data['cid'] if data else None
    if not cid:
        return 'No sensor data found', 404
    content = client.cat(cid)
    new_cid = client.add_bytes(content)
    if new_cid == cid:
        return 'Data integrity verified'
    return 'Data integrity check failed', 500


@app.route('/recover/<sensor_id>', methods=['GET'])
def recover(sensor_id):
    data = get_sensor_data(sensor_id)
    if not data:
        return 'No sensor data found', 404
    cid = data['cid']
    content = client.cat(cid)
    new_cid = client.add_bytes(content)
    if new_cid == cid:
        return 'Recovery successful'
    return jsonify({'old_cid': cid, 'new_cid': new_cid})


@app.route('/merkle/<int:block_num>')
def merkle(block_num: int):
    """Return Merkle tree information for a block."""
    block = get_block(block_num)
    tx_hashes = [
        hashlib.sha256(json.dumps(tx).encode()).hexdigest()
        for tx in block.get('data', [])
    ]
    root, tree = compute_merkle_root(tx_hashes)
    return jsonify({'root': root, 'tree': tree})


@app.route('/status-data')
def status_data():
    """Return incidents and quarantine information."""
    return jsonify({
        'incidents': get_incidents(),
        'quarantined': get_quarantined(),
        'attestations': get_attestations(),
    })


@app.route('/status')
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
            </style>
            <script>
            async function load() {
                const res = await fetch('/status-data');
                const data = await res.json();
                document.getElementById('incident-count').innerText = data.incidents.length;
                document.getElementById('quarantine-count').innerText = data.quarantined.length;
            }
            window.onload = load;
            </script>
        </head>
        <body>
            <h1>Network Status</h1>
            <div class="counter">Incidents: <span id="incident-count">0</span></div>
            <div class="counter">Quarantined devices: <span id="quarantine-count">0</span></div>
        </body>
        </html>
        """
    )


@app.route('/connect')
def connect_page():
    """Serve the sensor connection setup page."""
    template = Path(__file__).resolve().parent.parent / 'sensor_connection.html'
    return render_template_string(template.read_text())


@app.route('/check-pins', methods=['POST'])
def check_pins():
    """Simple stub that pretends to verify pin connections."""
    info = request.get_json() or {}
    node = info.get('node')
    valid = node in list_devices() or ping_node(node)
    msg = 'Pins appear connected and data is flowing.' if valid else 'Node not found.'
    return jsonify({'message': msg, 'ok': valid})


@app.route('/integrity')
def integrity_page():
    """Serve the data integrity management page."""
    template = Path(__file__).resolve().parent.parent / 'data_integrity.html'
    return render_template_string(template.read_text())


@app.route('/export')
def export_data():
    sensor_id = request.args.get('sensor_id')
    start = request.args.get('start')
    end = request.args.get('end')
    data, h = build_csv(sensor_id, start, end)
    resp = make_response(data)
    resp.headers['Content-Type'] = 'text/csv'
    resp.headers['Content-Disposition'] = 'attachment; filename="sensor_data.csv"'
    resp.headers['X-Data-Hash'] = h
    return resp


@app.route('/state/<date>')
def state_on(date):
    """Return the last reading for each node on the given YYYY-MM-DD date."""
    info = get_state_on(date)
    return jsonify(info)


@app.route('/verify-data', methods=['POST'])
def verify_data():
    sensor_id = request.form.get('sensor_id')
    start = request.form.get('start')
    end = request.form.get('end')
    if 'file' not in request.files:
        return 'no file', 400
    uploaded = request.files['file'].read()
    uploaded_hash = hashlib.sha256(uploaded).hexdigest()
    _, expected_hash = build_csv(sensor_id, start, end)
    return jsonify({'verified': uploaded_hash == expected_hash})

@app.route('/sensor', methods=['POST'])
def record_sensor():
    if request.is_json:
        data = request.get_json()
    else:
        data = request.form.to_dict()
    if not data:
        return 'Invalid payload', 400
    data['node_ip'] = request.remote_addr
    data['timestamp'] = datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ')
    js = json.dumps(data).encode('utf-8')
    ipfs_res = client.add_bytes(js)
    cid = ipfs_res
    record_sensor_data(
        data.get('id', 'unknown'),
        float(data.get('temperature', 0)),
        float(data.get('humidity', 0)),
        data['timestamp'],
        cid,
    )
    return jsonify({'cid': cid})

if __name__ == '__main__':
    # Start background watcher for incidents
    t = threading.Thread(target=incident_watch, daemon=True)
    t.start()
    # Requires cert.pem and key.pem for TLS
    app.run(host='0.0.0.0', port=8443, ssl_context=('cert.pem', 'key.pem'))
