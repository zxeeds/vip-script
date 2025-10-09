import os
import secrets
import string
import subprocess
from datetime import datetime, timedelta
from utils.logger import logger
from config.config_manager import ConfigManager

class SSHTrialService:
    def __init__(self):
        self.config = ConfigManager()
        self.domain = self.config.get('DOMAIN')
        self.protocol = 'ssh'
        # Path-path ini disesuaikan dari script shell Anda
        self.ssh_db_path = '/etc/ssh/.ssh.db'
        self.limit_ip_dir = '/etc/kyt/limit/ssh/ip'
        self.config_dir = '/var/www/html'
        logger.info(f"Initialized SSHTrialService with domain: {self.domain}")

    def generate_username(self):
        # Menggunakan logika yang sama dengan VMess untuk konsistensi
        return f"Trial{secrets.token_hex(3).upper()}"

    def generate_password(self, length=8):
        # Membuat password acak dari huruf dan angka
        characters = string.ascii_letters + string.digits
        return ''.join(secrets.choice(characters) for _ in range(length))

    def generate_credentials(self):
        return {
            "username": self.generate_username(),
            "password": self.generate_password(secrets.randbelow(8) + 1) # Panjang 1-8 karakter
        }

    def run_command(self, command):
        result = subprocess.run(command, shell=True, capture_output=True, text=True)
        if result.returncode != 0:
            logger.error(f"Command failed: {command}, Error: {result.stderr}")
            raise Exception(f"Command failed: {result.stderr}")
        return result.stdout.strip()

    def add_user_to_system(self, user, password, expiry_date):
        """
        Menambahkan user ke sistem Linux dan mengatur password serta expiry.
        """
        logger.info(f"Creating system user: {user}")
        
        # 1. Buat user tanpa home directory dan tanpa shell access
        self.run_command(f"useradd -e {expiry_date} -s /bin/false -M {user}")
        
        # 2. Atur password menggunakan chpasswd (lebih aman daripada pipe ke passwd)
        # Format untuk chpasswd adalah "username:password"
        self.run_command(f"echo '{user}:{password}' | chpasswd")
        
        logger.info(f"System user {user} created with password.")

    def generate_connection_info(self, user, credentials):
        """
        Menghasilkan informasi koneksi, bukan link seperti VMess.
        """
        ip_address = self.run_command("curl -sS ipv4.icanhazip.com")
        
        return {
            "ip_address": ip_address,
            "hostname": self.domain,
            "username": credentials['username'],
            "password": credentials['password'],
            "ports": {
                "openssh": "22, 143",
                "dropbear": "443, 109, 143",
                "ssh_ws_tls": "443",
                "ssh_ws_non_tls": "80, 8080, 8081-9999",
                "ssl_tls": "400-900"
            },
            "payload": "GET / HTTP/1.1[crlf]Host: [host][crlf]Connection: Upgrade[crlf]User-Agent: [ua][crlf]Upgrade: websocket[crlf][crlf]"
        }

    def ensure_directory_exists(self, path):
        os.makedirs(path, exist_ok=True)

    def set_limits(self, user, iplimit):
        """
        Menerapkan batasan IP.
        """
        logger.info(f"Setting SSH limits for {user}: iplimit={iplimit}")
        self.ensure_directory_exists(self.limit_ip_dir)
        with open(f"{self.limit_ip_dir}/{user}", "w") as f:
            f.write(str(iplimit))

    def update_database(self, user, expiry):
        """
        Mencatat akun ke database internal SSH.
        """
        logger.info(f"Updating SSH database for {user}")
        with open(self.ssh_db_path, "a") as f:
            f.write(f"### {user} {expiry}\n")

    def create_config_file(self, user, info):
        """
        Membuat file konfigurasi .txt untuk diunduh pengguna.
        """
        content = self.generate_config_content(user, info)
        self.ensure_directory_exists(self.config_dir)
        file_path = f"{self.config_dir}/ssh-{user}.txt"
        with open(file_path, "w") as f:
            f.write(content)
        logger.info(f"Created SSH config file for {user} at {file_path}")

    def generate_config_content(self, user, info):
        return f"""———————————————————————————————————————
Format SSH Account
———————————————————————————————————————
Username         : {info['username']}
Password         : {info['password']}
———————————————————————————————————————
IP Address       : {info['ip_address']}
Host             : {info['hostname']}
Port OpenSSH     : {info['ports']['openssh']}
Port Dropbear    : {info['ports']['dropbear']}
Port SSH WS      : {info['ports']['ssh_ws_non_tls']}
Port SSH SSL WS  : {info['ports']['ssh_ws_tls']}
Port SSL/TLS     : {info['ports']['ssl_tls']}
———————————————————————————————————————
Payload          : {info['payload']}
———————————————————————————————————————
"""

    def restart_services(self):
        """
        Me-restart layanan SSH untuk menerapkan perubahan.
        'reload' lebih disukai karena tidak memutus koneksi yang ada.
        """
        logger.info("Reloading SSH service...")
        self.run_command("systemctl reload ssh")
        logger.info("SSH service reloaded.")

    def get_expiry_date(self, minutes):
        """
        Menghasilkan tanggal expiry dalam format YYYY-MM-DD untuk perintah 'useradd'.
        """
        return (datetime.now() + timedelta(minutes=minutes)).strftime("%Y-%m-%d")

    def create_trial_account(self, minutes, quota, iplimit):
        """
        Fungsi utama untuk membuat akun trial SSH.
        """
        # Generate credentials
        credentials = self.generate_credentials()
        user = credentials['username']
        password = credentials['password']
        
        # Calculate expiry
        expiry_date = self.get_expiry_date(minutes)
        expiry_str = (datetime.now() + timedelta(minutes=minutes)).strftime("%Y-%m-%d %H:%M:%S")
        
        # Create user in system
        self.add_user_to_system(user, password, expiry_date)
        
        # Set limits
        self.set_limits(user, iplimit)
        
        # Update database
        self.update_database(user, expiry_str)
        
        # Generate connection info
        info = self.generate_connection_info(user, credentials)
        
        # Create config file
        self.create_config_file(user, info)
        
        # Restart service
        self.restart_services()

        
        # 1. Buat link untuk SSH over WebSocket (Non-TLS)
        ws_link = f"{self.domain}:80@{user}:{password}"
        
        # 2. Buat link untuk SSH over WebSocket (TLS/SSL)
        ssl_link = f"{self.domain}:443@{user}:{password}"
        
        # 3. Buat link untuk koneksi berbasis UDP (asumsi port 7300 dari range SSL/TLS)
        udp_link = f"{self.domain}:1-7300@{user}:{password}"
        
        # 4. Buat string informasi port dari dictionary
        ports_info = f"""OpenSSH: {info['ports']['openssh']}
Dropbear: {info['ports']['dropbear']}
SSH WS (TLS): {info['ports']['ssh_ws_tls']}
SSH WS (Non-TLS): {info['ports']['ssh_ws_non_tls']}
SSL/TLS: {info['ports']['ssl_tls']}"""

        return {
            "username": user,
            "password": password,
            "domain": self.domain,
            "expired": expiry_str,
            "quota": quota,
            "ip_limit": iplimit,
            "links": {
                "ws": ws_link,
                "ssl": ssl_link,
                "udp": udp_link
            },
            "ports": ports_info
        }