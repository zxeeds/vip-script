import os
import re
import sqlite3
from typing import Optional, Tuple, Union
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
    return bool(re.match(r'^[a-zA-Z0-9]+$', username))

def validate_password(password: str) -> bool:
    """Validate password strength"""
    return password and len(password) >= 8

def validate_protocol(protocol: str) -> bool:
    """Check if protocol is supported"""
    return protocol.lower() in config.supported_protocols

def check_username_unique(
    username: str,
    db_path: str = '/etc/vpn/database.db'
) -> Tuple[bool, Optional[str], int]:
    """Check whether a username is unique in the accounts table."""
    if not username:
        return False, 'Username is required', 400

    if not os.path.exists(db_path):
        return False, f'Database file not found at {db_path}', 500

    try:
        conn = sqlite3.connect(db_path)
        try:
            cursor = conn.cursor()
            cursor.execute(
                'SELECT 1 FROM accounts WHERE username = ? LIMIT 1',
                (username,)
            )
            exists = cursor.fetchone() is not None
        finally:
            conn.close()
    except sqlite3.Error as e:
        return False, f'Database error: {str(e)}', 500

    if exists:
        return False, 'Username already exists', 400

    return True, None, 200
