from flask import Flask, request, jsonify
import subprocess
import json
import os
import logging
import traceback

# Konfigurasi logging
logging.basicConfig(level=logging.DEBUG, 
                    format='%(asctime)s - %(levelname)s - %(message)s',
                    handlers=[
                        logging.FileHandler('/var/log/vpn-api/debug.log'),
                        logging.StreamHandler()
                    ])
logger = logging.getLogger(__name__)

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
        # Logging headers dan raw data
        logger.debug("Request Headers: %s", dict(request.headers))
        logger.debug("Raw Request Data: %s", request.get_data(as_text=True))
        
        api_key = request.headers.get('Authorization')
        logger.debug("API Key: %s", api_key)
        
        if not validate_api_key(api_key):
            logger.error("Invalid API Key")
            return jsonify({
                'status': 'error', 
                'message': 'Invalid API Key'
            }), 403
        
        # Parse JSON dengan mode strict
        try:
            data = request.get_json(force=True)
            logger.debug("Parsed JSON Data: %s", data)
        except Exception as json_error:
            logger.error("JSON Parsing Error: %s", json_error)
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
            logger.error("Username is required")
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
            
            # Debug subprocess
            logger.debug("Subprocess STDOUT: %s", result.stdout)
            logger.debug("Subprocess STDERR: %s", result.stderr)
            logger.debug("Return Code: %s", result.returncode)
            
            if result.returncode == 0:
                return jsonify({
                    'status': 'success', 
                    'output': json.loads(result.stdout)
                })
            else:
                logger.error("Subprocess Error: %s", result.stderr)
                return jsonify({
                    'status': 'error', 
                    'message': result.stderr
                }), 500
        
        except Exception as subprocess_error:
            logger.error("Subprocess Exception: %s", traceback.format_exc())
            return jsonify({
                'status': 'error', 
                'message': str(subprocess_error)
            }), 500
    
    except Exception as global_error:
        logger.error("Global Exception: %s", traceback.format_exc())
        return jsonify({
            'status': 'error', 
            'message': str(global_error)
        }), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8082))
    app.run(host='0.0.0.0', port=port)
