import logging
import os
from logging.handlers import RotatingFileHandler
from config.config_manager import ConfigManager

def setup_logging():
    """Setup logging configuration"""
    config = ConfigManager()
    
    log_dir = config.get('log_dir', '/var/log/vpn-api')
    os.makedirs(log_dir, exist_ok=True)
    
    logger = logging.getLogger('vpn_api')
    logger.setLevel(logging.DEBUG)
    
    # File handler with rotation
    file_handler = RotatingFileHandler(
        os.path.join(log_dir, 'vpn-api.log'),
        maxBytes=10 * 1024 * 1024,  # 10 MB
        backupCount=5
    )
    file_handler.setFormatter(logging.Formatter(
        '%(asctime)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s'
    ))
    
    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(logging.Formatter(
        '%(levelname)s - %(message)s'
    ))
    
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    
    return logger