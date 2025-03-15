#!/usr/bin/env python3
from flask import Flask, request, jsonify
import subprocess
import json
import os
import logging
import traceback
import re
from logging.handlers import RotatingFileHandler

# Konfigurasi logging dengan rotasi file
def setup_logging():
    log_dir = '/var/log/vpn-api'
    os.makedirs(log_dir, exist_ok=True)
    log_path = os.path.join(log_dir, 'debug.log')
    
    # Siapkan handler dengan rotasi
    file_handler = RotatingFileHandler(
        log_path, 
        maxBytes=10 * 1024 * 1024,  # 10 MB
        backupCount=5
    )
    
    # Konfigurasi format log
    formatter = logging.Formatter(
        '%(asctime)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s'
    )
    file_handler.setFormatter(formatter)
    
    # Setup logger
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.DEBUG)
    logger.addHandler(file_handler)
    
    # Tambahkan handler console untuk development
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    return logger

# Inisialisasi logger
logger = setup_logging()

# Path konfigurasi
CONFIG_PATH = '/etc/vpn-api/config.json'

# Baca konfigurasi
def load_config():
    try:
        # Tambahkan print untuk debugging
        print(f"Mencoba membaca konfigurasi dari {CONFIG_PATH}")
        
        with open(CONFIG_PATH, 'r') as f:
            config = json.load(f)
        
        print("Konfigurasi berhasil dibaca")
        
        # Validasi struktur konfigurasi
        required_keys = ['api_key', 'allowed_ips', 'protocols_allowed']
        for key in required_keys:
            if key not in config:
                print(f"Missing key: {key}")
                raise ValueError(f"Konfigurasi missing key: {key}")
        
        return config
    except Exception as e:
        # Tambahkan print untuk debugging
        print(f"Error membaca konfigurasi: {e}")
        logger.error(f"Error membaca konfigurasi: {e}")
        return {}

# Load konfigurasi global
CONFIG = load_config()

# Protokol yang didukung
SUPPORTED_PROTOCOLS = CONFIG.get('protocols_allowed', ['vmess', 'vless', 'trojan', 'ssh'])

# Mapping protokol ke script
PROTOCOL_SCRIPTS = {
    'vmess': {
        'add': '/usr/local/sbin/add-vme',
        'delete': '/usr/local/sbin/del-vme'
    },
    'vless': {
        'add': '/usr/local/sbin/add-vle', 
        'delete': '/usr/local/sbin/del-vle'
    },
    'trojan': {
        'add': '/usr/local/sbin/add-tro',
        'delete': '/usr/local/sbin/del-tro'
    },
    'ssh': {
        'add': '/usr/local/sbin/add-ssh',
        'delete': '/usr/local/sbin/del-ssh'
    }
}

def validate_ip(ip):
    """
    Validasi IP yang diizinkan
    """
    # Tambahkan dukungan localhost dan IP yang valid
    if ip in ['127.0.0.1', 'localhost']:
        return True
    
    allowed_ips = CONFIG.get('allowed_ips', [])
    return ip in allowed_ips

def validate_api_key(key):
    """
    Validasi API key dari file konfigurasi
    """
    try:
        config_key = CONFIG.get('api_key')
        return key == config_key
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

# Inisialisasi Flask app
app = Flask(__name__)

@app.route('/api/user', methods=['POST'])
def manage_user():
    try:
        # Validasi IP
        client_ip = request.remote_addr
        if not validate_ip(client_ip):
            logger.warning(f"Percobaan akses dari IP tidak diizinkan: {client_ip}")
            return jsonify({
                'status': 'error', 
                'message': 'IP tidak diizinkan'
            }), 403
        
        # Logging headers dan raw data
        logger.debug(f"Request dari IP: {client_ip}")
        logger.debug(f"Request Headers: {dict(request.headers)}")
        logger.debug(f"Raw Request Data: {request.get_data(as_text=True)}")
        
        # Ambil API Key dari header
        api_key = request.headers.get('Authorization')
        logger.debug(f"API Key yang diterima: {api_key}")
        
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
        
        # Tentukan script berdasarkan action dan protokol
        if action not in ['add', 'delete']:
            logger.error(f"Invalid action: {action}")
            return jsonify({
                'status': 'error', 
                'message': 'Aksi hanya bisa "add" atau "delete"'
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
                    PROTOCOL_SCRIPTS[protocol]['add'], 
                    'api',  # Tambahkan flag mode API
                    username, 
                    password,
                    str(data.get('ip_limit', 2)),  # Default 2 IP
                    str(data.get('validity', 30)),  # Default 30 hari
                    str(data.get('quota', 0))  # Default 0 GB
                ]
                
                # Logging subprocess arguments
                logger.debug(f"Subprocess Arguments: {subprocess_args}")
                logger.debug(f"Executing: {' '.join(subprocess_args)}")
            else:
                # Argumen untuk protokol Xray
                subprocess_args = [
                    PROTOCOL_SCRIPTS[protocol]['add'], 
                    username, 
                    str(data.get('quota', 100)),  # Default 100 GB
                    str(data.get('ip_limit', 3)),  # Default 3 IP
                    str(data.get('validity', 30))  # Default 30 hari
                ]
        
        elif action == 'delete':
            # Argumen untuk delete
            subprocess_args = [
                PROTOCOL_SCRIPTS[protocol]['delete'], 
                username,
                "api_mode"  # Flag mode API
            ]
        # Jalankan subprocess
        result = subprocess.run(
            subprocess_args, 
            capture_output=True, 
            text=True, 
            timeout=30,
            env={
                **os.environ,  # Pertahankan environment existing
                'TERM': 'xterm',  # Tambahkan TERM environment
                'HOME': os.path.expanduser('~'),  # Pastikan HOME ter-set
                'PATH': os.environ.get('PATH', '/usr/local/bin:/usr/bin:/bin')
            }
        )
        
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
    app.run(host='0.0.0.0', port=8082, debug=False)
