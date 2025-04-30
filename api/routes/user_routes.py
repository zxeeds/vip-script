from flask import jsonify, request
from typing import Dict, Tuple
from services.user_service import UserService
from utils.validators import (
    validate_ip,
    validate_api_key,
    validate_username,
    validate_protocol
)
from utils.logger import logger

user_service = UserService()

def init_user_routes(app):
    @app.route('/api/user', methods=['POST'])
    def manage_user():
        """Handle user management requests"""
        client_ip = request.remote_addr
        if not validate_ip(client_ip):
            logger.warning(f"Unauthorized IP: {client_ip}")
            return jsonify({
                'status': 'error',
                'message': 'IP not allowed'
            }), 403

        api_key = request.headers.get('Authorization')
        if not validate_api_key(api_key):
            logger.error("Invalid API key")
            return jsonify({
                'status': 'error',
                'message': 'Invalid API Key'
            }), 403

        try:
            data = request.get_json(force=True)
            logger.debug(f"Request data: {data}")

            # Validate input
            if not validate_username(data.get('username')):
                return jsonify({
                    'status': 'error',
                    'message': 'Invalid username format'
                }), 400

            if not validate_protocol(data.get('protocol')):
                return jsonify({
                    'status': 'error',
                    'message': 'Unsupported protocol'
                }), 400

            result = user_service.manage_user(data)
            if result['success']:
                return jsonify({
                    'status': 'success',
                    'data': result['data']
                })
            else:
                return jsonify({
                    'status': 'error',
                    'message': result['error']
                }), result.get('code', 500)

        except Exception as e:
            logger.error(f"User route error: {str(e)}")
            return jsonify({
                'status': 'error',
                'message': 'Internal server error'
            }), 500
        
    
    @app.route('/api/user/renew', methods=['POST'])
    def renew_user():
        """Handle user renewal requests"""
        client_ip = request.remote_addr
        if not validate_ip(client_ip):
            return jsonify({
                'status': 'error',
                'message': 'IP not allowed'
            }), 403

        if not validate_api_key(request.headers.get('Authorization')):
            return jsonify({
                'status': 'error',
                'message': 'Invalid API Key'
            }), 403

        try:
            data = request.get_json(force=True)
            
            # Validasi wajib
            if not all(key in data for key in ['protocol', 'username']):
                return jsonify({
                    'status': 'error',
                    'message': 'Protocol and username are required'
                }), 400

            protocol = data['protocol'].lower()
            username = data['username']

            if not validate_protocol(protocol):
                return jsonify({
                    'status': 'error',
                    'message': 'Unsupported protocol'
                }), 400

            if protocol == 'ssh' and 'password' not in data:
                return jsonify({
                    'status': 'error',
                    'message': 'Password is required for SSH renewal'
                }), 400

            result = user_service.renew_user(protocol, username, data)
            
            if result['success']:
                return jsonify({
                    'status': 'success',
                    'data': result['data']
                })
            return jsonify({
                'status': 'error',
                'message': result['error']
            }), result.get('code', 500)

        except Exception as e:
            logger.error(f"Renew endpoint error: {str(e)}")
            return jsonify({
                'status': 'error',
                'message': 'Internal server error'
            }), 500