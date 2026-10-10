"""Production adapter for the repository's existing single-user AnalysisService.

Place at repository root beside src/. Configure via hosting environment variables.
No scientific algorithms or API handlers are replaced.
"""
import fcntl
import os
from pathlib import Path
import secrets
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent / 'src'))
from serve_analysis import AnalysisService, MAX_BODY
from waitress import serve


def main():
    origin = os.environ['SHEEP_ALLOWED_ORIGIN'].rstrip('/')
    if not origin.startswith('https://') or '/' in origin[8:]:
        raise SystemExit('SHEEP_ALLOWED_ORIGIN must be an HTTPS origin without path')
    token = os.environ['SHEEP_API_TOKEN']
    if len(token) < 40 or token.strip() != token:
        raise SystemExit('Set SHEEP_API_TOKEN to a long secret, at least 40 characters')
    root = Path(os.environ.get('SHEEP_WORK_ROOT', '/var/data/sheep-analysis')).resolve()
    root.mkdir(parents=True, exist_ok=True, mode=0o700)
    os.chmod(root, 0o700)
    lock_file = (root / 'service.lock').open('a')
    try:
        fcntl.flock(lock_file, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        raise SystemExit('Another service instance uses the same work directory')
    # The service refuses new runs below this much free disk. Its default is 1 GiB, which a
    # 1 GB Render disk can never satisfy; keep the default unless SHEEP_MIN_FREE_BYTES is set.
    min_free = int(os.environ.get('SHEEP_MIN_FREE_BYTES', str(1 << 30)))
    if min_free < 64 * 1024 * 1024:
        raise SystemExit('SHEEP_MIN_FREE_BYTES must be at least 64 MiB')
    service = AnalysisService(root, token, [origin], min_free=min_free)
    port = int(os.environ.get('PORT', '10000'))
    if not 1 <= port <= 65535:
        raise SystemExit('Invalid PORT')
    print('Sheep analysis service listening; restricted origin and bearer authorization enabled', flush=True)
    try:
        serve(service, host='0.0.0.0', port=port, threads=4,
              max_request_body_size=MAX_BODY, max_request_header_size=16384,
              channel_timeout=60, connection_limit=20, expose_tracebacks=False)
    finally:
        service.stop()

if __name__ == '__main__':
    main()
