import os
import json
import re
from utils.logger import logger

class QuotaService:
    # Constants
    BYTES_TO_GB = 1073741824
    SUPPORTED_PROTOCOLS = ["vmess", "vless", "trojan"]
    
    def __init__(self):
        self.base_limit_dir = "/etc/limit"
        self.xray_config_path = "/etc/xray/config.json"
        
        # Pattern yang benar berdasarkan analisis
        # Format: comment di line terpisah
        self.comment_patterns = {
            "vless": r'#vless\s*\n\s*#&\s+([^\s]+)\s+(\d{4}-\d{2}-\d{2})',
            "vmess": r'#vmess\s*\n\s*###\s+([^\s]+)\s+(\d{4}-\d{2}-\d{2})',
            "trojan": r'#trojanws\s*\n\s*#!\s+([^\s]+)\s+(\d{4}-\d{2}-\d{2})'
        }
        
        # Pattern untuk grpc variant
        self.grpc_patterns = {
            "vless": r'#vlessgrpc\s*\n\s*#&\s+([^\s]+)\s+(\d{4}-\d{2}-\d{2})',
            "vmess": r'#vmessgrpc\s*\n\s*###\s+([^\s]+)\s+(\d{4}-\d{2}-\d{2})',
            "trojan": r'#trojangrpc\s*\n\s*#!\s+([^\s]+)\s+(\d{4}-\d{2}-\d{2})'
        }
        
        # Pattern untuk mencari expiry date
        self.expiry_patterns = {
            "vless": r'#&\s+{}\s+(\d{{4}}-\d{{2}}-\d{{2}})',
            "vmess": r'###\s+{}\s+(\d{{4}}-\d{{2}}-\d{{2}})',
            "trojan": r'#!\s+{}\s+(\d{{4}}-\d{{2}}-\d{{2}})'
        }

    def get_user_quota(self, username):
        """
        Mendapatkan informasi kuota untuk user tertentu dari semua protocol
        """
        try:
            # Validasi input
            if not username or not isinstance(username, str):
                return {"error": "Username tidak valid"}
            
            logger.info(f"Mencari user: {username}")
            
            # Cari user di semua protocol
            user_data = self._find_user_in_config(username)
            if not user_data:
                logger.warning(f"User {username} tidak ditemukan")
                return {"error": "User tidak ditemukan"}
                
            protocol = user_data['protocol']
            logger.info(f"User {username} ditemukan dengan protocol {protocol}")
                
            # Ambil batas kuota dari file konfigurasi pengguna
            quota_limit = 0
            is_unlimited = True
            protocol_dir = f"/etc/{protocol}"
                
            if os.path.exists(f"{protocol_dir}/{username}"):
                try:
                    with open(f"{protocol_dir}/{username}", 'r') as f:
                        content = f.read().strip()
                        if content:
                            quota_limit = int(content)
                            is_unlimited = False
                except (ValueError, FileNotFoundError) as e:
                    logger.warning(f"Error membaca file quota {protocol_dir}/{username}: {e}")
                
            # Ambil penggunaan kuota saat ini
            quota_used = 0
            quota_file = f"{self.base_limit_dir}/{protocol}/{username}"
            if os.path.exists(quota_file):
                try:
                    with open(quota_file, 'r') as f:
                        content = f.read().strip()
                        if content:
                            quota_used = int(content)
                except (ValueError, FileNotFoundError) as e:
                    logger.warning(f"Error membaca file penggunaan {quota_file}: {e}")
                
            # Konversi ke GB
            quota_limit_gb = "Unlimited" if is_unlimited else round(quota_limit / self.BYTES_TO_GB, 2)
            quota_used_gb = round(quota_used / self.BYTES_TO_GB, 2)
                
            # Ambil tanggal kedaluwarsa
            expiry_date = self._get_user_expiry(username, protocol)
                
            # Tentukan status
            status = "active"
            if not is_unlimited and quota_used >= quota_limit:
                status = "quota_exceeded"
            elif expiry_date and self._is_expired(expiry_date):
                status = "expired"
                
            result = {
                "username": username,
                "protocol": protocol,
                "quota_limit_gb": quota_limit_gb,
                "quota_used_gb": quota_used_gb,
                "quota_remaining_gb": "Unlimited" if is_unlimited else max(0, round((quota_limit - quota_used) / self.BYTES_TO_GB, 2)),
                "is_unlimited": is_unlimited,
                "status": status,
                "expiry_date": expiry_date
            }
                
            # Tambahkan uuid atau password
            if protocol == "trojan":
                result["password"] = user_data.get("password")
            else:
                result["uuid"] = user_data.get("id")
                
            return result
                
        except Exception as e:
            logger.error(f"Error mendapatkan kuota user {username}: {str(e)}")
            return {"error": f"Error mendapatkan kuota user: {str(e)}"}

    def get_all_users_quota(self):
        """
        Mendapatkan informasi kuota untuk semua user dari config.json
        """
        try:
            logger.info("Memulai get_all_users_quota")
            
            all_users = []
            users_data = self._get_all_users_from_config()
            
            logger.info(f"Data user ditemukan: {len(users_data)}")
            
            if len(users_data) == 0:
                logger.warning("Tidak ada user ditemukan dalam config")
                return {
                    "users": [],
                    "statistics": {
                        "total_users": 0,
                        "active_users": 0,
                        "expired_users": 0,
                        "quota_exceeded_users": 0
                    }
                }
                
            for user_data in users_data:
                username = user_data['email']
                protocol = user_data['protocol']
                
                # Ambil batas kuota
                quota_limit = 0
                is_unlimited = True
                protocol_dir = f"/etc/{protocol}"
                
                if os.path.exists(f"{protocol_dir}/{username}"):
                    try:
                        with open(f"{protocol_dir}/{username}", 'r') as f:
                            content = f.read().strip()
                            if content:
                                quota_limit = int(content)
                                is_unlimited = False
                    except (ValueError, FileNotFoundError):
                        pass
                
                # Ambil penggunaan kuota
                quota_used = 0
                quota_file = f"{self.base_limit_dir}/{protocol}/{username}"
                if os.path.exists(quota_file):
                    try:
                        with open(quota_file, 'r') as f:
                            content = f.read().strip()
                            if content:
                                quota_used = int(content)
                    except (ValueError, FileNotFoundError):
                        pass
                
                # Konversi ke GB
                quota_limit_gb = "Unlimited" if is_unlimited else round(quota_limit / self.BYTES_TO_GB, 2)
                quota_used_gb = round(quota_used / self.BYTES_TO_GB, 2)
                
                # Ambil tanggal kedaluwarsa
                expiry_date = self._get_user_expiry(username, protocol)
                
                # Tentukan status
                status = "active"
                if not is_unlimited and quota_used >= quota_limit:
                    status = "quota_exceeded"
                elif expiry_date and self._is_expired(expiry_date):
                    status = "expired"
                
                user_info = {
                    "username": username,
                    "protocol": protocol,
                    "quota_limit_gb": quota_limit_gb,
                    "quota_used_gb": quota_used_gb,
                    "quota_remaining_gb": "Unlimited" if is_unlimited else max(0, round((quota_limit - quota_used) / self.BYTES_TO_GB, 2)),
                    "is_unlimited": is_unlimited,
                    "status": status,
                    "expiry_date": expiry_date
                }
                
                # Tambahkan uuid atau password
                if protocol == "trojan":
                    user_info["password"] = user_data.get("password")
                else:
                    user_info["uuid"] = user_data.get("id")
                
                all_users.append(user_info)
                
            # Statistik tambahan
            total_users = len(all_users)
            active_users = len([u for u in all_users if u['status'] == 'active'])
            expired_users = len([u for u in all_users if u['status'] == 'expired'])
            quota_exceeded_users = len([u for u in all_users if u['status'] == 'quota_exceeded'])
            
            return {
                "users": all_users,
                "statistics": {
                    "total_users": total_users,
                    "active_users": active_users,
                    "expired_users": expired_users,
                    "quota_exceeded_users": quota_exceeded_users
                }
            }
                
        except Exception as e:
            logger.error(f"Error mendapatkan semua kuota user: {str(e)}")
            return {"error": f"Error mendapatkan semua kuota user: {str(e)}"}

    def _get_all_users_from_config(self):
        """
        Mendapatkan semua user dari config.json berdasarkan comment pattern
        """
        try:
            if not os.path.exists(self.xray_config_path):
                logger.error(f"File config tidak ditemukan: {self.xray_config_path}")
                return []
                
            with open(self.xray_config_path, 'r') as f:
                content = f.read()
                
            users = []
            
            # Cari user berdasarkan comment pattern (regular)
            for protocol, pattern in self.comment_patterns.items():
                matches = re.findall(pattern, content)
                logger.info(f"Protocol {protocol}: ditemukan {len(matches)} user")
                
                for username, expiry in matches:
                    user_data = self._find_user_in_json_by_email(username, protocol)
                    if user_data:
                        user_data['protocol'] = protocol
                        user_data['email'] = username
                        user_data['expiry_from_comment'] = expiry
                        users.append(user_data)
                        logger.info(f"User ditemukan: {username} ({protocol})")
            
            # Cari user berdasarkan grpc pattern
            for protocol, pattern in self.grpc_patterns.items():
                matches = re.findall(pattern, content)
                logger.info(f"Protocol {protocol}grpc: ditemukan {len(matches)} user")
                
                for username, expiry in matches:
                    # Cek apakah user sudah ada (avoid duplicate)
                    existing = any(u['email'] == username and u['protocol'] == protocol for u in users)
                    if not existing:
                        user_data = self._find_user_in_json_by_email(username, protocol)
                        if user_data:
                            user_data['protocol'] = protocol
                            user_data['email'] = username
                            user_data['expiry_from_comment'] = expiry
                            user_data['variant'] = 'grpc'
                            users.append(user_data)
                            logger.info(f"User ditemukan (grpc): {username} ({protocol})")
                
            return users
                
        except Exception as e:
            logger.error(f"Error membaca config: {str(e)}")
            return []

    def _find_user_in_config(self, username):
        """
        Mencari user tertentu di config.json
        """
        all_users = self._get_all_users_from_config()
        for user in all_users:
            if user['email'] == username:
                return user
        return None

    def _find_user_in_json_by_email(self, email, protocol):
        """
        Mencari user di struktur JSON berdasarkan email dan protocol
        """
        try:
            with open(self.xray_config_path, 'r') as f:
                # Remove comment lines untuk parsing JSON
                lines = f.readlines()
                json_lines = []
                for line in lines:
                    stripped = line.strip()
                    if not stripped.startswith('#'):
                        json_lines.append(line)
                
                json_content = ''.join(json_lines)
                config = json.loads(json_content)
                
            for inbound in config.get("inbounds", []):
                inbound_protocol = inbound.get("protocol")
                
                # Match protocol
                if (inbound_protocol == protocol or
                     (protocol == "trojan" and inbound_protocol in ["trojan", "trojanws"]) or
                    (protocol == "vless" and inbound_protocol == "vless") or
                    (protocol == "vmess" and inbound_protocol == "vmess")):
                    
                    settings = inbound.get("settings", {})
                    clients = settings.get("clients", [])
                    
                    for client in clients:
                        if client.get("email") == email:
                            return client
                            
            return None
            
        except Exception as e:
            logger.error(f"Error finding user {email} in JSON: {str(e)}")
            return None

    def _get_user_expiry(self, username, protocol):
        """
        Mendapatkan tanggal kedaluwarsa dari comment
        """
        try:
            if not os.path.exists(self.xray_config_path):
                return None
                
            with open(self.xray_config_path, 'r') as f:
                content = f.read()
                
            # Gunakan pattern yang sesuai dengan format
            pattern = self.expiry_patterns.get(protocol, "").format(re.escape(username))
            if pattern:
                match = re.search(pattern, content)
                if match:
                    return match.group(1)
                    
            return None
                
        except Exception as e:
            logger.error(f"Error mendapatkan tanggal kedaluwarsa untuk {username}: {str(e)}")
            return None

    def _is_expired(self, expiry_date):
        """
        Mengecek apakah tanggal sudah expired
        """
        try:
            from datetime import datetime
            expiry = datetime.strptime(expiry_date, "%Y-%m-%d")
            now = datetime.now()
            return now > expiry
        except Exception as e:
            logger.error(f"Error checking expiry date {expiry_date}: {str(e)}")
            return False

