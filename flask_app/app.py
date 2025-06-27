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
    list_devices,
    get_block,
    get_incidents,
    get_quarantined,
    get_attestations,
    log_security_incident,
    attest_device,
)

import threading
from incident_responder import watch as incident_watch

app = Flask(__name__)
client = ipfshttpclient.connect('/dns/localhost/tcp/5001/http')

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
            <style>
                body { font-family: Arial, sans-serif; margin: 0; padding: 0; }
                header {
                    background-color: #2c3e50;
                    color: #fff;
                    padding: 20px;
                    text-align: center;
                }
                main { padding: 40px; }
                footer {
                    background-color: #f4f4f4;
                    text-align: center;
                    padding: 10px 0;
                    position: fixed;
                    bottom: 0;
                    width: 100%;
                }
                h1 { margin: 0; }
                form { margin-bottom: 20px; }
                button { padding: 6px 12px; }
                #node-list li { margin-left: 20px; }
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
            </script>
        </head>
        <body>
        <header>
            <h1>Hyperledger Farm Dashboard</h1>
        </header>
        <main>
        <p>Registered nodes: {{count}}</p>
        <button onclick="discover()">Discover Active Nodes</button>
        <p>Active nodes: <span id="node-count">0</span></p>
        <ul id="node-list"></ul>
        <h2>Upload Sensor File</h2>
        <form action="/upload" method="post" enctype="multipart/form-data">
            <input type="file" name="file" />
            <button type="submit">Upload</button>
        </form>
        <h2>Record Sensor Data</h2>
        <form action="/sensor" method="post">
            <input name="id" placeholder="sensor id" />
            <input name="temperature" placeholder="temp" />
            <input name="humidity" placeholder="humidity" />
            <button type="submit">Send</button>
        </form>
        <h2>Merkle Tree</h2>
        <input id="block-num" placeholder="block number" />
        <button onclick="showMerkle()">Show</button>
        <p>Root: <span id="merkle-root"></span></p>
        <ul id="merkle-tree"></ul>
        </main>
        <footer>
            Hyperledger Farm Example
        </footer>
        </body>
        </html>
        """,
        count=len(nodes),
    )


@app.route('/nodes')
def nodes():
    nodes = list_devices()
    return jsonify({'count': len(nodes), 'nodes': nodes})


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


def start_blockchain():
    """Start the Fabric test network."""
    try:
        script = Path(__file__).resolve().parent.parent / 'test_network.sh'
        subprocess.Popen(['bash', str(script)])
        print('Blockchain network start initiated')
    except Exception as e:
        print('Failed to start blockchain:', e)


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
