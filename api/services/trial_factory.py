import subprocess
import json
from utils.logger import logger
from abc import ABC, abstractmethod

# --- Abstract Base Class untuk Trial Services ---
# Ini memastikan bahwa setiap service yang dibuat akan memiliki metode yang sama.
class TrialService(ABC):
    @abstractmethod
    def create_trial_account(self, minutes: int, quota: int, iplimit: int) -> str:
        """
        Menjalankan script trial dan mengembalikan output JSON mentah.
        """
        pass

# --- Concrete Service untuk SSH ---
class SshTrialService(TrialService):
    def __init__(self, script_path: str):
        self.script_path = script_path

    def create_trial_account(self, minutes: int, quota: int, iplimit: int) -> str:
        command = [self.script_path, 'api', str(minutes), str(quota), str(iplimit)]
        logger.info(f"Executing SSH trial script: {' '.join(command)}")
        
        try:
            # Jalankan script menggunakan subprocess
            result = subprocess.run(
                command,
                capture_output=True,  # Tangkap stdout dan stderr
                text=True,            # Hasil tangkapan dalam bentuk string
                check=True            # Anggap error jika return code != 0
                # cwd telah dihapus karena script berada di lokasi sistem
            )
            # Kembalikan output stdout (yang berupa JSON string) tanpa modifikasi
            return result.stdout.strip()
        except FileNotFoundError:
            logger.error(f"Script not found at {self.script_path}")
            raise Exception(f"SSH trial script not found.")
        except subprocess.CalledProcessError as e:
            # Jika script mengembalikan error, tangkap stderr-nya
            logger.error(f"SSH script execution failed with error: {e.stderr}")
            # Coba parsing error JSON dari script untuk pesan yang lebih jelas
            try:
                error_details = json.loads(e.stderr.strip())
                raise Exception(error_details.get('message', e.stderr))
            except json.JSONDecodeError:
                # Jika stderr bukan JSON, kirimkan apa adanya
                raise Exception(f"Script execution failed: {e.stderr.strip()}")

# --- Concrete Service untuk VMESS ---
class VmessTrialService(TrialService):
    def __init__(self, script_path: str):
        self.script_path = script_path

    def create_trial_account(self, minutes: int, quota: int, iplimit: int) -> str:
        command = [self.script_path, 'api', str(minutes), str(quota), str(iplimit)]
        logger.info(f"Executing VMESS trial script: {' '.join(command)}")

        try:
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                check=True
                # cwd telah dihapus karena script berada di lokasi sistem
            )
            return result.stdout.strip()
        except FileNotFoundError:
            logger.error(f"Script not found at {self.script_path}")
            raise Exception(f"VMESS trial script not found.")
        except subprocess.CalledProcessError as e:
            logger.error(f"VMESS script execution failed with error: {e.stderr}")
            try:
                error_details = json.loads(e.stderr.strip())
                raise Exception(error_details.get('message', e.stderr))
            except json.JSONDecodeError:
                raise Exception(f"Script execution failed: {e.stderr.strip()}")

class TrojanTrialService(TrialService):
    def __init__(self, script_path: str):
        self.script_path = script_path

    def create_trial_account(self, minutes: int, quota: int, iplimit: int) -> str:
        command = [self.script_path, 'api', str(minutes), str(quota), str(iplimit)]
        logger.info(f"Executing Trojan trial script: {' '.join(command)}")

        try:
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                check=True
                # cwd telah dihapus karena script berada di lokasi sistem
            )
            return result.stdout.strip()
        except FileNotFoundError:
            logger.error(f"Script not found at {self.script_path}")
            raise Exception(f"Trojan trial script not found.")
        except subprocess.CalledProcessError as e:
            logger.error(f"Trojan script execution failed with error: {e.stderr}")
            try:
                error_details = json.loads(e.stderr.strip())
                raise Exception(error_details.get('message', e.stderr))
            except json.JSONDecodeError:
                raise Exception(f"Script execution failed: {e.stderr.strip()}")

class VlessTrialService(TrialService):
    def __init__(self, script_path: str):
        self.script_path = script_path

    def create_trial_account(self, minutes: int, quota: int, iplimit: int) -> str:
        command = [self.script_path, 'api', str(minutes), str(quota), str(iplimit)]
        logger.info(f"Executing VLESS trial script: {' '.join(command)}")

        try:
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                check=True
                # cwd telah dihapus karena script berada di lokasi sistem
            )
            return result.stdout.strip()
        except FileNotFoundError:
            logger.error(f"Script not found at {self.script_path}")
            raise Exception(f"Vless trial script not found.")
        except subprocess.CalledProcessError as e:
            logger.error(f"Vless script execution failed with error: {e.stderr}")
            try:
                error_details = json.loads(e.stderr.strip())
                raise Exception(error_details.get('message', e.stderr))
            except json.JSONDecodeError:
                raise Exception(f"Script execution failed: {e.stderr.strip()}")

# --- Factory untuk membuat service yang tepat ---
class TrialServiceFactory:
    # Mapping protokol ke path script (LOKASI DIPERBARUI)
    _script_paths = {
        'ssh': '/usr/local/sbin/trial-ssh',
        'vmess': '/usr/local/sbin/trial-vme',
        'trojan': '/usr/local/sbin/trial-tro', 
        'vless': '/usr/local/sbin/trial-vle',
    }

    @classmethod
    def create_service(cls, protocol: str) -> TrialService:
        """Membuat instance service berdasarkan protokol."""
        protocol = protocol.lower()
        if protocol not in cls._script_paths:
            logger.error(f"Unsupported protocol requested: {protocol}")
            raise ValueError(f"Protocol '{protocol}' is not supported. Supported protocols are: {list(cls._script_paths.keys())}")

        script_path = cls._script_paths[protocol]
        
        if protocol == 'ssh':
            return SshTrialService(script_path)
        elif protocol == 'vmess':
            return VmessTrialService(script_path)
        elif protocol == 'trojan': # TAMBAHKAN BLOK INI
            return TrojanTrialService(script_path)
        elif protocol == 'vless': # TAMBAHKAN BLOK INI
            return VlessTrialService(script_path) 
        
        # Ini sebagai pengaman, seharusnya tidak tercapai
        raise ValueError(f"Service for protocol '{protocol}' is not implemented.")