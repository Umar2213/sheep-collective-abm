// Sheep Motion Lab in-browser analysis engine.
// Runs the repository's unchanged Python pipeline (engine/src, commit in SOURCE_COMMIT) in
// Pyodide (CPython compiled to WebAssembly), in this browser tab. No data leaves the computer.
// The request checks are the service's own validate_request, and outputs are checked with
// verify_analysis, exactly as the server does.
/* global importScripts, loadPyodide */
importScripts('pyodide/pyodide.js');

let py = null;
let ready = null;
const send = (msg, transfer) => self.postMessage(msg, transfer || []);

const DRIVER = String.raw`
import io, json, sys, time, uuid, zipfile
from pathlib import Path
sys.path.insert(0, '/app/src')
import trajectory_pipeline as tp
import run_analysis
import serve_analysis
from verify_analysis import verify_analysis

_original = {}

def _wrap(module, name, wrapper):
    if (module.__name__, name) not in _original:
        _original[(module.__name__, name)] = getattr(module, name)
    setattr(module, name, wrapper(_original[(module.__name__, name)]))

def run_job(payload_json, report):
    payload = json.loads(payload_json)
    # Same request checks and limits as the analysis service.
    files, config = serve_analysis.validate_request(payload)
    job = Path('/jobs') / uuid.uuid4().hex
    inputs = job / 'inputs'
    inputs.mkdir(parents=True)
    for name, text in files.items():
        (inputs / f'{name}.csv').write_text(text, encoding='utf-8')
    (inputs / 'config.json').write_text(json.dumps(config, allow_nan=False), encoding='utf-8')

    state = {'fits': 0, 'total': 1}
    # Progress reporting only: each wrapper calls the original function unchanged.
    def stage(label, share):
        def wrapper(fn):
            def inner(*a, **k):
                report(label, share)
                return fn(*a, **k)
            return inner
        return wrapper
    def fit_predict_wrapper(fn):
        def inner(features, folds, config, has_ties=False):
            f = features.merge(folds, on=list(config.split_columns), how='left')
            n_defs, n_ind = 3, 1
            if has_ties:
                n_defs += 2 + len(config.shuffle_seeds); n_ind += 1 + len(config.shuffle_seeds)
                if config.common_shuffle_controls:
                    n_defs += len(config.shuffle_seeds)
            total = 0
            for fold in range(config.n_folds):
                animals = f[f.fold == fold][['group_id', 'individual_id']].drop_duplicates().shape[0]
                total += n_defs + n_ind * animals
            state['fits'], state['total'] = 0, max(total, 1)
            report('Fitting the models on each held-out trial', 0.25)
            return fn(features, folds, config, has_ties)
        return inner
    def fit_wrapper(fn):
        def inner(*a, **k):
            state['fits'] += 1
            if state['fits'] % 5 == 0:
                report('Fitting the models on each held-out trial', 0.25 + 0.6 * min(state['fits'] / state['total'], 1))
            return fn(*a, **k)
        return inner
    _wrap(tp, 'prepare_trajectories', stage('Checking and preparing the trajectories', 0.03))
    _wrap(tp, 'construct_features', stage('Finding neighbours for every sheep and second', 0.08))
    _wrap(tp, 'fit_predict', fit_predict_wrapper)
    _wrap(tp, '_fit', fit_wrapper)
    _wrap(tp, 'evaluate', stage('Scoring predictions and bootstrapping uncertainty', 0.86))
    _wrap(run_analysis, 'figures', stage('Writing figures, report and fingerprints', 0.93))

    argv = ['run_analysis.py', str(inputs / 'trajectories.csv'), '--config', str(inputs / 'config.json'),
            '--output', str(job / 'outputs')]
    for name in ('ties', 'folds'):
        if name in files:
            argv += [f'--{name}', str(inputs / f'{name}.csv')]
    started = time.time()
    sys.argv = argv
    run_analysis.main()
    report('Verifying every output file', 0.98)
    check = verify_analysis(job / 'outputs')
    out = job / 'outputs'
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, 'w', compression=zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(out.iterdir()):
            archive.write(path, arcname=path.name)
    manifest = json.loads((out / 'manifest.json').read_text())
    return json.dumps({'bundle': (out / 'analysis_bundle.json').read_text(), 'verified': check,
                       'seconds': round(time.time() - started, 1), 'packages': manifest.get('packages'),
                       'python': manifest.get('python')}), buffer.getvalue()
`;

async function init() {
  const base = new URL('./', self.location).href;
  send({ type: 'progress', label: 'Loading Python (about 45 MB, once per visit)', share: 0.02 });
  py = await loadPyodide({ indexURL: base + 'pyodide/' });
  const packages = await (await fetch(base + 'packages.json')).json();
  send({ type: 'progress', label: 'Loading numpy, pandas, scipy and matplotlib', share: 0.4 });
  await py.loadPackage(packages);
  const files = await (await fetch(base + 'src/files.json')).json();
  py.FS.mkdirTree('/app/src');
  for (const name of files) {
    const bytes = new Uint8Array(await (await fetch(base + 'src/' + name)).arrayBuffer());
    py.FS.writeFile('/app/src/' + name, bytes);   // exact bytes, so source hashes match the repository
  }
  py.FS.mkdirTree('/jobs');
  send({ type: 'progress', label: 'Starting the analysis code', share: 0.9 });
  await py.runPythonAsync(DRIVER);
  const commit = (await (await fetch(base + 'SOURCE_COMMIT')).text()).trim();
  const versions = py.runPython("import json, run_analysis, platform; json.dumps({'python': platform.python_version(), **run_analysis.package_versions()})");
  return { commit, versions: JSON.parse(versions) };
}

self.onmessage = async (event) => {
  const msg = event.data;
  try {
    if (msg.type === 'init') {
      if (!ready) ready = init();
      const info = await ready;
      send({ type: 'ready', ...info });
    } else if (msg.type === 'run') {
      if (!ready) ready = init();
      await ready;
      const report = (label, share) => send({ type: 'progress', label, share });
      const runJob = py.globals.get('run_job');
      const result = runJob(JSON.stringify(msg.payload), report);
      const [text, zipProxy] = result.toJs();
      const zipBytes = zipProxy.toJs ? zipProxy.toJs() : zipProxy;
      const zip = new Uint8Array(zipBytes);
      result.destroy(); runJob.destroy();
      send({ type: 'done', result: JSON.parse(text), zip: zip.buffer }, [zip.buffer]);
    }
  } catch (err) {
    const text = String(err && err.message ? err.message : err);
    // Python errors end with the exception line; show that line, keep the rest for the log.
    const lines = text.trim().split('\n');
    send({ type: 'error', message: lines[lines.length - 1], detail: text });
  }
};
