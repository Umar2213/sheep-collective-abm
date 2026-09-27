# Private reference analysis service

## Purpose and boundary

The website's Reference analysis page calls `src/serve_analysis.py`, which runs
`src/run_analysis.py` in a separate Python process. It uses the same scientific pipeline,
not the separate JavaScript explorer. This supports WP1, WP2, WP6 and WP7. It does not add
behavioural classification, repeatability inference or training-derived social ties.

The code and website connection can be tested without Mserver. Actual Mserver operation,
an institution-approved HTTPS address and data permissions must be established on that
machine. No server address or credentials are supplied by this repository. Do not send
restricted data until the service destination is approved for them.

## Start on the approved machine

Use the Python 3.12 environment and private project location described in
[MSERVER_SETUP.md](MSERVER_SETUP.md). From the repository checkout:

```bash
: "${SHEEP_WORK_ROOT:?Set the approved private project root first}"
python --version
df -h "$SHEEP_WORK_ROOT"
git status --short
git pull --ff-only
python -m pip install -r requirements-service.txt
python -m unittest discover -s tests -v
python src/serve_analysis.py \
  --work-root "$SHEEP_WORK_ROOT/service" \
  --allowed-origin https://sheep-motion-lab.youma6.chatgpt.site
```

If the change is still an open PR, explicitly check out `research/private-analysis-service`
first. Use a clean, fixed commit while the service runs. Stop it before updating code and
restart afterward. The health endpoint records its startup commit; output manifests record
executed source hashes and dirty-tree state. This command runs in the foreground. Arrange
an approved supervisor/service manager with the administrator for persistent operation.
Do not run multiple processes against one work root; a process lock prevents this in the CLI.

The service listens only on `127.0.0.1:8765`. It generates a random access token in
`$SHEEP_WORK_ROOT/service/access-token`, readable only by your account. Read that file on
your own machine and paste the token into the website's password field. Do not paste it
into chat, GitHub, a URL or a shared screenshot. Restart after rotating the token file.
The token authorizes every run in this single-user service. It is not multi-user isolation.

## Connect the hosted website

The administrator must provide an approved HTTPS reverse proxy to the loopback listener,
with a certificate trusted by your browser. Bind it on an institution-approved host and
apply the institution's network policy. This repository does not expose Mserver or create
a public tunnel. A server's SSH login or private hostname alone is not a browser-accessible
HTTPS API. A loopback URL is supported in the client for local testing only; do not assume
that a hosted page can reach an SSH-forwarded loopback service in every browser.

Proxy requirements:

- Preserve `/health` and `/jobs` paths, `Authorization`, `Origin` and `Content-Type`.
- Permit GET, POST, DELETE and OPTIONS. Do not redirect API calls to a login HTML page.
- Use a request-body limit of 26 MB or less, and allow a 120-second upload timeout.
- Do not log Authorization headers or request bodies; disable response caching.
- Terminate HTTPS at the approved proxy. The Python listener stays on loopback.
- If using a URL prefix, strip that prefix before forwarding to the listener.

An administrator-adapted nginx location inside an existing approved TLS server could be:

```nginx
location /sheep-api/ {
    client_max_body_size 26m;
    proxy_pass http://127.0.0.1:8765/;
    proxy_set_header Authorization $http_authorization;
    proxy_set_header Origin $http_origin;
    proxy_read_timeout 120s;
    proxy_send_timeout 120s;
    proxy_no_cache 1;
    proxy_cache_bypass 1;
}
```

This fragment is not a complete TLS or institutional deployment configuration. Do not
modify shared server configuration without its administrator. The application uses
[Waitress](https://docs.pylonsproject.org/projects/waitress/en/latest/arguments.html)
with bounded request bodies and connections; no development HTTP server is used.

In the website, open **Reference analysis**, enter the approved HTTPS base URL and token,
and select **Connect to service**. Check the displayed code commit. Select trajectory CSV,
optional independent ties and optional previously frozen folds. Review the JSON settings,
confirm permission to transfer the data, and run. Settings shown are illustrative, not
validated sensor thresholds. Mark synthetic data as synthetic. The website sends the
request directly from the browser to the chosen service, with the token in an Authorization
header. Tokens and inputs are not saved to browser storage by this feature.

## Results and retention

One analysis runs at a time, with a 30-minute timeout and one numerical-library thread.
Service limits are 20,000 rows per CSV, 8 MB per file, 12 folds, 10,000 bootstrap draws and
five shuffle seeds. Use the CLI for larger datasets instead of breaking biological blocks
just to fit the service limit. A new run requires at least 1 GiB free storage. This is a
filesystem-space check, not a guarantee about user quota or final output size.

Uploads are copied into a fresh private job folder with read-only input files. Original
files on your computer remain unchanged. Results are checksum-verified before being marked
complete and packaged into a ZIP. The ZIP contains prepared trajectories and other sensitive
outputs, so keep it in approved study storage. It does not include the access token. The
viewer checks score consistency; checksum verification does not establish scientific validity.

Runs, uploaded copies and private logs remain until explicitly deleted. At 20 retained runs,
the service rejects new runs. Download and verify your archive before using **Delete service
copy**. That action removes the job's uploads and outputs, not your original source files.
Deletion is not secure erasure and institutional backups follow their own retention policy.
The service refuses to delete running jobs. Restarted incomplete jobs are marked failed;
submit a fresh run instead of reusing partial output. Normal SIGINT/SIGTERM stops the active
analysis subprocess. Abrupt machine/process failure still requires checking for orphan work.

## API contract, version 1

All endpoints except OPTIONS require `Authorization: Bearer <private token>`.
Browser requests require an exact allowed origin. CORS is not a replacement for the token.

| Method/path | Result |
|---|---|
| GET `/health` | Service identity, code commit and limits |
| POST `/jobs` | JSON: `trajectories` CSV text, `config` object, optional `ties` and `folds` CSV text; returns 202 and job ID |
| GET `/jobs` | Retained single-user jobs |
| GET `/jobs/{id}` | Running, succeeded or failed status |
| GET `/jobs/{id}/bundle` | Completed `analysis_bundle.json` |
| GET `/jobs/{id}/archive` | Completed outputs and manifest ZIP |
| GET `/jobs/{id}/log` | Last 32 KB of a completed/failed private log |
| DELETE `/jobs/{id}` | Delete a non-running service copy |

Unknown fields and invalid settings fail before a job starts. Scientific input failures
produce a failed job and private log, not fabricated results. The client never follows API
redirects with the token. Configuration cannot select server filesystem paths or commands.

## Verification

The service regression suite checks authentication, origins, request/configuration limits,
job concurrency, retention/deletion, restart handling and a real subprocess analysis whose
predictions match the direct pipeline on identical serialized inputs. The website tests
its HTTP client and existing numerical utilities. Live Mserver routing and browser access
must be checked separately after server installation.
