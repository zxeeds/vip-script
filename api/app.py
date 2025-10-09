# /etc/vpn-api/api/app.py

"""
Modul utama untuk menjalankan aplikasi VPN API.
Aplikasi ini dirancang untuk dijalankan sebagai sebuah package Python.
"""

from flask import Flask

# Buat app instance DI LEVEL MODUL
app = Flask(__name__)

# Import logger SETELAH app dibuat untuk menghindari circular import
from utils.logger import logger

def configure_app():
    """Konfigurasi aplikasi Flask."""
    try:
        logger.info("Memulai konfigurasi aplikasi...")
        
        # 1. Load konfigurasi dari ConfigManager
        # ConfigManager seharusnya mengembalikan objek kelas konfigurasi
        from config.config_manager import ConfigManager
        app.config.from_object(ConfigManager())
        logger.info(f"Konfigurasi berhasil dimuat untuk environment: {app.config.get('ENV', 'default')}")

        # 2. Lazy load semua route dalam app context
        # Ini memastikan semua route memiliki akses ke konteks aplikasi
        with app.app_context():
            from routes.health_routes import init_health_routes
            from routes.user_routes import init_user_routes
            from routes.quota_routes import init_quota_routes
            from routes.trial_routes import init_trial_routes
            
            init_health_routes(app)
            init_user_routes(app)
            init_quota_routes(app)
            init_trial_routes(app)
        
        logger.info("Semua route berhasil diinisialisasi.")
        logger.info("Aplikasi berhasil dikonfigurasi.")
        
    except Exception as e:
        logger.critical(f"Gagal konfigurasi aplikasi: {str(e)}", exc_info=True)
        raise

# Panggil fungsi konfigurasi saat modul diimpor
configure_app()

# Fungsi ini hanya untuk development server
# TIDAK digunakan saat dijalankan dengan Gunicorn
def run_dev_server():
    """Menjalankan server development Flask."""
    debug_mode = app.config.get('DEBUG', False)
    logger.warning(f"Menjalankan server development di mode {'debug' if debug_mode else 'produksi simulasi'}. JANGAN GUNAKAN UNTUK PRODUKSI.")
    app.run(host='0.0.0.0', port=8082, debug=debug_mode)

# Blok ini dieksekusi hanya jika file dijalankan langsung (python app.py)
if __name__ == '__main__':
    run_dev_server()
