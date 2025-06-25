from flask import Flask, request, jsonify
import ipfshttpclient
import json
from datetime import datetime

# Placeholder for Hyperledger Fabric client imports
from hlf_client import record_sensor_data, register_device, log_event

app = Flask(__name__)
client = ipfshttpclient.connect('/dns/localhost/tcp/5001/http')


@app.route('/')
def index():
    return "<h1>Hyperledger Farm</h1>"

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
    # Placeholder that would query ledger and fetch file from IPFS
    log_event(sensor_id, 'verify', datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ'))
    return 'verification scheduled'

@app.route('/sensor', methods=['POST'])
def record_sensor():
    data = request.get_json()
    if not data:
        return 'Invalid JSON', 400
    data['timestamp'] = datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ')
    js = json.dumps(data).encode('utf-8')
    ipfs_res = client.add_bytes(js)
    cid = ipfs_res
    record_sensor_data(data['id'], data['temperature'], data['humidity'], data['timestamp'], cid)
    return jsonify({'cid': cid})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)