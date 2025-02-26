from flask import Flask, request, jsonify
import subprocess
import json
import os
import traceback  # Tambahkan ini

app = Flask(__name__)
CONFIG_PATH = '/etc/vpn-api/config.json'
API_SCRIPT = '/etc/vpn-api/api-management.sh'

def validate_api_key(key):
    with open(CONFIG_PATH, 'r') as f:
        config = json.load(f)
    return key == config.get('api_key')

@app.route('/api/user', methods=['POST'])
def manage_user():
    try:
        # Logging tambahan
        logger.debug("Headers: %s", dict(request.headers))
        logger.debug("Raw Data: %s", request.get_data(as_text=True))
        # Debug: Cetak headers
        print("Headers:", dict(request.headers))
        
        # Debug: Cetak raw data
        print("Raw Data:", request.get_data(as_text=True))
        
        api_key = request.headers.get('Authorization')
        
        if not validate_api_key(api_key):
            return jsonify({
                'status': 'error', 
                'message': 'Invalid API Key'
            }), 403
        
        # Gunakan get_json dengan silent=True untuk debugging
        data = request.get_json(silent=True)
        
        # Debug: Cetak data yang di-parse
        print("Parsed Data:", data)
        
        if data is None:
            return jsonify({
                'status': 'error', 
                'message': 'Invalid JSON data'
            }), 400
        
        action = data.get('action')
        username = data.get('username')
        protocol = data.get('protocol', 'vmess')
        validity = data.get('validity', 30)
        
        # Tambahan input untuk quota dan IP limit
        quota = data.get('quota', 100)  # Default 100 GB
        ip_limit = data.get('ip_limit', 3)  # Default 3 IP
        
        if not username:
            return jsonify({
                'status': 'error', 
                'message': 'Username is required'
            }), 400
        
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
            logger.error("Error: %s", traceback.format_exc())
            # Cetak full traceback
            print("Exception:", traceback.format_exc())
            return jsonify({
                'status': 'error', 
                'message': str(e)
            }), 500
    
    except Exception as e:
        # Cetak full traceback untuk error di luar subprocess
        print("Global Exception:", traceback.format_exc())
        return jsonify({
            'status': 'error', 
            'message': str(e)
        }), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8082))
    app.run(host='0.0.0.0', port=port)
