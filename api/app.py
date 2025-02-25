from flask import Flask, request, jsonify
import subprocess
import json
import os

app = Flask(__name__)

CONFIG_PATH = '/etc/vpn-api/config.json'
API_SCRIPT = '/etc/vpn-api/api-management.sh'

def validate_api_key(key):
    with open(CONFIG_PATH, 'r') as f:
        config = json.load(f)
    return key == config.get('api_key')

@app.route('/api/user', methods=['POST'])
def manage_user():
    api_key = request.headers.get('Authorization')
    
    if not validate_api_key(api_key):
        return jsonify({
            'status': 'error', 
            'message': 'Invalid API Key'
        }), 403
    
    data = request.json
    action = data.get('action')
    username = data.get('username')
    protocol = data.get('protocol', 'vmess')
    validity = data.get('validity', 30)
    
    if not username:
        return jsonify({
            'status': 'error', 
            'message': 'Username is required'
        }), 400
    
    try:
        result = subprocess.run([
            API_SCRIPT, 
            action, 
            username, 
            protocol, 
            str(validity)
        ], capture_output=True, text=True)
        
        if result.returncode == 0:
            return jsonify({
                'status': 'success', 
                'output': result.stdout
            })
        else:
            return jsonify({
                'status': 'error', 
                'message': result.stderr
            }), 500
    
    except Exception as e:
        return jsonify({
            'status': 'error', 
            'message': str(e)
        }), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8081))
    app.run(host='0.0.0.0', port=8081)
