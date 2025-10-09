import os
import uuid
import base64
import json
import subprocess
import secrets
from datetime import datetime, timedelta
from utils.logger import logger
from config.config_manager import ConfigManager

class TrojanTrialService:
    def __init__(self):
        self.config = ConfigManager()
        self.domain = self.config.get('DOMAIN')
        self.xray_config_path = self.config.get('XRAY_CONFIG_PATH', '/etc/xray/config.json')
        self.protocol = 'trojan'
        logger.info(f"Initialized TrojanTrialService with domain: {self.domain}")

    def generate_credentials(self):
        # Trojan menggunakan password
        return {
            "password": secrets.token_urlsafe(32)
        }

    def run_command(self, command):
        result = subprocess.run(command, shell=True, capture_output=True, text=True)
        if result.returncode != 0:
            logger.error(f"Command failed: {command}, Error: {result.stderr}")
            raise Exception(f"Command failed: {result.stderr}")
        return result.stdout.strip()

    def add_to_xray_config(self, user, credentials, expiry):
        password = credentials['password']
        # Backup config
        self.run_command(f"cp {self.xray_config_path} {self.xray_config_path}.bak")
        
        with open(self.xray_config_path, 'r') as f:
            content = f.read()
        
        # Add Trojan entries
        new_entry = f'#! {user} {expiry}\n{{"password": "{password}","email": "{user}"}}'
        content = content.replace('#trojan', f'#trojan\n{new_entry}')
        content = content.replace('#trojangprc', f'#trojangprc\n{new_entry}')
        
        with open(self.xray_config_path, 'w') as f:
            f.write(content)
        
        logger.info(f"Added Trojan user {user} to Xray config")

    def generate_links(self, user, credentials):
        password = credentials['password']
        
        # Trojan WS TLS
        trojan_tls = f"trojan://{password}@{self.domain}:443?security=tls&type=ws&host={self.domain}&path=%2Ftrojan&sniname={self.domain}#{user}"
        
        # Trojan gRPC
        trojan_grpc = f"trojan://{password}@{self.domain}:443?security=tls&type=grpc&host={self.domain}&serviceName=trojan-grpc&sniname={self.domain}#{user}"
        
        return {
            "tls": trojan_tls,
            "grpc": trojan_grpc
        }

    def ensure_directory_exists(self, path):
        os.makedirs(path, exist_ok=True)

    def restart_services(self):
        self.run_command("systemctl restart xray")
        self.run_command("service cron restart")
        logger.info("Services restarted")

    def get_expiry_time(self, minutes):
        return (datetime.now() + timedelta(minutes=minutes)).strftime("%Y-%m-%d %H:%M:%S")

    def generate_username(self):
        return f"Trial{secrets.token_hex(3).upper()}"

    def set_limits(self, user, quota, iplimit):
        # Set IP limit
        self.ensure_directory_exists("/etc/kyt/limit/trojan/ip")
        with open(f"/etc/kyt/limit/trojan/ip/{user}", "w") as f:
            f.write(str(iplimit))
        
        # Set quota (dalam byte)
        quota_bytes = quota * 1024 * 1024 * 1024
        self.ensure_directory_exists("/etc/trojan")
        with open(f"/etc/trojan/{user}", "w") as f:
            f.write(str(quota_bytes))
        
        logger.info(f"Set Trojan limits for {user}: quota={quota}GB, iplimit={iplimit}")

    def update_database(self, user, expiry, credentials):
        db_path = self.config.get('TROJAN_DB_PATH', '/etc/trojan/.trojan.db')
        with open(db_path, "a") as f:
            f.write(f"### {user} {expiry} {credentials['password']}\n")
        logger.info(f"Updated Trojan database for {user}")

    def create_config_file(self, user, credentials, links):
        content = self.generate_config_content(user, credentials, links)
        self.ensure_directory_exists("/var/www/html")
        with open(f"/var/www/html/trojan-{user}.txt", "w") as f:
            f.write(content)
        logger.info(f"Created Trojan config file for {user}")

    def generate_config_content(self, user, credentials, links):
        password = credentials['password']
        return f"""———————————————————————————————————————
  VIP SCRIPT - TROJAN
———————————————————————————————————————
 https://github.com/jaka1m/project
———————————————————————————————————————
# Format Trojan WS TLS

- name: Trojan-{user}-WS TLS
  type: trojan
  server: {self.domain}
  port: 443
  password: {password}
  udp: true
  tls: true
  skip-cert-verify: true
  servername: {self.domain}
  network: ws
  ws-opts:
    path: /trojan
    headers:
      Host: {self.domain}

# Format Trojan gRPC

- name: Trojan-{user}-gRPC (SNI)
  server: {self.domain}
  port: 443
  type: trojan
  password: {password}
  udp: true
  tls: true
  skip-cert-verify: true
  servername: {self.domain}
  network: grpc
  grpc-opts:
    grpc-service-name: trojan-grpc

———————————————————————————————————————
 Link Akun Trojan                   
———————————————————————————————————————
Link TLS         : 
{links['tls']}
———————————————————————————————————————
Link GRPC        : 
{links['grpc']}
———————————————————————————————————————
"""

    def create_trial_account(self, minutes, quota, iplimit):
        # Generate username
        user = self.generate_username()
        
        # Generate credentials
        credentials = self.generate_credentials()
        
        # Calculate expiry
        expiry = self.get_expiry_time(minutes)
        
        # Add to Xray config
        self.add_to_xray_config(user, credentials, expiry)
        
        # Generate links
        links = self.generate_links(user, credentials)
        
        # Set limits
        self.set_limits(user, quota, iplimit)
        
        # Update database
        self.update_database(user, expiry, credentials)
        
        # Create config file
        self.create_config_file(user, credentials, links)
        
        # Restart services
        self.restart_services()

        return {
            "username": user,
            "credentials": credentials,
            "expiry": expiry,
            "links": links,
            "config_url": f"https://{self.domain}:81/trojan-{user}.txt"
        }