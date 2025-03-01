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
    """
    Validasi API key dari file konfigurasi
    """
    try:
        with open(CONFIG_PATH, 'r') as f:
            config = json.load(f)
        return key == config.get('api_key')
    except Exception as e:
        logger.error(f"Error validating API key: {e}")
        return False

@app.route('/api/user', methods=['POST'])
def manage_user():
    try:
        # Logging headers dan raw data
        logger.debug("Request Headers: %s", dict(request.headers))
        logger.debug("Raw Request Data: %s", request.get_data(as_text=True))
        
        # Ambil API Key dari header
        api_key = request.headers.get('Authorization')
        logger.debug("API Key: %s", api_key)
        
        # Validasi API Key
        if not validate_api_key(api_key):
            logger.error("Invalid API Key")
            return jsonify({
                'status': 'error', 
                'message': 'Invalid API Key'
            }), 403
        
        # Parse JSON
        try:
            data = request.get_json(force=True)
            logger.debug("Parsed JSON Data: %s", data)
        except Exception as json_error:
            logger.error("JSON Parsing Error: %s", json_error)
            return jsonify({
                'status': 'error', 
                'message': 'Invalid JSON data'
            }), 400
        
        # Ekstrak action
        action = data.get('action')
        
        # Validasi action
        if action not in ['add', 'delete']:
            logger.error("Invalid action: %s", action)
            return jsonify({
                'status': 'error', 
                'message': 'Invalid action'
            }), 400
        
        # Persiapkan argumen untuk subprocess
        if action == 'add':
            # Parameter untuk menambah user
            username = data.get('username')
            protocol = data.get('protocol', 'vmess')
            validity = data.get('validity', 30)
            quota = data.get('quota', 100)
            ip_limit = data.get('ip_limit', 3)
            
            # Validasi username
            if not username:
                logger.error("Username is required")
                return jsonify({
                    'status': 'error', 
                    'message': 'Username is required'
                }), 400
            
            # Validasi panjang username
            if len(username) < 3 or len(username) > 20:
                logger.error("Username length invalid")
                return jsonify({
                    'status': 'error', 
                    'message': 'Username must be 3-20 characters'
                }), 400
            
            # Jalankan subprocess untuk add user
            result = subprocess.run([
                API_SCRIPT, 
                api_key,
                action, 
                username, 
                protocol, 
                str(validity),
                str(quota),
                str(ip_limit)
            ], capture_output=True, text=True, timeout=30)
        
        elif action == 'delete':
            # Parameter untuk menghapus user
            username = data.get('username')
            protocol = data.get('protocol')
            
            # Validasi username dan protokol
            if not username or not protocol:
                logger.error("Username and protocol are required for deletion")
                return jsonify({
                    'status': 'error', 
                    'message': 'Username and protocol are required'
                }), 400
            
            # Jalankan subprocess untuk delete user
            result = subprocess.run([
                API_SCRIPT, 
                api_key,
                action, 
                username,
                protocol
            ], capture_output=True, text=True, timeout=30)
        
        # Debug subprocess
        logger.debug("Subprocess STDOUT: %s", result.stdout)
        logger.debug("Subprocess STDERR: %s", result.stderr)
        logger.debug("Return Code: %s", result.returncode)
        
        # Proses hasil subprocess
        if result.returncode == 0:
            try:
                # Coba parsing output sebagai JSON
                output_json = json.loads(result.stdout.strip())
                return jsonify({
                    'status': 'success', 
                    'output': output_json
                })
            except json.JSONDecodeError as e:
                # Jika output bukan JSON valid
                logger.error(f"JSON Parsing Error: {e}")
                logger.error(f"Raw output: {result.stdout}")
                return jsonify({
                    'status': 'error', 
                    'message': 'Gagal memproses output',
                    'raw_output': result.stdout
                }), 500
        else:
            # Subprocess gagal
            logger.error("Subprocess Error: %s", result.stderr)
            return jsonify({
                'status': 'error', 
                'message': result.stderr.strip()
            }), 500
    
    except subprocess.TimeoutExpired:
        # Tangani timeout
        logger.error("Subprocess timeout")
        return jsonify({
            'status': 'error', 
            'message': 'Operasi memakan waktu terlalu lama'
        }), 504
    
    except Exception as global_error:
        # Tangani exception global
        logger.error("Global Exception: %s", traceback.format_exc())
        return jsonify({
            'status': 'error', 
            'message': str(global_error)
        }), 500
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8082))
    app.run(host='0.0.0.0', port=port)
