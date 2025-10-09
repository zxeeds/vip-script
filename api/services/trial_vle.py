import os
import uuid
import base64
import json
import subprocess
import secrets
from datetime import datetime, timedelta
from utils.logger import logger
from config.config_manager import ConfigManager

class VLESSTrialService:
    def __init__(self):
        self.config = ConfigManager()
        self.domain = self.config.get('DOMAIN')
        self.xray_config_path = self.config.get('XRAY_CONFIG_PATH', '/etc/xray/config.json')
        self.protocol = 'vless'
        logger.info(f"Initialized VLESSTrialService with domain: {self.domain}")

    def generate_credentials(self):
        # VLESS hanya membutuhkan UUID
        return {
            "uuid": str(uuid.uuid4())
        }

    def run_command(self, command):
        result = subprocess.run(command, shell=True, capture_output=True, text=True)
        if result.returncode != 0:
            logger.error(f"Command failed: {command}, Error: {result.stderr}")
            raise Exception(f"Command failed: {result.stderr}")
        return result.stdout.strip()

    def add_to_xray_config(self, user, credentials, expiry):
        uuid = credentials['uuid']
        # Backup config
        self.run_command(f"cp {self.xray_config_path} {self.xray_config_path}.bak")
        
        with open(self.xray_config_path, 'r') as f:
            content = f.read()
        
        # Add VLESS entries
        new_entry = f'#& {user} {expiry}\n{{"id": "{uuid}","email": "{user}"}}'
        content = content.replace('#vlessws', f'#vlessws\n{new_entry}')
        content = content.replace('#vlessgrpc', f'#vlessgrpc\n{new_entry}')
        
        with open(self.xray_config_path, 'w') as f:
            f.write(content)
        
        logger.info(f"Added VLESS user {user} to Xray config")

    def generate_links(self, user, credentials):
        uuid = credentials['uuid']
        
        # VLESS WS TLS
        vless_tls = f"vless://{uuid}@{self.domain}:443?encryption=none&security=tls&type=ws&host={self.domain}&path=%2Fvless&sniname={self.domain}#{user}"
        
        # VLESS WS Non-TLS
        vless_non_tls = f"vless://{uuid}@{self.domain}:80?encryption=none&security=none&type=ws&host={self.domain}&path=%2Fvless#{user}"
        
        # VLESS gRPC
        vless_grpc = f"vless://{uuid}@{self.domain}:443?encryption=none&security=tls&type=grpc&host={self.domain}&serviceName=vless-grpc&sniname={self.domain}#{user}"
        
        return {
            "tls": vless_tls,
            "non_tls": vless_non_tls,
            "grpc": vless_grpc
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
        self.ensure_directory_exists("/etc/kyt/limit/vless/ip")
        with open(f"/etc/kyt/limit/vless/ip/{user}", "w") as f:
            f.write(str(iplimit))
        
        # Set quota (dalam byte)
        quota_bytes = quota * 1024 * 1024 * 1024
        self.ensure_directory_exists("/etc/vless")
        with open(f"/etc/vless/{user}", "w") as f:
            f.write(str(quota_bytes))
        
        logger.info(f"Set VLESS limits for {user}: quota={quota}GB, iplimit={iplimit}")

    def update_database(self, user, expiry, credentials):
        db_path = self.config.get('VLESS_DB_PATH', '/etc/vless/.vless.db')
        with open(db_path, "a") as f:
            f.write(f"### {user} {expiry} {credentials['uuid']}\n")
        logger.info(f"Updated VLESS database for {user}")

    def create_config_file(self, user, credentials, links):
        content = self.generate_config_content(user, credentials, links)
        self.ensure_directory_exists("/var/www/html")
        with open(f"/var/www/html/vless-{user}.txt", "w") as f:
            f.write(content)
        logger.info(f"Created VLESS config file for {user}")

    def generate_config_content(self, user, credentials, links):
        uuid = credentials['uuid']
        return f"""———————————————————————————————————————
  VIP SCRIPT - VLESS
———————————————————————————————————————
# Format Vless WS TLS

- name: Vless-{user}-WS TLS
  type: vless
  server: {self.domain}
  port: 443
  uuid: {uuid}
  udp: true
  tls: true
  skip-cert-verify: true
  servername: {self.domain}
  network: ws
  ws-opts:
    path: /vless
    headers:
      Host: {self.domain}

# Format Vless WS Non TLS

- name: Vless-{user}-WS Non TLS
  type: vless
  server: {self.domain}
  port: 80
  uuid: {uuid}
  udp: true
  tls: false
  network: ws
  ws-opts:
    path: /vless
    headers:
      Host: {self.domain}

# Format Vless gRPC

- name: Vless-{user}-gRPC (SNI)
  server: {self.domain}
  port: 443
  type: vless
  uuid: {uuid}
  udp: true
  tls: true
  skip-cert-verify: true
  servername: {self.domain}
  network: grpc
  grpc-opts:
    grpc-service-name: vless-grpc

———————————————————————————————————————
 Link Akun Vless                   
———————————————————————————————————————
Link TLS         : 
{links['tls']}
———————————————————————————————————————
Link none TLS    : 
{links['non_tls']}
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
            "domain": self.domain,
            "uuid": credentials['uuid'],
            "expired": expiry,
            "quota": quota,
            "ip_limit": iplimit,
            "links": links
        }