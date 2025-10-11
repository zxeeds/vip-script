from flask import Blueprint, request, jsonify
from services.trial_factory import TrialServiceFactory  # Import factory yang baru dibuat
from utils.logger import logger
from config.config_manager import ConfigManager
from functools import wraps
import json  # Perlu import modul json

# --- Decorator untuk validasi API key dan IP (tidak berubah) ---
def validate_api_key_and_ip(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        config = ConfigManager()
        api_key = request.headers.get('Authorization')
        if not api_key or api_key != config.api_key:
            logger.warning(f"Unauthorized access attempt with invalid API key from {request.remote_addr}")
            return jsonify({
                "success": False,
                "error": "Invalid API key"
            }), 401
        return f(*args, **kwargs)
    return decorated_function

def init_trial_routes(app):
    trial_bp = Blueprint('trial', __name__, url_prefix='/api')
    
    @trial_bp.route('/create-trial', methods=['POST'])
    @validate_api_key_and_ip
    def create_trial():
        try:
            data = request.get_json()
            protocol = data.get('protocol')
            
            # Validasi input dasar
            if not protocol:
                return jsonify({
                    "success": False,
                    "error": "Protocol is required"
                }), 400

            minutes = data.get('minutes', 10)
            quota = data.get('quota', 5)
            iplimit = data.get('iplimit', 2)
            
            logger.info(f"Request to create trial account for protocol: {protocol}")
            
            # 1. Pilih service yang sesuai menggunakan factory
            service = TrialServiceFactory.create_service(protocol)
            
            # 2. Jalankan service dan dapatkan output JSON mentah dari script
            script_output = service.create_trial_account(minutes, quota, iplimit)
            
            logger.info(f"Successfully received response from script for protocol: {protocol}")
            
            # 3. Parse output string dari script menjadi dictionary Python
            #    Ini diperlukan agar jsonify bisa membuat response JSON yang valid (dengan header yang benar).
            response_data = json.loads(script_output)
            
            # 4. Kembalikan response langsung dari script ke klien
            #    Status code 200 untuk sukses, 400/500 untuk error (akan ditangkap di except)
            return jsonify(response_data), 200
        
        except ValueError as e:
            # Tangkap error dari factory (misal: protokol tidak didukung)
            logger.error(f"Validation error: {str(e)}")
            return jsonify({
                "success": False,
                "error": str(e)
            }), 400
            
        except Exception as e:
            # Tangkap error dari eksekusi script (misal: script error)
            logger.error(f"Error creating trial account: {str(e)}", exc_info=True)
            # Pesan error sudah disaring oleh service layer
            return jsonify({
                "success": False,
                "error": str(e)
            }), 500
    
    app.register_blueprint(trial_bp)