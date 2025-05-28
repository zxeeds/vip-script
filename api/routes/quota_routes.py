from flask import jsonify, request
from services.quota_service import QuotaService
from utils.logger import logger
from config.config_manager import ConfigManager
from functools import wraps

def validate_api_key_and_ip(f):
    """Decorator untuk validasi API key dan IP address"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        config = ConfigManager()
        
        # Validasi API Key
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

def init_quota_routes(app):
    """Inisialisasi routes untuk quota"""
    
    quota_service = QuotaService()
    
    @app.route('/api/quota/all', methods=['GET'])
    @validate_api_key_and_ip
    def get_all_users_quota():
        """
        Mendapatkan informasi kuota untuk semua user
        """
        try:
            logger.info("Request kuota untuk semua user")
            result = quota_service.get_all_users_quota()
            
            if "error" in result:
                return jsonify({
                    "success": False,
                    "error": result["error"]
                }), 500
            
            return jsonify({
                "success": True,
                "data": result
            })
            
        except Exception as e:
            logger.error(f"Error mendapatkan kuota semua user: {str(e)}")
            return jsonify({
                "success": False,
                "error": str(e)
            }), 500

    @app.route('/api/quota/<username>', methods=['GET'])
    @validate_api_key_and_ip
    def get_user_quota(username):
        """
        Mendapatkan informasi kuota untuk user tertentu
        """
        try:
            logger.info(f"Request kuota untuk user {username}")
            
            # Validasi username
            if not username or len(username.strip()) == 0:
                return jsonify({
                    "success": False,
                    "error": "Username tidak boleh kosong"
                }), 400
            
            result = quota_service.get_user_quota(username.strip())
            
            if "error" in result:
                return jsonify({
                    "success": False,
                    "error": result["error"]
                }), 404
            
            return jsonify({
                "success": True,
                "data": result
            })
            
        except Exception as e:
            logger.error(f"Error mendapatkan kuota user {username}: {str(e)}")
            return jsonify({
                "success": False,
                "error": str(e)
            }), 500

    logger.info("Quota routes berhasil diinisialisasi")
