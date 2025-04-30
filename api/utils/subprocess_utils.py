import subprocess
import logging
from typing import List, Dict, Optional

logger = logging.getLogger('vpn_api')

def run_subprocess(
    args: List[str],
    timeout: int = 30,
    env: Optional[Dict] = None
) -> Dict:
    """Run subprocess command with proper error handling"""
    default_env = {
        'TERM': 'xterm',
        'PATH': '/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin',
        'HOME': '/root'
    }
    
    try:
        result = subprocess.run(
            args,
            capture_output=True,
            text=True,
            timeout=timeout,
            env={**default_env, **(env or {})}
        )
        
        logger.debug(f"Command: {' '.join(args)}")
        logger.debug(f"Exit Code: {result.returncode}")
        logger.debug(f"Output: {result.stdout}")
        
        if result.returncode != 0:
            logger.error(f"Subprocess failed: {result.stderr}")
            return {
                'success': False,
                'error': result.stderr.strip(),
                'code': result.returncode
            }
            
        try:
            output = json.loads(result.stdout)
            return {'success': True, 'data': output}
        except json.JSONDecodeError:
            return {'success': True, 'data': result.stdout.strip()}
            
    except subprocess.TimeoutExpired:
        logger.error("Subprocess timeout")
        return {'success': False, 'error': 'Process timeout', 'code': 504}
    except Exception as e:
        logger.error(f"Subprocess error: {str(e)}")
        return {'success': False, 'error': str(e), 'code': 500}