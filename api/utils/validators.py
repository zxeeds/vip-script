import re
from typing import Union
from config.config_manager import ConfigManager

config = ConfigManager()

def validate_ip(ip: str) -> bool:
    """Validate if IP is allowed"""
    return ip in ['127.0.0.1', 'localhost'] or ip in config.allowed_ips

def validate_api_key(key: str) -> bool:
    """Validate API key"""
    return key == config.api_key

def validate_username(username: str, protocol: str = None) -> bool:
    """Validate username based on protocol"""
    if not username or len(username) < 3 or len(username) > 20:
        return False
    return bool(re.match(r'^[a-zA-Z0-9_]+$', username))

def validate_password(password: str) -> bool:
    """Validate password strength"""
    return password and len(password) >= 8

def validate_protocol(protocol: str) -> bool:
    """Check if protocol is supported"""
    return protocol.lower() in config.supported_protocols