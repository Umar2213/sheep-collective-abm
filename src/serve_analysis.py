"""Single-user private HTTP adapter for the reference pipeline, behind approved HTTPS.

Scientific calculations remain in run_analysis.py. No browser implementation is used.
"""
from __future__ import annotations
import argparse
import csv
import hmac
import io
import json
import os
from pathlib import Path
import re
import secrets
import shutil
import subprocess
import sys
import threading
import time
import uuid
import zipfile
from http import HTTPStatus

from trajectory_pipeline import AnalysisConfig
from verify_analysis import verify_analysis

SOURCE = Path(__file__).resolve().parent
MAX_BODY = 26_000_000
MAX_FILE = 8_000_000
JOB_ID = re.compile(r"^[a-f0-9]{32}$")


class APIError(Exception):
    def __init__(self, status, message):
        self.status, self.message = status, message


def write_json(path, value):
    temporary = path.with_suffix('.tmp')
    temporary.write_text(json.dumps(value, indent=2, allow_nan=False) + '\n')
    temporary.replace(path)


def validate_request(payload):
    if not isinstance(payload, dict) or set(payload) - {'trajectories', 'config', 'ties', 'folds'}:
        raise ValueError('Supply trajectories, config, and optionally ties and folds.')
    config = payload.get('config')
    if not isinstance(config, dict):
        raise ValueError('config must be a JSON object.')
    options = dict(config)
    for name in ('split_columns', 'uncertainty_columns', 'shuffle_seeds'):
        if name in options:
            if not isinstance(options[name], list):
                raise ValueError(f'{name} must be an array.')
            options[name] = tuple(options[name])
    try:
        settings = AnalysisConfig(**options)
        settings.validate()
    except TypeError as error:
        raise ValueError('Invalid configuration field or type.') from error
    if settings.data_kind not in ('synthetic', 'observational'):
        raise ValueError('Explicitly declare synthetic or observational data.')
    if settings.n_folds > 12 or settings.n_bootstrap > 10000 or len(settings.shuffle_seeds) > 5:
        raise ValueError('Service limits: 12 folds, 10000 bootstrap draws and 5 shuffle seeds. Use the CLI for larger runs.')
    files = {}
    for name in ('trajectories', 'ties', 'folds'):
        value = payload.get(name)
        if value is None and name != 'trajectories':
            continue
        if not isinstance(value, str) or not value.strip() or len(value.encode('utf-8')) > MAX_FILE:
            raise ValueError(f'{name} must be nonempty CSV text, at most 8 MB.')
        reader = csv.reader(io.StringIO(value))
        header = next(reader, [])
        if not header or len(set(header)) != len(header) or any(not h.strip() for h in header):
            raise ValueError(f'{name} requires unique, nonempty column names.')
        if sum(1 for _ in reader) > 20000:
            raise ValueError(f'{name} exceeds 20000 rows; use the CLI for larger studies.')
        files[name] = value
    if 'ties' in files and not settings.ties_independent:
        raise ValueError('Social ties require a true independence declaration in config.')
    return files, config


