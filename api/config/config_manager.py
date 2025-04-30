import json
import logging
from typing import Dict, Any, Optional

class ConfigManager:
    """
    Kelas untuk mengelola konfigurasi aplikasi dari file JSON.
    Menggunakan Singleton pattern untuk memastikan hanya satu instance yang ada.
    """
    
    _instance = None
    _config_path = '/etc/vpn-api/config.json'  # Default config path
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._load_config()
        return cls._instance
    
    def _load_config(self) -> None:
        """Memuat konfigurasi dari file JSON"""
        try:
            with open(self._config_path, 'r') as f:
                self._config = json.load(f)
            self._validate_config()
            logging.info("Konfigurasi berhasil dimuat")
        except FileNotFoundError:
            logging.critical(f"File konfigurasi tidak ditemukan di {self._config_path}")
            self._config = {}
        except json.JSONDecodeError:
            logging.critical(f"File konfigurasi tidak valid (bukan JSON yang benar)")
            self._config = {}
        except Exception as e:
            logging.critical(f"Gagal memuat konfigurasi: {str(e)}")
            self._config = {}
    
    def _validate_config(self) -> None:
        """Validasi struktur konfigurasi dasar"""
        required_keys = {
            'api_key': str,
            'allowed_ips': list,
            'protocols_allowed': list,
            'port': int
        }
        
        for key, key_type in required_keys.items():
            if key not in self._config:
                raise ValueError(f"Key wajib '{key}' tidak ditemukan dalam konfigurasi")
            if not isinstance(self._config[key], key_type):
                raise ValueError(f"Key '{key}' harus bertipe {key_type.__name__}")
    
    def get(self, key: str, default: Optional[Any] = None) -> Any:
        """
        Mendapatkan nilai konfigurasi berdasarkan key
        
        Args:
            key: Key konfigurasi yang ingin diambil
            default: Nilai default jika key tidak ditemukan
            
        Returns:
            Nilai konfigurasi atau default
        """
        return self._config.get(key, default)
    
    @property
    def api_key(self) -> str:
        """Mendapatkan API key"""
        return self._config['api_key']
    
    @property
    def allowed_ips(self) -> list:
        """Daftar IP yang diizinkan"""
        return self._config['allowed_ips']
    
    @property
    def supported_protocols(self) -> list:
        """Daftar protokol yang didukung"""
        return self._config['protocols_allowed']
    
    @property
    def port(self) -> int:
        """Port untuk Flask server"""
        return self._config.get('port', 8082)

    @classmethod
    def set_config_path(cls, path: str) -> None:
        """Set custom path untuk file konfigurasi (utama untuk testing)"""
        cls._config_path = path
        if cls._instance is not None:
            cls._instance._load_config()