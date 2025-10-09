from services.trial_vme import VMessTrialService
from services.trial_vle import VLESSTrialService
from services.trial_tro import TrojanTrialService
from services.trial_ssh import SSHTrialService
from utils.logger import logger

class TrialServiceFactory:
    @staticmethod
    def create_service(protocol):
        if protocol == 'vmess':
            return VMessTrialService()
        elif protocol == 'vless':
            return VLESSTrialService()
        elif protocol == 'trojan':
            return TrojanTrialService()
        elif protocol == 'ssh':
            return SSHTrialService()
        else:
            error_msg = f"Unsupported protocol: {protocol}"
            logger.error(error_msg)
            raise ValueError(error_msg)