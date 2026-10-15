#!/usr/bin/env bash
# Assemble the website upload folder: page, headers and the in-browser analysis engine.
# Usage: bash website/build_engine.sh OUTPUT_DIR
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
OUT="${1:?Give an output folder, for example /tmp/site}"
VER=0.28.3
[ -e "$OUT" ] && { echo "Output exists; choose a new folder"; exit 1; }
mkdir -p "$OUT/engine/pyodide" "$OUT/engine/src"
cp "$ROOT/website/index.html" "$ROOT/website/_headers" "$OUT/"
cp "$ROOT/website/engine/worker.js" "$ROOT/website/engine/packages.json" "$ROOT/website/engine/THIRD_PARTY.md" "$OUT/engine/"
cp "$ROOT"/src/*.py "$OUT/engine/src/"
git -C "$ROOT" rev-parse HEAD > "$OUT/engine/SOURCE_COMMIT"
TMP="$(mktemp -d)"; trap 'rm -rf "$TMP"' EXIT
echo "Downloading Pyodide $VER (about 350 MB, once)..."
curl -fL --retry 3 -o "$TMP/pyodide.tar.bz2" "https://github.com/pyodide/pyodide/releases/download/$VER/pyodide-$VER.tar.bz2"
tar -xjf "$TMP/pyodide.tar.bz2" -C "$TMP"
python3 - "$TMP/pyodide" "$OUT/engine" <<'PY'
import json, shutil, sys, os
src, eng = sys.argv[1], sys.argv[2]
for name in ("pyodide.js", "pyodide.mjs", "pyodide.asm.js", "pyodide.asm.wasm", "python_stdlib.zip", "pyodide-lock.json", "package.json"):
    shutil.copy(os.path.join(src, name), os.path.join(eng, "pyodide", name))
lock = json.load(open(os.path.join(src, "pyodide-lock.json")))["packages"]
for name in json.load(open(os.path.join(eng, "packages.json"))):
    shutil.copy(os.path.join(src, lock[name]["file_name"]), os.path.join(eng, "pyodide"))
files = sorted(f for f in os.listdir(os.path.join(eng, "src")) if f.endswith(".py"))
json.dump(files, open(os.path.join(eng, "src", "files.json"), "w"))
print(f"Engine ready: {len(files)} source files")
PY
echo "Done. Upload the contents of $OUT"
