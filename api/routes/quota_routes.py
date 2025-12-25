from flask import request, jsonify
# Import class QuotaService dari folder services
from services.quota_service import QuotaService
from utils.logger import logger

def init_quota_routes(flask_app):
    """
    Mendaftarkan semua endpoint API terkait kuota ke aplikasi Flask.
    """
    # Instansiasi service
    service = QuotaService()

    # Endpoint: Cek kuota user spesifik menggunakan URL Path
    # Contoh URL: /api/quota/vmess/username123
    @flask_app.route('/api/quota/<protocol>/<username>', methods=['GET'])
    def get_user_quota(protocol, username):
        try:
            # Parameter protocol dan username otomatis diambil dari URL oleh Flask
            # Tidak perlu lagi request.args.get(...)
            
            # Validasi input dasar (walaupun URL path seharusnya selalu ada isinya)
            if not username or not protocol:
                return jsonify({
                    "error": "Username dan Protocol tidak boleh kosong"
                }), 400
            
            # Panggil logika dari service
            result = service.get_user_quota(protocol, username)

            # Cek jika service mengembalikan error
            if "error" in result:
                status_code = 404 if "tidak ditemukan" in result["error"] else 400
                return jsonify(result), status_code

            return jsonify(result), 200

        except Exception as e:
            logger.error(f"Error pada endpoint /api/quota/{protocol}/{username}: {e}")
            return jsonify({"error": "Internal Server Error"}), 500

    # Endpoint: Mendapatkan kuota semua user (Tetap sama)
    @flask_app.route('/api/quota/all', methods=['GET'])
    def get_all_users_quota():
        try:
            result = service.get_all_users_quota()
            return jsonify(result), 200
        except Exception as e:
            logger.error(f"Error pada endpoint /api/quota/all: {e}")
            return jsonify({"error": "Internal Server Error"}), 500