import os
import json
import re
from utils.logger import logger

class QuotaService:
    def __init__(self):
        self.protocols = ["vmess", "vless", "trojan"]
        self.base_limit_dir = "/etc/limit"
        self.xray_config_path = "/etc/xray/config.json"
    
    def get_user_quota(self, username, protocol):
        """
        Mendapatkan informasi kuota pengguna
        """
        if protocol not in self.protocols:
            logger.error(f"Protocol tidak valid: {protocol}")
            return {"error": "Protocol tidak valid"}
        
        # Cek apakah pengguna ada di config Xray
        if not self._user_exists_in_xray(username, protocol):
            logger.error(f"Pengguna {username} tidak ditemukan untuk protocol {protocol}")
            return {"error": "Pengguna tidak ditemukan"}
        
        try:
            # Ambil batas kuota dari file konfigurasi pengguna (jika ada)
            quota_limit = 0
            is_unlimited = True
            protocol_dir = f"/etc/{protocol}"
            
            if os.path.exists(f"{protocol_dir}/{username}"):
                with open(f"{protocol_dir}/{username}", 'r') as f:
                    content = f.read().strip()
                    try:
                        quota_limit = int(content)
                        is_unlimited = False
                    except ValueError:
                        logger.warning(f"Format tidak valid dalam file kuota: {protocol_dir}/{username}")
            
            # Ambil penggunaan kuota saat ini
            quota_used = 0
            quota_file = f"{self.base_limit_dir}/{protocol}/{username}"
            if os.path.exists(quota_file):
                with open(quota_file, 'r') as f:
                    content = f.read().strip()
                    try:
                        quota_used = int(content)
                    except ValueError:
                        logger.warning(f"Format tidak valid dalam file penggunaan: {quota_file}")
            
            # Konversi ke format yang lebih mudah dibaca
            quota_limit_readable = "Unlimited" if is_unlimited else self._convert_bytes(quota_limit)
            quota_used_readable = self._convert_bytes(quota_used)
            
            # Hitung persentase penggunaan (hanya jika ada batas)
            percentage = 0
            if not is_unlimited and quota_limit > 0:
                percentage = min(round((quota_used / quota_limit) * 100, 2), 100)
            
            # Ambil tanggal kedaluwarsa dari config.json jika ada
            expiry_date = self._get_user_expiry(username, protocol)
            
            return {
                "username": username,
                "protocol": protocol,
                "quota_limit": quota_limit if not is_unlimited else -1,
                "quota_limit_readable": quota_limit_readable,
                "quota_used": quota_used,
                "quota_used_readable": quota_used_readable,
                "percentage": percentage,
                "is_unlimited": is_unlimited,
                "status": "expired" if (not is_unlimited and percentage >= 100) else "active",
                "expiry_date": expiry_date
            }
        except Exception as e:
            logger.error(f"Error mendapatkan kuota pengguna: {str(e)}")
            return {"error": f"Error mendapatkan kuota pengguna: {str(e)}"}
    
    def get_all_users_quota(self, protocol):
        """
        Mendapatkan informasi kuota untuk semua pengguna dari protocol tertentu
        """
        if protocol not in self.protocols:
            logger.error(f"Protocol tidak valid: {protocol}")
            return {"error": "Protocol tidak valid"}
        
        try:
            # Ambil semua pengguna dari config Xray
            users = []
            usernames = self._get_users_from_xray(protocol)
            
            if not usernames:
                return {"users": [], "protocol": protocol}
            
            for username in usernames:
                user_quota = self.get_user_quota(username, protocol)
                if "error" not in user_quota:
                    users.append(user_quota)
            
            return {"users": users, "protocol": protocol}
        except Exception as e:
            logger.error(f"Error mendapatkan kuota semua pengguna: {str(e)}")
            return {"error": f"Error mendapatkan kuota semua pengguna: {str(e)}"}
    
    def _get_users_from_xray(self, protocol):
        """
        Mendapatkan daftar pengguna dari config Xray berdasarkan protocol
        """
        try:
            if not os.path.exists(self.xray_config_path):
                logger.error(f"File config Xray tidak ditemukan: {self.xray_config_path}")
                return []
            
            with open(self.xray_config_path, 'r') as f:
                config_content = f.read()
                config = json.loads(config_content)
            
            usernames = []
            
            # Cari inbound dengan protocol yang sesuai
            for inbound in config.get("inbounds", []):
                inbound_protocol = inbound.get("protocol")
                
                # Periksa apakah ini adalah inbound yang kita cari
                if inbound_protocol == protocol:
                    settings = inbound.get("settings", {})
                    clients = settings.get("clients", [])
                    
                    for client in clients:
                        email = client.get("email")
                        if email:
                            usernames.append(email)
            
            return usernames
            
        except Exception as e:
            logger.error(f"Error mendapatkan pengguna dari config Xray: {str(e)}")
            return []
    
    def _get_user_expiry(self, username, protocol):
        """
        Mendapatkan tanggal kedaluwarsa pengguna dari komentar di config.json
        """
        try:
            if not os.path.exists(self.xray_config_path):
                return None
            
            with open(self.xray_config_path, 'r') as f:
                content = f.read()
            
            # Pola komentar berbeda untuk setiap protokol
            if protocol == "trojan":
                pattern = r'#!\s+' + re.escape(username) + r'\s+(\S+)'
            elif protocol == "vless":
                pattern = r'#&\s+' + re.escape(username) + r'\s+(\S+)'
            elif protocol == "vmess":
                pattern = r'###\s+' + re.escape(username) + r'\s+(\S+)'
            else:
                return None
            
            match = re.search(pattern, content)
            if match:
                return match.group(1)
            
            return None
            
        except Exception as e:
            logger.error(f"Error mendapatkan tanggal kedaluwarsa: {str(e)}")
            return None
    
    def _user_exists_in_xray(self, username, protocol):
        """
        Memeriksa apakah pengguna ada di config Xray
        """
        users = self._get_users_from_xray(protocol)
        return username in users
    
    def _convert_bytes(self, bytes_value):
        """
        Mengkonversi bytes ke format yang lebih mudah dibaca
        """
        if bytes_value < 1024:
            return f"{bytes_value}B"
        elif bytes_value < 1048576:
            return f"{bytes_value // 1024}KB"
        elif bytes_value < 1073741824:
            return f"{bytes_value // 1048576}MB"
        else:
            return f"{bytes_value // 1073741824}GB"
