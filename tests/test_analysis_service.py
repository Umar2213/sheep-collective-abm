import io
import json
from pathlib import Path
import sys
import tempfile
import time
import unittest
from unittest.mock import patch
import zipfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from serve_analysis import AnalysisService, validate_request, MAX_BODY, SOURCE
from generate_demo import generate
from trajectory_pipeline import AnalysisConfig, run_pipeline, read_table

TOKEN = 'test-token-not-a-real-credential-' + 'x' * 32
ORIGIN = 'https://example.test'


def request(app, method='GET', path='/health', payload=None, token=TOKEN, origin=ORIGIN, **extra):
    body = json.dumps(payload).encode() if payload is not None else b''
    env = {'REQUEST_METHOD': method, 'PATH_INFO': path, 'HTTP_AUTHORIZATION': 'Bearer ' + token,
           'HTTP_ORIGIN': origin, 'CONTENT_TYPE': 'application/json', 'CONTENT_LENGTH': str(len(body)),
           'wsgi.input': io.BytesIO(body), **extra}
    response = {}
    def start(status, headers):
        response.update(status=int(status.split()[0]), headers=dict(headers))
    iterator = app(env, start)
    response['body'] = b''.join(iterator)
    if response['headers']['Content-Type'] == 'application/json':
        response['json'] = json.loads(response['body'])
    return response


class ServiceTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.app = AnalysisService(self.tmp.name, TOKEN, [ORIGIN], min_free=0)
        self.data, self.ties, _ = generate(groups=2, sessions=2, animals=3, steps=12)
        self.config = dict(data_kind='synthetic', n_folds=2, n_bootstrap=100, shuffle_seeds=[], ties_independent=True)
        self.payload = dict(trajectories=self.data.to_csv(index=False), ties=self.ties.to_csv(index=False), config=self.config)

    def test_auth_origin_preflight_and_path_boundaries(self):
        self.assertEqual(request(self.app, token='wrong')['status'], 401)
        self.assertEqual(request(self.app, origin='https://untrusted.test')['status'], 403)
        response = request(self.app, 'OPTIONS', token='')
        self.assertEqual(response['status'], 200)
        self.assertEqual(response['headers']['Access-Control-Allow-Origin'], ORIGIN)
        self.assertEqual(request(self.app, path='/jobs/../../access-token')['status'], 404)
        self.assertEqual(request(self.app, path='/health')['json']['api_version'], 1)
        self.assertEqual(request(self.app, 'POST', '/jobs', CONTENT_LENGTH=str(MAX_BODY + 1))['status'], 413)
        self.assertEqual(request(self.app, 'POST', '/jobs', self.payload, CONTENT_TYPE='text/plain')['status'], 415)

    def test_bad_config_and_inputs_fail_before_creating_jobs(self):
        for config in (dict(self.config, ties_independent='true'), dict(self.config, n_folds=13),
                       dict(self.config, output='/tmp/not-allowed'), dict(self.config, split_columns='group_id')):
            response = request(self.app, 'POST', '/jobs', dict(self.payload, config=config))
            self.assertEqual(response['status'], 400)
        response = request(self.app, 'POST', '/jobs', dict(self.payload, trajectories='x,x\n1,2'))
        self.assertEqual(response['status'], 400)
        self.assertEqual(self.app.jobs, {})

    def test_concurrency_delete_and_storage_guards(self):
        with patch('serve_analysis.threading.Thread.start'):
            created = request(self.app, 'POST', '/jobs', self.payload)
        job = created['json']['id']
        self.assertEqual(created['status'], 202)
        self.assertEqual(request(self.app, 'POST', '/jobs', self.payload)['status'], 409)
        self.assertEqual(request(self.app, 'DELETE', '/jobs/' + job)['status'], 409)
        self.assertEqual(request(self.app, path='/jobs/' + job + '/archive')['status'], 409)
        self.app.jobs[job]['status'] = 'failed'
        self.app.active = None
        self.app.max_jobs = 1
        self.assertEqual(request(self.app, 'POST', '/jobs', self.payload)['status'], 409)
        self.assertEqual(request(self.app, 'DELETE', '/jobs/' + job)['status'], 200)
        self.assertFalse((Path(self.tmp.name) / job).exists())
        self.app.min_free = 10 ** 30
        self.assertEqual(request(self.app, 'POST', '/jobs', self.payload)['status'], 507)
        with self.assertRaisesRegex(ValueError, 'outside'):
            AnalysisService(SOURCE.parent / 'private-api-test', TOKEN, [ORIGIN])

    def test_restart_marks_interrupted_jobs_failed_and_preserves_inputs(self):
        with patch('serve_analysis.threading.Thread.start'):
            job = self.app.submit(self.payload)['id']
        restored = AnalysisService(self.tmp.name, TOKEN, [ORIGIN], min_free=0)
        self.assertEqual(restored.status(job)['status'], 'failed')
        self.assertEqual((Path(self.tmp.name)/job/'inputs'/'trajectories.csv').read_text(), self.payload['trajectories'])

    def test_real_subprocess_matches_reference_pipeline_and_downloads_verified_archive(self):
        response = request(self.app, 'POST', '/jobs', self.payload)
        self.assertEqual(response['status'], 202)
        job = response['json']['id']
        deadline = time.monotonic() + 60
        while self.app.status(job)['status'] == 'running' and time.monotonic() < deadline:
            time.sleep(.05)
        self.assertEqual(self.app.status(job)['status'], 'succeeded', (Path(self.tmp.name)/job/'run.log').read_text())
        bundle = request(self.app, path=f'/jobs/{job}/bundle')['json']
        inputs = Path(self.tmp.name)/job/'inputs'
        expected = run_pipeline(read_table(inputs/'trajectories.csv'), AnalysisConfig(**self.config), read_table(inputs/'ties.csv'))
        self.assertEqual(bundle['audit']['eligible_transitions'], len(expected['features']))
        self.assertEqual((Path(self.tmp.name)/job/'outputs'/'predictions.csv').read_text(), expected['predictions'].to_csv(index=False))
        downloaded = request(self.app, path=f'/jobs/{job}/archive')
        self.assertEqual(downloaded['status'], 200)
        with zipfile.ZipFile(io.BytesIO(downloaded['body'])) as archive:
            self.assertIn('manifest.json', archive.namelist())
            self.assertIn('prepared.csv', archive.namelist())
            self.assertNotIn('access-token', archive.namelist())
            self.assertNotIn('inputs/trajectories.csv', archive.namelist())
        self.assertEqual(request(self.app, path=f'/jobs/{job}/log')['status'], 200)