class AnalysisService:
    def __init__(self, root, token, origins, *, timeout=1800, max_jobs=20, min_free=1 << 30):
        self.root = Path(root).resolve()
        if self.root == SOURCE.parent or SOURCE.parent in self.root.parents:
            raise ValueError('Service data must be outside the public repository.')
        if len(token) < 32:
            raise ValueError('Use an access token of at least 32 characters.')
        self.root.mkdir(parents=True, exist_ok=True, mode=0o700)
        self.root.chmod(0o700)
        self.token, self.origins = token, set(origins)
        self.timeout, self.max_jobs, self.min_free = timeout, max_jobs, min_free
        self.lock = threading.RLock()
        self.jobs = {}
        self.active = None
        self.process = None
        self.stopping = False
        for path in self.root.glob('*/status.json'):
            if not JOB_ID.fullmatch(path.parent.name):
                continue
            record = json.loads(path.read_text())
            if record['status'] == 'running':
                record.update(status='failed', message='Service restarted before completion. Submit a new run.')
                write_json(path, record)
            self.jobs[path.parent.name] = record
        try:
            self.commit = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=SOURCE, text=True).strip()
        except (OSError, subprocess.CalledProcessError):
            self.commit = None

    def status(self, job):
        if not JOB_ID.fullmatch(job) or job not in self.jobs:
            raise APIError(404, 'Unknown job.')
        return dict(self.jobs[job])

    def submit(self, payload):
        files, config = validate_request(payload)
        with self.lock:
            if self.stopping:
                raise APIError(503, 'Service is stopping.')
            if self.active:
                raise APIError(409, 'One analysis is already running. Wait for it to finish.')
            if len(self.jobs) >= self.max_jobs:
                raise APIError(409, 'Retention limit reached. Download and delete an old service copy first.')
            if shutil.disk_usage(self.root).free < self.min_free:
                raise APIError(507, 'Insufficient free storage for a new analysis.')
            job = uuid.uuid4().hex
            folder = self.root / job
            folder.mkdir(mode=0o700)
            inputs = folder / 'inputs'
            inputs.mkdir(mode=0o700)
            try:
                for name, text in files.items():
                    path = inputs / f'{name}.csv'
                    path.write_text(text, encoding='utf-8')
                    path.chmod(0o400)
                path = inputs / 'config.json'
                path.write_text(json.dumps(config, allow_nan=False), encoding='utf-8')
                path.chmod(0o400)
                record = dict(id=job, status='running', created_at=time.time(), message='Running the reference Python pipeline.')
                self.jobs[job] = record
                self.active = job
                write_json(folder / 'status.json', record)
                threading.Thread(target=self.run, args=(job, files), daemon=True).start()
            except BaseException:
                self.jobs.pop(job, None)
                self.active = None
                shutil.rmtree(folder)
                raise
            return dict(record)

    def run(self, job, files):
        folder = self.root / job
        inputs = folder / 'inputs'
        command = [sys.executable, str(SOURCE / 'run_analysis.py'), str(inputs / 'trajectories.csv'),
                   '--config', str(inputs / 'config.json'), '--output', str(folder / 'outputs')]
        for name in ('ties', 'folds'):
            if name in files:
                command += [f'--{name}', str(inputs / f'{name}.csv')]
        status, message = 'failed', 'Analysis failed. Inspect the private run log, correct inputs and submit a new run.'
        try:
            env = dict(os.environ, OMP_NUM_THREADS='1', OPENBLAS_NUM_THREADS='1', MKL_NUM_THREADS='1', MPLBACKEND='Agg')
            with (folder / 'run.log').open('w') as log:
                with self.lock:
                    if self.stopping:
                        raise RuntimeError('Service is stopping.')
                    self.process = subprocess.Popen(command, stdout=log, stderr=subprocess.STDOUT, cwd=SOURCE.parent, env=env)
                    process = self.process
                try:
                    code = process.wait(timeout=self.timeout)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait()
                    raise
            if code == 0:
                verify_analysis(folder / 'outputs')
                with zipfile.ZipFile(folder / 'results.zip', 'x', compression=zipfile.ZIP_DEFLATED) as archive:
                    for path in sorted((folder / 'outputs').iterdir()):
                        archive.write(path, arcname=path.name)
                status, message = 'succeeded', 'Analysis complete; output checksums verified. Scientific interpretation still requires study review.'
        except subprocess.TimeoutExpired:
            message = 'Analysis exceeded the service time limit. Use the command-line workflow for a larger run.'
        except Exception:
            message = 'Analysis or output verification failed. Inspect the private run log.'
        finally:
            with self.lock:
                self.jobs[job].update(status=status, message=message, finished_at=time.time())
                write_json(folder / 'status.json', self.jobs[job])
                self.active = None
                self.process = None

    def stop(self):
        with self.lock:
            self.stopping = True
            process = self.process
        if process and process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()

    def __call__(self, env, start_response):
        origin = env.get('HTTP_ORIGIN')
        headers = [('Cache-Control', 'no-store'), ('X-Content-Type-Options', 'nosniff'), ('Vary', 'Origin')]
        if origin in self.origins:
            headers += [('Access-Control-Allow-Origin', origin), ('Access-Control-Allow-Methods', 'GET, POST, DELETE, OPTIONS'),
                        ('Access-Control-Allow-Headers', 'Authorization, Content-Type')]
        def respond(code, value, content_type='application/json'):
            body = value if isinstance(value, bytes) else json.dumps(value, allow_nan=False).encode()
            start_response(f'{code} {HTTPStatus(code).phrase}', headers + [('Content-Type', content_type), ('Content-Length', str(len(body)))])
            return [body]
        try:
            if origin and origin not in self.origins:
                raise APIError(403, 'This website origin is not allowed.')
            method, path = env['REQUEST_METHOD'], env.get('PATH_INFO', '')
            if method == 'OPTIONS':
                return respond(200, {'ok': True})
            if not hmac.compare_digest(env.get('HTTP_AUTHORIZATION', ''), 'Bearer ' + self.token):
                raise APIError(401, 'An access token is required.')
            if method == 'GET' and path == '/health':
                return respond(200, dict(service='sheep-reference-analysis', api_version=1, source_commit=self.commit,
                                         max_rows=20000, max_file_bytes=MAX_FILE, max_jobs=self.max_jobs, active_job=self.active))
            if method == 'POST' and path == '/jobs':
                if env.get('CONTENT_TYPE', '').split(';')[0] != 'application/json':
                    raise APIError(415, 'Send JSON.')
                size = int(env.get('CONTENT_LENGTH') or 0)
                if not 0 < size <= MAX_BODY:
                    raise APIError(413, 'Request exceeds 26 MB or has no content length.')
                raw = env['wsgi.input'].read(size)
                if len(raw) != size:
                    raise ValueError('Incomplete request body.')
                return respond(202, self.submit(json.loads(raw)))
            if method == 'GET' and path == '/jobs':
                with self.lock:
                    return respond(200, {'jobs': [dict(r) for r in self.jobs.values()]})
            match = re.fullmatch(r'/jobs/([a-f0-9]{32})(?:/(bundle|archive|log))?', path)
            if not match:
                raise APIError(404, 'Unknown endpoint.')
            job, resource = match.groups()
            with self.lock:
                record = self.status(job)
                folder = self.root / job
                if method == 'DELETE' and resource is None:
                    if record['status'] == 'running':
                        raise APIError(409, 'Cannot delete a running analysis.')
                    shutil.rmtree(folder)
                    del self.jobs[job]
                    return respond(200, {'deleted': job})
                if method != 'GET':
                    raise APIError(405, 'Method not allowed.')
                if resource is None:
                    return respond(200, record)
                if record['status'] == 'running':
                    raise APIError(409, 'Analysis is still running.')
                if resource == 'log':
                    return respond(200, (folder / 'run.log').read_bytes()[-32000:], 'text/plain; charset=utf-8')
                if record['status'] != 'succeeded':
                    raise APIError(409, 'No completed results are available.')
                if resource == 'bundle':
                    return respond(200, (folder / 'outputs' / 'analysis_bundle.json').read_bytes())
                file = (folder / 'results.zip').open('rb')
                size = os.fstat(file.fileno()).st_size
                start_response('200 OK', headers + [('Content-Type', 'application/zip'), ('Content-Length', str(size)),
                                                      ('Content-Disposition', 'attachment; filename="analysis-results.zip"')])
                def chunks():
                    with file:
                        while block := file.read(65536):
                            yield block
                return chunks()
        except APIError as error:
            return respond(error.status, {'error': error.message})
        except (ValueError, TypeError, UnicodeError, csv.Error) as error:
            return respond(400, {'error': str(error)[:500]})
        except Exception:
            return respond(500, {'error': 'Service error. Check the private server storage and log.'})


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--work-root', type=Path, required=True)
    parser.add_argument('--allowed-origin', action='append', required=True)
    parser.add_argument('--port', type=int, default=8765)
    args = parser.parse_args()
    from urllib.parse import urlsplit
    for origin in args.allowed_origin:
        url = urlsplit(origin)
        if url.scheme not in ('https', 'http') or not url.netloc or url.path or url.query or url.fragment or url.username:
            parser.error('Provide exact website origins without trailing slashes, paths or credentials.')
        if url.scheme == 'http' and url.hostname not in ('localhost', '127.0.0.1'):
            parser.error('Non-local website origins require HTTPS.')
    root = args.work_root.resolve()
    if root == SOURCE.parent or SOURCE.parent in root.parents:
        parser.error('Keep private service storage outside the repository.')
    os.umask(0o077)
    root.mkdir(parents=True, exist_ok=True, mode=0o700)
    import fcntl
    lock = (root / 'service.lock').open('a')
    try:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        parser.error('Another service is using this work root.')
    token_path = root / 'access-token'
    if not token_path.exists():
        with token_path.open('x') as stream:
            stream.write(secrets.token_urlsafe(48) + '\n')
    token_path.chmod(0o600)
    app = AnalysisService(root, token_path.read_text().strip(), args.allowed_origin)
    print(f'Private token file: {token_path}', flush=True)
    print(f'Listening on 127.0.0.1:{args.port}. Use an approved HTTPS reverse proxy for the hosted website.', flush=True)
    import signal
    def stop(signum, frame):
        app.stop()
        raise SystemExit(0)
    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)
    from waitress import serve
    serve(app, host='127.0.0.1', port=args.port, threads=4, max_request_body_size=MAX_BODY,
          max_request_header_size=16384, channel_timeout=60, connection_limit=20, expose_tracebacks=False)


if __name__ == '__main__':
    main()
