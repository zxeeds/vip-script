from flask import Blueprint, request, jsonify
from services.trial_factory import TrialServiceFactory
from utils.logger import logger
from config.config_manager import ConfigManager
from functools import wraps  # <-- Tambahkan import ini

# --- SALIN DAN TEMPATKAN DECORATOR INI DI SINI ---
def validate_api_key_and_ip(f):
    """Decorator untuk validasi API key dan IP address"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        config = ConfigManager()
        
        # Validasi API Key
        # Diasumsikan API Key dikirim di header dengan format "Bearer YOUR_API_KEY"
        # atau langsung "YOUR_API_KEY". Sesuaikan jika perlu.
        api_key = request.headers.get('Authorization')
        if not api_key or api_key != config.api_key:
            logger.warning(f"Unauthorized access attempt with invalid API key from {request.remote_addr}")
            return jsonify({
                "success": False,
                "error": "Invalid API key"
            }), 401
        
        # Validasi IP Address - Temporarily disabled
        client_ip = request.remote_addr
        allowed_ips = config.allowed_ips
        
        # # Jika allowed_ips tidak kosong, validasi IP
        # if allowed_ips and client_ip not in allowed_ips:
        #     logger.warning(f"Unauthorized access attempt from IP {client_ip}")
        #     return jsonify({
        #         "success": False,
        #         "error": "IP address not allowed"
        #     }), 403
        
        return f(*args, **kwargs)
    return decorated_function
# --- AKHIR DECORATOR ---

def init_trial_routes(app):
    trial_bp = Blueprint('trial', __name__, url_prefix='/api')
    
    @trial_bp.route('/create-trial', methods=['POST'])
    @validate_api_key_and_ip  # <-- TAMBAHKAN DECORATOR DI SINI
    def create_trial():
        try:
            data = request.get_json()
            protocol = data.get('protocol')
            minutes = data.get('minutes', 10)
            quota = data.get('quota', 5)
            iplimit = data.get('iplimit', 2)
            
            logger.info(f"Creating trial account for protocol: {protocol}")
            
            # Pilih service berdasarkan protokol
            service = TrialServiceFactory.create_service(protocol)
            
            # Buat akun trial
            account = service.create_trial_account(minutes, quota, iplimit)
            
            logger.info(f"Successfully created trial account: {account['username']}")
            
            # --- PERUBAHAN FORMAT RESPONS UNTUK KONSISTENSI ---
            return jsonify({
                "success": True,             # Diubah dari "status"
                "message": "Akun trial berhasil dibuat",
                "protocol": protocol,
                "data": account              # Diubah dari "details"
            }), 201
        
        except Exception as e:
            logger.error(f"Error creating trial account: {str(e)}", exc_info=True)
            # --- PERUBAHAN FORMAT RESPONS UNTUK KONSISTENSI ---
            return jsonify({
                "success": False,            # Diubah dari "status"
                "error": str(e)              # Diubah dari "message"
            }), 500
    
    app.register_blueprint(trial_bp)