#!/usr/bin/env bash
# Start the sheep analysis service on a Linux server (Mserver now; the Adelaide server later).
# The same script works on any server: only the server address used by the website changes.
#
# One-time setup on the server:
#   conda create -y -n sheep python=3.12 && conda activate sheep
#   git clone https://github.com/Umar2213/sheep-collective-abm.git ~/sheep-collective-abm
#   pip install -r ~/sheep-collective-abm/requirements-service.txt
#
# Every time (inside tmux or screen, so it keeps running after you log out):
#   conda activate sheep && bash start_service_on_server.sh
set -euo pipefail
REPO="${REPO:-$HOME/sheep-collective-abm}"     # the repository checkout
WORK="${WORK:-$HOME/sheep-service}"            # private job folder; must be outside the repository
PORT="${PORT:-8765}"                           # change if another user already uses 8765
ONLINE="${ONLINE:-https://raspy-sun-25b9.umaraziz.workers.dev}"
[ -f "$REPO/src/serve_analysis.py" ] || { echo "Repository not found at $REPO (set REPO=...)"; exit 1; }
python -c 'import sys; assert sys.version_info >= (3, 11), "Activate the Python 3.12 environment first (conda activate sheep)"'
python -c 'import waitress, numpy, pandas, scipy, matplotlib' || { echo "Run: pip install -r $REPO/requirements-service.txt"; exit 1; }
if (exec 3<>/dev/tcp/127.0.0.1/"$PORT") 2>/dev/null; then echo "Port $PORT is already in use. Start with PORT=8766 bash $0"; exit 1; fi
echo "Server: $(hostname)   code commit: $(git -C "$REPO" rev-parse --short HEAD 2>/dev/null || echo unknown)"
echo "Free space for jobs: $(df -h "$(dirname "$WORK")" | awk 'NR==2{print $4}')"
( sleep 3
  echo
  echo "Token (paste into 'Access token'; never show it on screen): $(cat "$WORK/access-token")"
  echo
  echo "On your own computer, open a terminal and run (keep it open):"
  echo "  ssh -N -L $PORT:127.0.0.1:$PORT $(whoami)@$(hostname -I 2>/dev/null | awk '{print $1}')"
  echo "Then open in Chrome:"
  echo "  $ONLINE/?api=http://127.0.0.1:$PORT"
  echo
  echo "Leave this running. In tmux press Ctrl+B then D to detach. Ctrl+C stops the service." ) &
cd "$REPO"
exec python src/serve_analysis.py --work-root "$WORK" --port "$PORT" \
  --allowed-origin "$ONLINE" --allowed-origin http://localhost:8000
