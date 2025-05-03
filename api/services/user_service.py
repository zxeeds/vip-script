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

    def _build_ssh_args(self, action: str, data: Dict) -> List[str]:
        """Build arguments for SSH commands"""
        args = [
            self.PROTOCOL_SCRIPTS['ssh'][action],
            'api',
            '--username', data['username'],
            '--password', data['password'],
            '--limit', str(data.get('ip_limit', 2)),
            '--duration', str(data.get('validity', 30)),
            '--quota', str(data.get('quota', 0))
        ]
        return args

    def _build_xray_args(self, protocol: str, action: str, data: Dict) -> List[str]:
        """Build arguments for Xray protocols"""
        if action == 'delete':
            # Untuk delete, hanya kirim username
            args = [
                self.PROTOCOL_SCRIPTS[protocol][action],
                data['username']
            ]
        elif action == 'renew':
            # Untuk renew, kirim dalam format yang sesuai dengan script renew-vme yang dimodifikasi
            args = [
                self.PROTOCOL_SCRIPTS[protocol][action],
                'api',
                '--username', data['username'],
                '--quota', str(data.get('quota', 100)),
                '--limit', str(data.get('ip_limit', 3)),
                '--duration', str(data.get('validity', 30))
            ]
        else:  # action == 'add'
            # Untuk add, kirim semua parameter dalam format posisional
            args = [
                self.PROTOCOL_SCRIPTS[protocol][action],
                data['username'],
                str(data.get('quota', 100)),
                str(data.get('ip_limit', 3)),
                str(data.get('validity', 30))
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

            if protocol == 'ssh' and action == 'add' and not data.get('password'):
                return {
                    'success': False,
                    'error': 'Password is required for SSH',
                    'code': 400,
                    'data': None
                }

            # Bangun argumen
            if protocol == 'ssh' and action == 'add':
                args = self._build_ssh_args(action, data)
            else:
                args = self._build_xray_args(protocol, action, data)

            if action == 'delete':
                args.append("api_mode")

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