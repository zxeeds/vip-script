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
    
    # Debug: Cetak headers dan data
    print("Headers:", request.headers)
    print("Data:", request.get_json())
    
    if not validate_api_key(api_key):
        return jsonify({
            'status': 'error', 
            'message': 'Invalid API Key'
        }), 403
    
    data = request.get_json()
    
    # Debug: Cetak data setelah parsing
    print("Parsed Data:", data)
    
    action = data.get('action')
    username = data.get('username')
    protocol = data.get('protocol', 'vmess')
    validity = data.get('validity', 30)
    
    # Tambahan untuk quota dan IP limit
    quota = data.get('quota', 100)
    ip_limit = data.get('ip_limit', 3)
    
    # Cetak semua parameter
    print(f"Action: {action}")
    print(f"Username: {username}")
    print(f"Protocol: {protocol}")
    print(f"Validity: {validity}")
    print(f"Quota: {quota}")
    print(f"IP Limit: {ip_limit}")
    
    try:
        result = subprocess.run([
            API_SCRIPT, 
            api_key,
            action, 
            username, 
            protocol, 
            str(validity),
            str(quota),
            str(ip_limit)
        ], capture_output=True, text=True)
        
        # Debug: Cetak output subprocess
        print("Subprocess STDOUT:", result.stdout)
        print("Subprocess STDERR:", result.stderr)
        print("Return Code:", result.returncode)
        
        if result.returncode == 0:
            return jsonify({
                'status': 'success', 
                'output': json.loads(result.stdout)
            })
        else:
            return jsonify({
                'status': 'error', 
                'message': result.stderr
            }), 500
    
    except Exception as e:
        # Debug: Cetak exception
        print("Exception:", str(e))
        return jsonify({
            'status': 'error', 
            'message': str(e)
        }), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8082))
    app.run(host='0.0.0.0', port=port)
