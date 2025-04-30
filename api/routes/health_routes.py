from flask import jsonify
from datetime import datetime
from utils.validators import validate_ip, validate_api_key
from utils.logger import logger

def init_health_routes(app):
    @app.route('/api/ping', methods=['GET'])
    def ping():
        """Health check endpoint"""
        client_ip = request.remote_addr
        if not validate_ip(client_ip):
            return jsonify({
                "status": "error",
                "message": "IP not allowed"
            }), 403

        if not validate_api_key(request.headers.get('Authorization')):
            return jsonify({
                "status": "error",
                "message": "Invalid API Key"
            }), 401

        return jsonify({
            "status": "success",
            "message": "API is running",
            "timestamp": datetime.utcnow().isoformat(),
            "client_ip": client_ip
        })

    @app.route('/api/protocols', methods=['GET'])
    def list_protocols():
        """List supported protocols"""
        from config.config_manager import ConfigManager
        config = ConfigManager()
        return jsonify({
            'status': 'success',
            'protocols': config.supported_protocols
        })