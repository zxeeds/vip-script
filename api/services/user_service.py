import json
import logging
from typing import Dict, List, Optional
from utils.subprocess_utils import run_subprocess
from config.config_manager import ConfigManager

logger = logging.getLogger('vpn_api')
config = ConfigManager()

class UserService:
    PROTOCOL_SCRIPTS = {
        'vmess': {
            'add': '/usr/local/sbin/add-vme',
            'delete': '/usr/local/sbin/del-vme',
            'renew': '/usr/local/sbin/renew-vme'
        },
        'vless': {
            'add': '/usr/local/sbin/add-vle', 
            'delete': '/usr/local/sbin/del-vle',
            'renew': '/usr/local/sbin/renew-vle'
        },
        'trojan': {
            'add': '/usr/local/sbin/add-tro',
            'delete': '/usr/local/sbin/del-tro',
            'renew': '/usr/local/sbin/renew-tro'
        },
        'ssh': {
            'add': '/usr/local/sbin/add-ssh',
            'delete': '/usr/local/sbin/del-ssh',
            'renew': '/usr/local/sbin/renew-ssh'
        }
    }

    def _build_xray_args(self, protocol: str, action: str, data: Dict) -> List[str]:
        """Build arguments for Xray protocols (vmess, vless, trojan)"""
        username = data.get('username')
        quota = data.get('quota', 0)  # Default 0 (unlimited)
        ip_limit = data.get('ip_limit', 0) # Default 0 (no limit)
        masaaktif = data.get('validity', 30) # Default 30 hari

        if action == 'delete':
            # Untuk delete, hanya kirim username
            args = [
                self.PROTOCOL_SCRIPTS[protocol][action],
                username
            ]
        else:  # action == 'add' or 'renew'
            # Format: <script> <username> <quota_gb> <ip_limit> <masa_aktif>
            args = [
                self.PROTOCOL_SCRIPTS[protocol][action],
                username,
                str(quota),
                str(ip_limit),
                str(masaaktif)
            ]
        
        return args

    # --- PERUBAHAN 1: Menambahkan fungsi baru untuk membangun argumen SSH ---
    def _build_ssh_args(self, action: str, data: Dict) -> List[str]:
        """Build arguments for SSH protocol (add, renew, delete)"""
        username = data.get('username')
        password = data.get('password') # Password diperlukan untuk 'add'
        quota = data.get('quota', 0)
        ip_limit = data.get('ip_limit', 0)
        masaaktif = data.get('validity', 30)

        if action == 'delete':
            # Skrip delete hanya memerlukan username
            args = [
                self.PROTOCOL_SCRIPTS['ssh'][action],
                username
            ]
        elif action == 'add':
            # Skrip add memerlukan username dan password
            if not password:
                # Validasi ini sebagai jaga-jaga, meskipun sudah ada di manage_user
                raise ValueError("Password is required for adding SSH user.")
            args = [
                self.PROTOCOL_SCRIPTS['ssh'][action],
                username,
                password,  # <-- Argumen password ditambahkan di sini
                str(quota),
                str(ip_limit),
                str(masaaktif)
            ]
        else:  # action == 'renew'
            # Skrip renew tidak memerlukan password
            args = [
                self.PROTOCOL_SCRIPTS['ssh'][action],
                username,
                str(quota),
                str(ip_limit),
                str(masaaktif)
            ]
        return args

    def manage_user(self, data: Dict) -> Dict:
        """Main method to handle user management"""
        action = data.get('action', 'add').lower()
        protocol = data.get('protocol', 'vmess').lower()
        username = data.get('username')
        
        try:
            # Validasi tambahan
            if not username:
                return {
                    'success': False,
                    'error': 'Username is required',
                    'code': 400,
                    'data': None
                }

            # --- PERHATIKAN BAGIAN INI ---
            # Validasi password hanya untuk aksi 'add', bukan 'renew'
            if protocol == 'ssh' and action == 'add' and not data.get('password'):
                return {
                    'success': False,
                    'error': 'Password is required for SSH', # Pesan ini bisa disesuaikan
                    'code': 400,
                    'data': None
                }

            # --- PERUBAHAN 2: Memperbaiki logika routing untuk argumen ---
            # Jika protokolnya SSH, gunakan fungsi pembangun argumen SSH
            if protocol == 'ssh':
                args = self._build_ssh_args(action, data)
            else:
            # Jika bukan, gunakan fungsi pembangun argumen Xray
                args = self._build_xray_args(protocol, action, data)

            # Jalankan proses
            result = run_subprocess(args)
            
            # Standarisasi response
            if not isinstance(result, dict):
                logger.error(f"Invalid subprocess response: {result}")
                return {
                    'success': False,
                    'error': 'Invalid subprocess response',
                    'code': 500,
                    'data': None
                }
                    
            # Jika subprocess mengembalikan status error, log dengan detail
            if not result.get('success', False):
                logger.error(f"Subprocess error: {result.get('error')}")
                
            # Kembalikan hasil yang sudah distandarisasi
            return {
                'success': result.get('success', False),
                'data': result.get('data'),
                'error': result.get('error'),
                'code': result.get('code', 500) if not result.get('success', False) else 200
            }

        except KeyError as e:
            logger.error(f"Missing parameter: {str(e)}", exc_info=True)
            return {
                'success': False,
                'error': f'Missing parameter: {str(e)}',
                'code': 400,
                'data': None
            }
        except Exception as e:
            logger.error(f"Unexpected error: {str(e)}", exc_info=True)
            return {
                'success': False,
                'error': str(e),
                'code': 500,
                'data': None
            }


    def renew_user(self, protocol: str, username: str, data: Dict) -> Dict:
        """Alias untuk manage_user dengan action=renew"""
        data.update({'action': 'renew', 'protocol': protocol, 'username': username})
        return self.manage_user(data)