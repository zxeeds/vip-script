from flask import Flask, request, jsonify
import subprocess
import json
import os
import logging
import traceback
import re

# Konfigurasi logging
logging.basicConfig(
    level=logging.DEBUG, 
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/var/log/vpn-api/debug.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Path konfigurasi
CONFIG_PATH = '/etc/vpn-api/config.json'

# Protokol yang didukung
SUPPORTED_PROTOCOLS = ['vmess', 'vless', 'trojan', 'ssh']

# Mapping protokol ke script
PROTOCOL_SCRIPTS = {
    'vmess': '/usr/local/sbin/add-vme',
    'vless': '/usr/local/sbin/add-vle',
    'trojan': '/usr/local/sbin/add-tro',
    'ssh': '/usr/local/sbin/add-ssh'
}

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

def validate_username(username, protocol=None):
    """
    Validasi username dengan aturan berbeda untuk setiap protokol
    """
    # Validasi umum
    if not username or len(username) < 3 or len(username) > 20:
        return False
    
    # Hanya huruf, angka, dan underscore
    if not re.match(r'^[a-zA-Z0-9_]+$', username):
        return False
    
    return True

def validate_password(password):
    """
    Validasi password untuk protokol yang membutuhkan
    """
    # Minimal 8 karakter
    return password and len(password) >= 8

@app.route('/api/user', methods=['POST'])
def manage_user():
    try:
        # Logging headers dan raw data
        logger.debug(f"Request Headers: {dict(request.headers)}")
        logger.debug(f"Raw Request Data: {request.get_data(as_text=True)}")
        
        # Ambil API Key dari header
        api_key = request.headers.get('Authorization')
        logger.debug(f"API Key: {api_key}")
        
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
            logger.debug(f"Parsed JSON Data: {data}")
        except Exception as json_error:
            logger.error(f"JSON Parsing Error: {json_error}")
            return jsonify({
                'status': 'error', 
                'message': 'Invalid JSON data'
            }), 400
        
        # Tentukan action
        action = data.get('action', 'add').lower()
        
        # Validasi protokol
        protocol = data.get('protocol', 'vmess').lower()
        if protocol not in SUPPORTED_PROTOCOLS:
            logger.error(f"Protokol tidak didukung: {protocol}")
            return jsonify({
                'status': 'error', 
                'message': f'Protokol {protocol} tidak didukung. Protokol yang didukung: {", ".join(SUPPORTED_PROTOCOLS)}'
            }), 400
        
        # Validasi username
        username = data.get('username')
        if not validate_username(username, protocol):
            logger.error("Username invalid")
            return jsonify({
                'status': 'error', 
                'message': 'Username harus 3-20 karakter (huruf, angka, underscore)'
            }), 400
        
        # Siapkan argumen untuk subprocess
        if action == 'add':
            # Parameter untuk protokol SSH berbeda
            if protocol == 'ssh':
                # Validasi password khusus SSH
                password = data.get('password')
                if not validate_password(password):
                    logger.error("Password invalid untuk SSH")
                    return jsonify({
                        'status': 'error', 
                        'message': 'Password harus minimal 8 karakter'
                    }), 400
                
                # Argumen untuk SSH
                subprocess_args = [
                    PROTOCOL_SCRIPTS[protocol], 
                    username, 
                    password,
                    str(data.get('ip_limit', 2)),  # Default 2 IP
                    str(data.get('validity', 30)),  # Default 30 hari
                    str(data.get('quota', 0))  # Default 0 GB
                ]
            else:
                # Argumen untuk protokol Xray
                subprocess_args = [
                    PROTOCOL_SCRIPTS[protocol], 
                    username, 
                    str(data.get('quota', 100)),  # Default 100 GB
                    str(data.get('ip_limit', 3)),  # Default 3 IP
                    str(data.get('validity', 30))  # Default 30 hari
                ]
            
            # Jalankan subprocess untuk add user
            result = subprocess.run(
                subprocess_args, 
                capture_output=True, 
                text=True, 
                timeout=60
            )
        
        elif action == 'delete':
            # Jalankan subprocess untuk delete user
            result = subprocess.run([
                f'/usr/local/sbin/del-{protocol}', 
                username
            ], capture_output=True, text=True, timeout=30)
        
        else:
            logger.error(f"Invalid action: {action}")
            return jsonify({
                'status': 'error', 
                'message': 'Invalid action. Gunakan "add" atau "delete"'
            }), 400
        
        # Debug subprocess
        logger.debug(f"Subprocess STDOUT: {result.stdout}")
        logger.debug(f"Subprocess STDERR: {result.stderr}")
        logger.debug(f"Return Code: {result.returncode}")
        
        # Proses hasil subprocess
        if result.returncode == 0:
            try:
                # Coba parsing output sebagai JSON
                output_json = json.loads(result.stdout.strip())
                return jsonify({
                    'status': 'success', 
                    'output': output_json
                })
            except json.JSONDecodeError:
                # Jika output bukan JSON valid
                logger.error(f"Output tidak dapat di-parse: {result.stdout}")
                return jsonify({
                    'status': 'success', 
                    'output': {
                        'message': 'User berhasil diproses',
                        'raw_output': result.stdout
                    }
                })
        else:
            # Subprocess gagal
            logger.error(f"Subprocess Error: {result.stderr}")
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
        logger.error(f"Global Exception: {traceback.format_exc()}")
        return jsonify({
            'status': 'error', 
            'message': str(global_error)
        }), 500

@app.route('/api/protocols', methods=['GET'])
def list_protocols():
    """
    Endpoint untuk menampilkan protokol yang didukung
    """
    return jsonify({
        'status': 'success',
        'protocols': SUPPORTED_PROTOCOLS
    })

if __name__ == '__main__':
    # Pastikan bind ke semua interface
    app.run(host='0.0.0.0', port=8082, debug=True)
