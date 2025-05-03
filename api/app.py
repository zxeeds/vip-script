import sys
from flask import Flask

# Fix Python path
sys.path.insert(0, '/etc/vpn-api/api')

# Buat app instance DI LEVEL MODUL
app = Flask(__name__)

# Import logger SETELAH app dibuat
from utils.logger import logger

def configure_app():
    """Konfigurasi aplikasi"""
    try:
        logger.info("Memulai konfigurasi aplikasi...")
        
        # Lazy import untuk hindari circular import
        from config.config_manager import ConfigManager
        ConfigManager()
        
        # Lazy load routes
        with app.app_context():
            from routes.health_routes import init_health_routes
            from routes.user_routes import init_user_routes
            
            init_health_routes(app)
            init_user_routes(app)
            
        logger.info("Aplikasi berhasil dikonfigurasi")
    
    except Exception as e:
        logger.critical(f"Gagal konfigurasi: {str(e)}", exc_info=True)
        raise

# Panggil konfigurasi
configure_app()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8082)