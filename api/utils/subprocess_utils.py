import subprocess
import logging
import json
from typing import List, Dict, Optional

logger = logging.getLogger('vpn_api')

def run_subprocess(args: List[str], timeout: int = 30, env: Optional[Dict] = None) -> Dict:
    """Run subprocess command with proper error handling"""
    default_env = {
        'TERM': 'xterm',
        'PATH': '/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin',
        'HOME': '/root'
    }
    
    process_env = default_env.copy()
    if env:
        process_env.update(env)
    
    try:
        logger.debug(f"Running command: {' '.join(args)}")
        result = subprocess.run(
            args,
            capture_output=True,
            text=True,
            timeout=timeout,
            env=process_env
        )
        
        logger.debug(f"Exit Code: {result.returncode}")
        logger.debug(f"Stdout: {result.stdout}")
        logger.debug(f"Stderr: {result.stderr}")
        
        if result.returncode != 0:
            error_msg = result.stderr.strip() or "Unknown error occurred"
            logger.error(f"Subprocess failed: {error_msg}")
            return {
                'success': False,
                'error': error_msg,
                'code': result.returncode
            }
        
        # Jika output kosong, berikan respons default
        if not result.stdout.strip():
            return {
                'success': True,
                'data': {'message': 'Operation completed successfully'}
            }
        
        # Coba parse JSON, jika gagal kembalikan raw output
        try:
            output = json.loads(result.stdout)
            # Periksa apakah output JSON memiliki status error
            if output.get('status') == 'error':
                return {
                    'success': False,
                    'error': output.get('message', 'Unknown error'),
                    'code': 400  # Gunakan kode yang sesuai
                }
            return {'success': True, 'data': output}
        except json.JSONDecodeError:
            return {
                'success': True, 
                'data': {'message': result.stdout.strip()}
            }

            
    except subprocess.TimeoutExpired:
        logger.error("Subprocess timeout")
        return {'success': False, 'error': 'Process timeout', 'code': 504}
    except Exception as e:
        logger.error(f"Subprocess error: {str(e)}", exc_info=True)
        return {'success': False, 'error': str(e), 'code': 500}