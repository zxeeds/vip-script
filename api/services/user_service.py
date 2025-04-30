import logging
from typing import Dict, Optional
from utils.subprocess_utils import run_subprocess
from config.config_manager import ConfigManager
from typing import Dict, List

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

    def _validate_input(self, data: Dict) -> Optional[Dict]:
        """Validasi input dasar"""
        if 'username' not in data:
            return {'success': False, 'error': 'Username wajib diisi', 'code': 400}
        
        if data.get('protocol') not in self.PROCOL_SCRIPTS:
            return {'success': False, 'error': 'Protokol tidak didukung', 'code': 400}
        
        action = data.get('action', 'add').lower()
        if action not in ['add', 'delete', 'renew']:
            return {'success': False, 'error': 'Action tidak valid', 'code': 400}
        
        return None

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
        args = [
            self.PROTOCOL_SCRIPTS[protocol][action],
            data['username'],
            str(data.get('quota', 100)),
            str(data.get('ip_limit', 3)),
            str(data.get('validity', 30))
        ]
        return args

    def manage_user(self, data: Dict) -> Dict:
        """Main method untuk manage user"""
        if error := self._validate_input(data):
            return error

        action = data.get('action', 'add').lower()
        protocol = data.get('protocol', 'vmess').lower()

        try:
            if protocol == 'ssh' and action == 'add':
                args = self._build_ssh_args(action, data)
            else:
                args = self._build_xray_args(protocol, action, data)

            if action == 'delete':
                args.append("api_mode")

            return run_subprocess(args)

        except KeyError as e:
            logger.error(f"Parameter kurang: {str(e)}")
            return {'success': False, 'error': f"Parameter kurang: {str(e)}", 'code': 400}
        except Exception as e:
            logger.error(f"Error: {str(e)}")
            return {'success': False, 'error': str(e), 'code': 500}

    def renew_user(self, protocol: str, username: str, data: Dict) -> Dict:
        """Alias untuk manage_user dengan action=renew"""
        data.update({'action': 'renew', 'protocol': protocol, 'username': username})
        return self.manage_user(data)