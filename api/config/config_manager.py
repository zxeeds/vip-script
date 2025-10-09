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
        """Memuat konfigurasi dari file JSON dan file domain Xray"""
        self._config = {}  # Inisialisasi dengan dict kosong
        main_config_loaded = False  # Flag untuk melacak status config utama

        # 1. Muat konfigurasi JSON utama
        try:
            with open(self._config_path, 'r') as f:
                self._config = json.load(f)
            main_config_loaded = True  # Tandai bahwa config utama berhasil
            logging.info("Konfigurasi JSON utama berhasil dimuat")
        except FileNotFoundError:
            logging.critical(f"File konfigurasi tidak ditemukan di {self._config_path}")
        except json.JSONDecodeError:
            logging.critical(f"File konfigurasi tidak valid (bukan JSON yang benar)")
        except Exception as e:
            logging.critical(f"Gagal memuat konfigurasi JSON: {str(e)}")

        # 2. Muat domain dari file terpisah (selalu coba, tidak peduli config utama gagal atau tidak)
        domain_file_path = '/etc/xray/domain'
        try:
            with open(domain_file_path, 'r') as f:
                domain = f.read().strip()
            if domain:
                self._config['DOMAIN'] = domain
                logging.info(f"Domain '{domain}' berhasil dimuat dari {domain_file_path}")
            else:
                logging.warning(f"File domain di {domain_file_path} kosong.")
        except FileNotFoundError:
            logging.warning(f"File domain tidak ditemukan di {domain_file_path}. Key 'DOMAIN' tidak akan diset.")
        except Exception as e:
            logging.error(f"Gagal membaca file domain: {str(e)}")

        # 3. Validasi konfigurasi HANYA jika config utama berhasil dimuat
        if main_config_loaded:
            self._validate_config()
            logging.info("Konfigurasi berhasil dimuat dan divalidasi")
        else:
            logging.warning("Konfigurasi utama gagal dimuat, validasi dilewati. Aplikasi mungkin tidak berfungsi dengan baik.")

    
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