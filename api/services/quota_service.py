import os
import sqlite3
from datetime import datetime
from utils.logger import logger

class QuotaService:
    # Constants
    BYTES_TO_GB = 1073741824  # 1024 * 1024 * 1024
    SUPPORTED_PROTOCOLS = ["vmess", "vless", "trojan"]
    DB_PATH = "/etc/vpn/database.db"
    
    def __init__(self):
        # Inisialisasi koneksi database
        try:
            self.conn = sqlite3.connect(self.DB_PATH)
            # Memungkinkan akses kolom seperti dictionary (e.g., row['username'])
            self.conn.row_factory = sqlite3.Row 
            logger.info(f"Berhasil terhubung ke database: {self.DB_PATH}")
        except sqlite3.Error as e:
            logger.error(f"Error saat menghubungkan ke database: {e}")
            # Hentikan layanan jika koneksi database gagal
            raise

    def _convert_timestamp_to_date(self, timestamp):
        """Helper untuk mengkonversi Unix Epoch ke format YYYY-MM-DD."""
        if timestamp:
            try:
                return datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d')
            except (ValueError, TypeError) as e:
                logger.warning(f"Gagal mengkonversi timestamp {timestamp}: {e}")
                return None
        return None

    def get_user_quota(self, protocol, username):
        """
        Mendapatkan informasi kuota untuk user tertentu dari database.
        Response API sudah dikonversi ke format yang mudah dibaca.
        """
        try:
            # Validasi input
            if not protocol or protocol not in self.SUPPORTED_PROTOCOLS:
                return {"error": f"Protocol tidak valid. Gunakan: {', '.join(self.SUPPORTED_PROTOCOLS)}"}
            
            if not username or not isinstance(username, str):
                return {"error": "Username tidak valid"}
            
            logger.info(f"Mencari kuota untuk user: {username} di protokol: {protocol}")
            
            cursor = self.conn.cursor()
            # Query untuk mendapatkan semua data yang diperlukan
            query = """
                SELECT quota, quota_usage, expired_at, created_at, password_or_uuid
                FROM accounts 
                WHERE username = ? AND protocol = ? AND is_active = 1
            """
            cursor.execute(query, (username, protocol))
            row = cursor.fetchone()
            
            if not row:
                logger.warning(f"User {username} dengan protokol {protocol} tidak ditemukan atau tidak aktif di database.")
                return {"error": "User tidak ditemukan"}
            
            # --- Proses Konversi Data ---
            
            # 1. Konversi Kuota dari Bytes ke GB
            quota_limit_bytes = row['quota']
            quota_used_bytes = row['quota_usage']
            
            # Asumsi: quota <= 0 berarti unlimited
            is_unlimited = quota_limit_bytes <= 0
            
            quota_limit_gb = "Unlimited" if is_unlimited else round(quota_limit_bytes / self.BYTES_TO_GB, 2)
            quota_used_gb = round(quota_used_bytes / self.BYTES_TO_GB, 2)
            
            if is_unlimited:
                quota_remaining_gb = "Unlimited"
            else:
                quota_remaining_bytes = quota_limit_bytes - quota_used_bytes
                quota_remaining_gb = round(max(0, quota_remaining_bytes) / self.BYTES_TO_GB, 2)

            # 2. Konversi Timestamp dari Unix Epoch ke format YYYY-MM-DD
            expiry_date = self._convert_timestamp_to_date(row['expired_at'])
            created_at_date = self._convert_timestamp_to_date(row['created_at'])
            
            # --- Membangun Response API ---
            result = {
                "username": username,
                "protocol": protocol,
                "quota_limit_gb": quota_limit_gb,
                "quota_used_gb": quota_used_gb,
                "quota_remaining_gb": quota_remaining_gb,
                "is_unlimited": is_unlimited,
                "created_at": created_at_date,
                "expiry_date": expiry_date
            }
            
            # Tambahkan UUID atau password
            if protocol == "trojan":
                result["password"] = row['password_or_uuid']
            else: # vless, vmess
                result["uuid"] = row['password_or_uuid']
            
            return result
            
        except sqlite3.Error as e:
            logger.error(f"Error database saat mendapatkan kuota user {username}: {str(e)}")
            return {"error": f"Error database: {str(e)}"}
        except Exception as e:
            logger.error(f"Error umum saat mendapatkan kuota user {username}: {str(e)}")
            return {"error": f"Error mendapatkan kuota user: {str(e)}"}

    def get_all_users_quota(self):
        """
        Mendapatkan informasi kuota untuk semua user dari database.
        Response API sudah dikonversi ke format yang mudah dibaca.
        """
        try:
            logger.info("Memulai get_all_users_quota dari database")
            
            all_users = []
            cursor = self.conn.cursor()
            
            # Query untuk mendapatkan semua data user aktif
            query = """
                SELECT username, protocol, quota, quota_usage, expired_at, created_at, password_or_uuid
                FROM accounts 
                WHERE is_active = 1
            """
            cursor.execute(query)
            users_data = cursor.fetchall()
            
            logger.info(f"Ditemukan {len(users_data)} user aktif di database.")
            
            if not users_data:
                return {
                    "users": [],
                    "statistics": {
                        "total_users": 0,
                        "active_users": 0,
                        "expired_users": 0,
                        "quota_exceeded_users": 0
                    }
                }
                
            for user_row in users_data:
                username = user_row['username']
                protocol = user_row['protocol']
                
                # --- Proses Konversi Data ---

                # 1. Konversi Kuota dari Bytes ke GB
                quota_limit_bytes = user_row['quota']
                quota_used_bytes = user_row['quota_usage']
                
                is_unlimited = quota_limit_bytes <= 0
                
                quota_limit_gb = "Unlimited" if is_unlimited else round(quota_limit_bytes / self.BYTES_TO_GB, 2)
                quota_used_gb = round(quota_used_bytes / self.BYTES_TO_GB, 2)
                
                if is_unlimited:
                    quota_remaining_gb = "Unlimited"
                else:
                    quota_remaining_bytes = quota_limit_bytes - quota_used_bytes
                    quota_remaining_gb = round(max(0, quota_remaining_bytes) / self.BYTES_TO_GB, 2)

                # 2. Konversi Timestamp dari Unix Epoch ke format YYYY-MM-DD
                expiry_date = self._convert_timestamp_to_date(user_row['expired_at'])
                created_at_date = self._convert_timestamp_to_date(user_row['created_at'])
                
                # --- Menentukan Status User ---
                status = "active"
                is_expired = False
                if user_row['expired_at']:
                    try:
                        expiry_datetime = datetime.fromtimestamp(user_row['expired_at'])
                        if datetime.now() > expiry_datetime:
                            status = "expired"
                            is_expired = True
                    except (ValueError, TypeError):
                        pass # Abaikan jika timestamp tidak valid

                if not is_expired and not is_unlimited and quota_used_bytes >= quota_limit_bytes:
                    status = "quota_exceeded"
                
                # --- Membangun Response API ---
                user_info = {
                    "username": username,
                    "protocol": protocol,
                    "quota_limit_gb": quota_limit_gb,
                    "quota_used_gb": quota_used_gb,
                    "quota_remaining_gb": quota_remaining_gb,
                    "is_unlimited": is_unlimited,
                    "status": status,
                    "created_at": created_at_date,
                    "expiry_date": expiry_date
                }
                
                # Tambahkan UUID atau password
                if protocol == "trojan":
                    user_info["password"] = user_row['password_or_uuid']
                else: # vless, vmess
                    user_info["uuid"] = user_row['password_or_uuid']
                
                all_users.append(user_info)
                
            # --- Menghitung Statistik ---
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
                
        except sqlite3.Error as e:
            logger.error(f"Error database saat mendapatkan semua kuota user: {str(e)}")
            return {"error": f"Error database: {str(e)}"}
        except Exception as e:
            logger.error(f"Error umum saat mendapatkan semua kuota user: {str(e)}")
            return {"error": f"Error mendapatkan semua kuota user: {str(e)}"}

    def close_connection(self):
        """
        Menutup koneksi database. Sebaiknya dipanggil saat service dimatikan.
        """
        if self.conn:
            self.conn.close()
            logger.info("Koneksi database ditutup.")