from flask import Flask
from config.config_manager import ConfigManager
from utils.logger import setup_logging

def create_app():
    app = Flask(__name__)
    ConfigManager()  # Load config
    setup_logging()  # Setup logging

    # Import dan daftarkan routes
    from routes.user_routes import init_user_routes
    from routes.health_routes import init_health_routes
    
    init_user_routes(app)
    init_health_routes(app)
    
    return app

if __name__ == '__main__':
    app = create_app()
    port = ConfigManager().port
    app.run(host='0.0.0.0', port=port, debug=False)