import os
import uuid
import base64
import json
import subprocess
import secrets
from datetime import datetime, timedelta
from utils.logger import logger
from config.config_manager import ConfigManager

class VMessTrialService:
    def __init__(self):
        self.config = ConfigManager()
        self.domain = self.config.get('DOMAIN')
        self.xray_config_path = self.config.get('XRAY_CONFIG_PATH', '/etc/xray/config.json')
        self.protocol = 'vmess'
        logger.info(f"Initialized VMessTrialService with domain: {self.domain}")

    def generate_credentials(self):
        return {
            "uuid": str(uuid.uuid4()),
            "alterId": 0
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
        
        # Add VMess entries
        new_entry = f'### {user} {expiry}\n{{"id": "{uuid}","alterId": 0,"email": "{user}"}}'
        content = content.replace('#vmess', f'#vmess\n{new_entry}')
        content = content.replace('#vmessgprc', f'#vmessgprc\n{new_entry}')
        
        with open(self.xray_config_path, 'w') as f:
            f.write(content)
        
        logger.info(f"Added VMess user {user} to Xray config")

    def generate_links(self, user, credentials):
        uuid = credentials['uuid']
        
        # VMess WS TLS
        vmess_tls = {
            "v": "2", "ps": user, "add": self.domain, "port": "443",
            "id": uuid, "aid": "0", "net": "ws", "path": "/vmess",
            "type": "none", "host": self.domain, "tls": "tls"
        }
        tls_link = "vmess://" + base64.b64encode(json.dumps(vmess_tls).encode()).decode()
        
        # VMess WS Non-TLS
        vmess_non_tls = {
            "v": "2", "ps": user, "add": self.domain, "port": "80",
            "id": uuid, "aid": "0", "net": "ws", "path": "/vmess",
            "type": "none", "host": self.domain, "tls": "none"
        }
        non_tls_link = "vmess://" + base64.b64encode(json.dumps(vmess_non_tls).encode()).decode()
        
        # VMess gRPC
        vmess_grpc = {
            "v": "2", "ps": user, "add": self.domain, "port": "443",
            "id": uuid, "aid": "0", "net": "grpc", "path": "vmess-grpc",
            "type": "none", "host": self.domain, "tls": "tls"
        }
        grpc_link = "vmess://" + base64.b64encode(json.dumps(vmess_grpc).encode()).decode()
        
        return {
            "tls": tls_link,
            "non_tls": non_tls_link,
            "grpc": grpc_link
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
        self.ensure_directory_exists("/etc/kyt/limit/vmess/ip")
        with open(f"/etc/kyt/limit/vmess/ip/{user}", "w") as f:
            f.write(str(iplimit))
        
        # Set quota (dalam byte)
        quota_bytes = quota * 1024 * 1024 * 1024
        self.ensure_directory_exists("/etc/vmess")
        with open(f"/etc/vmess/{user}", "w") as f:
            f.write(str(quota_bytes))
        
        logger.info(f"Set limits for {user}: quota={quota}GB, iplimit={iplimit}")

    def update_database(self, user, expiry, credentials):
        db_path = self.config.get('VMESS_DB_PATH', '/etc/vmess/.vmess.db')
        with open(db_path, "a") as f:
            f.write(f"### {user} {expiry} {credentials['uuid']}\n")
        logger.info(f"Updated database for {user}")

    def create_config_file(self, user, credentials, links):
        content = self.generate_config_content(user, credentials, links)
        self.ensure_directory_exists("/var/www/html")
        with open(f"/var/www/html/vmess-{user}.txt", "w") as f:
            f.write(content)
        logger.info(f"Created config file for {user}")

    def generate_config_content(self, user, credentials, links):
        uuid = credentials['uuid']
        return f"""———————————————————————————————————————
  VIP SCRIPT
———————————————————————————————————————
 https://github.com/jaka1m/project
———————————————————————————————————————
# Format Vmess WS TLS

- name: Vmess-{user}-WS TLS
  type: vmess
  server: {self.domain}
  port: 443
  uuid: {uuid}
  alterId: 0
  cipher: auto
  udp: true
  tls: true
  skip-cert-verify: true
  servername: {self.domain}
  network: ws
  ws-opts:
    path: /vmess
    headers:
      Host: {self.domain}

# Format Vmess WS Non TLS

- name: Vmess-{user}-WS Non TLS
  type: vmess
  server: {self.domain}
  port: 80
  uuid: {uuid}
  alterId: 0
  cipher: auto
  udp: true
  tls: false
  skip-cert-verify: false
  servername: {self.domain}
  network: ws
  ws-opts:
    path: /vmess
    headers:
      Host: {self.domain}

# Format Vmess gRPC

- name: Vmess-{user}-gRPC (SNI)
  server: {self.domain}
  port: 443
  type: vmess
  uuid: {uuid}
  alterId: 0
  cipher: auto
  network: grpc
  tls: true
  servername: {self.domain}
  skip-cert-verify: true
  grpc-opts:
    grpc-service-name: vmess-grpc

———————————————————————————————————————
 Link Akun Vmess                   
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
            "credentials": credentials,
            "expiry": expiry,
            "links": links,
            "config_url": f"https://{self.domain}:81/vmess-{user}.txt"
        }