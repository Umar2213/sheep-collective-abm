# Website

`index.html` is the published page (Cloudflare Worker `raspy-sun-25b9`, static assets) and
`_headers` its security headers. `engine/` holds the in-browser analysis engine:

- `engine/worker.js` loads Pyodide, writes the unchanged `src/*.py` files, applies
  `serve_analysis.validate_request`, runs `run_analysis.py` and checks the outputs with
  `verify_analysis.verify_analysis`. It only adds progress messages.
- `engine/packages.json` lists the Pyodide packages needed (numpy, pandas, scipy, matplotlib
  and their dependencies).

The Pyodide runtime (about 45 MB) is not committed. Build the complete upload folder with:

```bash
bash website/build_engine.sh /tmp/site     # then upload the contents of /tmp/site
```

The script copies `src/*.py`, records the Git commit, and extracts the needed files from the
Pyodide 0.28.3 release (MPL-2.0). Upload the folder's contents with "New deployment" in the
Cloudflare dashboard, or run `npx wrangler deploy` with `assets.directory` pointing to it.
