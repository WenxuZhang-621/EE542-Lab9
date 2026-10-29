"""Run with python -m rag.run_upload from the repository root."""
import os
import subprocess
import sys
from shared.config import CONFIG, ROOT


def main():
    env = dict(os.environ)
    env['PYTHONPATH'] = str(ROOT) + os.pathsep + env.get('PYTHONPATH', '')
    result = subprocess.run([
        sys.executable, '-m', 'streamlit', 'run', str(ROOT / 'rag/upload_app.py'),
        '--server.address', CONFIG['services']['host'],
        '--server.port', str(CONFIG['services']['upload_port']),
        '--server.maxUploadSize', '20',
        '--server.headless', 'true',
        '--browser.gatherUsageStats', 'false',
    ], cwd=ROOT, env=env)
    raise SystemExit(result.returncode)


if __name__ == '__main__':
    main()
