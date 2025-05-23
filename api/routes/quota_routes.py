from flask import jsonify, request
from utils.logger import logger
from services.quota_service import QuotaService
from config.config_manager import ConfigManager

# Inisialisasi service dan config
quota_service = QuotaService()
config = ConfigManager()

def init_quota_routes(app):
    """
    Inisialisasi rute untuk pengecekan kuota
    """
    logger.info("Inisialisasi rute quota...")

    @app.route('/api/quota/user/<protocol>/<username>', methods=['GET'])
    def get_user_quota(protocol, username):
        """
        Mendapatkan informasi kuota pengguna
        """
        # Validasi API key
        api_key = request.headers.get('Authorization')
        client_ip = request.remote_addr
        
        if not api_key or api_key != config.get_api_key():
            logger.warning(f"Unauthorized access attempt from {client_ip}")
            return jsonify({"success": False, "message": "Unauthorized"}), 401
        
        allowed_ips = config.get_allowed_ips()
        if allowed_ips and client_ip not in allowed_ips and '0.0.0.0' not in allowed_ips:
            logger.warning(f"Access attempt from unauthorized IP: {client_ip}")
            return jsonify({"success": False, "message": "IP not allowed"}), 403
        
        logger.info(f"Request kuota untuk pengguna {username} protocol {protocol}")
        result = quota_service.get_user_quota(username, protocol)
        
        if "error" in result:
            return jsonify({"success": False, "message": result["error"]}), 400
        
        return jsonify({"success": True, "data": result})

    @app.route('/api/quota/all/<protocol>', methods=['GET'])
    def get_all_users_quota(protocol):
        """
        Mendapatkan informasi kuota untuk semua pengguna dari protocol tertentu
        """
        # Validasi API key
        api_key = request.headers.get('Authorization')
        client_ip = request.remote_addr
        
        if not api_key or api_key != config.get_api_key():
            logger.warning(f"Unauthorized access attempt from {client_ip}")
            return jsonify({"success": False, "message": "Unauthorized"}), 401
        
        allowed_ips = config.get_allowed_ips()
        if allowed_ips and client_ip not in allowed_ips and '0.0.0.0' not in allowed_ips:
            logger.warning(f"Access attempt from unauthorized IP: {client_ip}")
            return jsonify({"success": False, "message": "IP not allowed"}), 403
        
        logger.info(f"Request kuota untuk semua pengguna protocol {protocol}")
        result = quota_service.get_all_users_quota(protocol)
        
        if "error" in result:
            return jsonify({"success": False, "message": result["error"]}), 400
        
        return jsonify({"success": True, "data": result})

    @app.route('/api/quota/summary', methods=['GET'])
    def get_quota_summary():
        """
        Mendapatkan ringkasan kuota untuk semua protocol
        """
        # Validasi API key
        api_key = request.headers.get('Authorization')
        client_ip = request.remote_addr
        
        if not api_key or api_key != config.get_api_key():
            logger.warning(f"Unauthorized access attempt from {client_ip}")
            return jsonify({"success": False, "message": "Unauthorized"}), 401
        
        allowed_ips = config.get_allowed_ips()
        if allowed_ips and client_ip not in allowed_ips and '0.0.0.0' not in allowed_ips:
            logger.warning(f"Access attempt from unauthorized IP: {client_ip}")
            return jsonify({"success": False, "message": "IP not allowed"}), 403
        
        logger.info("Request ringkasan kuota untuk semua protocol")
        protocols = ["vmess", "vless", "trojan"]
        summary = {}
        
        for protocol in protocols:
            result = quota_service.get_all_users_quota(protocol)
            if "error" not in result:
                summary[protocol] = {
                    "total_users": len(result["users"]),
                    "active_users": sum(1 for user in result["users"] if user["status"] == "active"),
                    "expired_users": sum(1 for user in result["users"] if user["status"] == "expired")
                }
            else:
                summary[protocol] = {"error": result["error"]}
        
        return jsonify({"success": True, "data": summary})

    logger.info("Rute quota berhasil diinisialisasi")
