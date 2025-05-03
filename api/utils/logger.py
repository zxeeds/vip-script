import logging
import os
from logging.handlers import RotatingFileHandler

# Buat logger instance GLOBAL
logger = logging.getLogger('vpn_api')

def setup_logging():
    """Initialize logging configuration"""
    # Konfigurasi dasar
    logger.setLevel(logging.DEBUG)
    
    # Buat formatter
    formatter = logging.Formatter(
        '%(asctime)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s'
    )
    
    # File handler
    log_dir = '/var/log/vpn-api'
    os.makedirs(log_dir, exist_ok=True)
    
    file_handler = RotatingFileHandler(
        os.path.join(log_dir, 'vpn-api.log'),
        maxBytes=10*1024*1024,
        backupCount=5
    )
    file_handler.setFormatter(formatter)
    
    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)
    
    # Tambahkan handler
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

# Panggil saat modul diimport
setup_logging()

# Ekspor logger
__all__ = ['logger', 'setup_logging']