from flask import Blueprint, request, jsonify
from services.trial_factory import TrialServiceFactory
from utils.logger import logger

def init_trial_routes(app):
    trial_bp = Blueprint('trial', __name__, url_prefix='/api')
    
    @trial_bp.route('/create-trial', methods=['POST'])
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
            
            return jsonify({
                "status": "success",
                "message": "Akun trial berhasil dibuat",  # Pesan sukses ditambahkan
                "protocol": protocol,
                "details": account  # Key 'account' diubah menjadi 'details'
            }), 201
        
        except Exception as e:
            logger.error(f"Error creating trial account: {str(e)}", exc_info=True)
            return jsonify({
                "status": "error",
                "message": str(e)
            }), 500
    
    app.register_blueprint(trial_bp)