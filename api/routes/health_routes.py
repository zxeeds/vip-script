from flask import jsonify, request
from datetime import datetime
from utils.validators import validate_ip, validate_api_key
from utils.logger import logger

def init_health_routes(app):
    @app.route('/api/ping', methods=['GET'])
    def ping():
        """Health check endpoint"""
        try:
            client_ip = request.remote_addr
            logger.info(f"Ping request from {client_ip}")
            
            # Validasi IP - Temporarily disabled
            # if not validate_ip(client_ip):
            #     logger.warning(f"Unauthorized IP: {client_ip}")
            #     return jsonify({"status": "error", "message": "IP not allowed"}), 403

            # Validasi API Key
            if not validate_api_key(request.headers.get('Authorization')):
                logger.warning("Invalid API Key")
                return jsonify({"status": "error", "message": "Invalid API Key"}), 401

            # Response sukses
            response = {
                "status": "success",
                "message": "API is running",
                "timestamp": datetime.utcnow().isoformat(),
                "client_ip": client_ip
            }
            logger.debug(f"Ping response: {response}")
            return jsonify(response)

        except Exception as e:
            logger.error(f"Ping error: {str(e)}", exc_info=True)
            return jsonify({"status": "error", "message": "Internal server error"}), 500

    @app.route('/api/protocols', methods=['GET'])
    def list_protocols():
        """List supported protocols"""
        try:
            from config.config_manager import ConfigManager
            config = ConfigManager()
            protocols = config.supported_protocols
            logger.info(f"Protocols requested: {protocols}")
            return jsonify({
                'status': 'success',
                'protocols': protocols
            })
        except Exception as e:
            logger.error(f"Protocols error: {str(e)}", exc_info=True)
            return jsonify({
                'status': 'error',
                'message': 'Failed to get protocols'
            }), 500