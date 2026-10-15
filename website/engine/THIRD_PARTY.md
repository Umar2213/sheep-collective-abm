# In-browser analysis engine: contents and licences

- `src/`: the unchanged Python source of github.com/Umar2213/sheep-collective-abm at commit
  666a36d3f11d15ef240a87b0fd2ed9e912725378 (MIT licence). Only the `.py` files of `src/` are included.
- `pyodide/`: Pyodide 0.28.3 (CPython 3.13 compiled to WebAssembly), Mozilla Public License 2.0,
  from github.com/pyodide/pyodide/releases/tag/0.28.3, with these package builds from the same release:
  numpy 2.2.5, pandas 2.3.1, scipy 1.14.1, matplotlib 3.8.4 (and their dependencies contourpy,
  cycler, fonttools, kiwisolver, libopenblas, packaging, pillow, pyparsing, python-dateutil, pytz, six).
  Each package keeps its own open-source licence, recorded inside its wheel.
- `worker.js`: runs `run_analysis.py` with the analysis service's own request checks
  (`serve_analysis.validate_request`) and output check (`verify_analysis.verify_analysis`).
  It only adds progress messages; every wrapped function is called unchanged.
