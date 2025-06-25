from flask import Flask, request, jsonify, render_template_string
import ipfshttpclient
import json
from datetime import datetime

# Placeholder for Hyperledger Fabric client imports
from hlf_client import (
    record_sensor_data,
    register_device,
    log_event,
    get_sensor_data,
    list_devices,
)

app = Flask(__name__)
client = ipfshttpclient.connect('/dns/localhost/tcp/5001/http')


@app.route('/')
def index():
    nodes = list_devices()
    return render_template_string(
        """
        <h1>Hyperledger Farm Dashboard</h1>
        <p>Registered nodes: {{count}}</p>
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
        """,
        count=len(nodes),
    )


@app.route('/nodes')
def nodes():
    nodes = list_devices()
    return jsonify({'count': len(nodes), 'nodes': nodes})

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

@app.route('/sensor', methods=['POST'])
def record_sensor():
    if request.is_json:
        data = request.get_json()
    else:
        data = request.form.to_dict()
    if not data:
        return 'Invalid payload', 400
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
    # Requires cert.pem and key.pem for TLS
    app.run(host='0.0.0.0', port=8443, ssl_context=('cert.pem', 'key.pem'))
