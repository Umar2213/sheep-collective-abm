# Mserver setup for empirical work

Use a separate Python 3.12 environment. The repository's Python dependencies are not intended
for Ubuntu 20.04's system Python. No root privileges or OS upgrade are needed for these steps.
Server OS/security maintenance belongs with its administrator. This guide does not log in,
change system packages or verify live storage quotas.

First inspect current capacity and tools (the pasted login banner is only a past snapshot):

```bash
hostname
pwd
df -h /home /issd /data
quota -s 2>/dev/null || true
command -v conda
command -v git
```

Ask the server administrator which project directory is allocated, backed up and authorized
for these data. Free filesystem space is not your personal quota. Do not use a mount root
or somebody else's directory. Set a private path interactively without recording it in Git:

```bash
read -r -p 'Approved private project directory: ' SHEEP_WORK_ROOT
export SHEEP_WORK_ROOT
umask 077
mkdir -p "$SHEEP_WORK_ROOT"/{code,raw,interim,processed,results,tmp,metadata,envs}
export TMPDIR="$SHEEP_WORK_ROOT/tmp"
export CONDA_PKGS_DIRS="$SHEEP_WORK_ROOT/envs/pkgs"
conda create --prefix "$SHEEP_WORK_ROOT/envs/python312" python=3.12 pip -y
conda activate "$SHEEP_WORK_ROOT/envs/python312"
git clone https://github.com/Umar2213/sheep-collective-abm.git "$SHEEP_WORK_ROOT/code/sheep-collective-abm"
cd "$SHEEP_WORK_ROOT/code/sheep-collective-abm"
python -m pip install -r requirements.txt
python -m unittest discover -s tests -v
```

For a branch under review, explicitly check out its branch or recorded commit before testing.
Do not assume an open pull request is already on the default branch. For future runs, reuse
this environment and checkout instead of repeating clone/create commands.

Run a small synthetic end-to-end check before empirical analysis:

```bash
RUN_ROOT=$(mktemp -d "$SHEEP_WORK_ROOT/results/software-check.XXXXXX")
export RUN_ROOT
python src/generate_demo.py --output "$RUN_ROOT/input"
python src/audit_trajectories.py "$RUN_ROOT/input/trajectories.csv" --output "$RUN_ROOT/raw-audit.json"
python src/run_analysis.py "$RUN_ROOT/input/trajectories.csv" --config "$RUN_ROOT/input/config.json" --ties "$RUN_ROOT/input/ties.csv" --output "$RUN_ROOT/analysis"
python src/verify_analysis.py "$RUN_ROOT/analysis"
python -m pip freeze > "$RUN_ROOT/pip-freeze.txt"
git rev-parse HEAD > "$RUN_ROOT/code-commit.txt"
```

The generated input is synthetic. Keep real raw exports under the approved raw-data policy;
do not copy them into this public Git checkout. Copy the study inventory template into private
metadata storage and complete it before choosing analysis thresholds or claiming validation.

Julia 1.10.5 is needed only for simulation and Julia tests. If available as an approved module
or user installation, activate it and instantiate the committed Project/Manifest:

```bash
julia --version
julia --project=. -e 'using Pkg; Pkg.instantiate()'
julia --project=. tests/runtests.jl
julia --project=. tests/trait_distributions.jl
ABM_SMOKE=1 ABM_OUTPUT_DIR="$RUN_ROOT/production-smoke" julia --project=. --threads=2 src/production_sweep.jl
```

Use allocated cores, not `--threads=auto` on a shared server. Before full simulation grids,
confirm scheduler rules, storage, expected output size and wall time, then benchmark. See
`EXPERIMENT_PROTOCOL.md`. Every campaign/shard needs a fresh output directory; failed partial
runs must be retained or explicitly archived, never reused as complete results.
