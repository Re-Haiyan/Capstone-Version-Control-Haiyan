#!/usr/bin/env bash
# Read-only check. Usage: bash deploy/phase7-readonly-vm-check.sh /absolute/private/staging
set -euo pipefail
if [[ $# -ne 1 ]]; then echo "Usage: $0 /absolute/path/to/phase7-staging" >&2; exit 2; fi
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
CANDIDATE_DIR="$1"
if [[ ! -d "$CANDIDATE_DIR" ]]; then echo "No staging candidate: $CANDIDATE_DIR" >&2; exit 3; fi
PY="$ROOT/backend/.venv/bin/python"
if [[ ! -x "$PY" ]]; then echo "Missing production Python venv: $PY" >&2; exit 3; fi
echo "System resources (read-only)"
free -m || :
df -h "$ROOT" || :
echo "Existing live service (read-only)"
systemctl is-active defaketive || :
"$PY" - "$ROOT" "$CANDIDATE_DIR" <<'PY'
import hashlib,json,pathlib,sys
repo=pathlib.Path(sys.argv[1])
cand=pathlib.Path(sys.argv[2]).resolve()
configured=repo/"backend/sentiment-analysis/models/sentiment_onnx/xlmr_firecs_v1"
hazard=repo/"backend/sentiment-analysis/models/hazard_classifier_v6/manifest.json"
def digest(p):
    h=hashlib.sha256()
    with p.open("rb") as f:
        for b in iter(lambda:f.read(1<<20),b""): h.update(b)
    return h.hexdigest()
def load(p):
    return json.loads(p.read_text())
old=load(configured/"manifest.json")
stage=load(cand/"manifest.json")
h=load(hazard)
print("CONFIGURED PRODUCTION:",old["model_version"])
print("CONFIGURED SHA:",old["files"]["model.onnx"])
print("ACTUAL ON-DISK PROD SHA:",digest(configured/"model.onnx"))
print("HAZARD V6 REQUIRED SENTIMENT SHA:",(h.get("sentiment_model") or {}).get("model_sha256"))
assert old["files"]["model.onnx"] == digest(configured/"model.onnx"),"Live-repository model hash mismatch"
assert old["files"]["model.onnx"] == (h.get("sentiment_model") or {}).get("model_sha256"),"Hazard dependency mismatch"
print("PROPOSED CANDIDATE:",stage["model_version"])
assert stage.get("eligible_for_deployment") is False
assert stage.get("qualified_for_integration") is False
for name,expected in stage["files"].items():
    actual=digest(cand/name)
    if actual!=expected: raise RuntimeError("Staging file hash mismatch: "+name)
assert stage["outputs"]==["logits","hidden_states"]
print("CANDIDATE SHA:",stage["files"]["model.onnx"])
print("CANDIDATE ONNX MB:",round((cand/"model.onnx").stat().st_size/1024**2,1))
print("CANDIDATE INCOMPATIBLE WITH HAZARD V6 SHA GATE:",
      stage["files"]["model.onnx"] != (h.get("sentiment_model") or {}).get("model_sha256"))
mem={}
for line in pathlib.Path("/proc/meminfo").read_text().splitlines():
    if line.startswith(("MemTotal:","MemAvailable:","SwapFree:")):
        k,v=line.split(":",1);mem[k]=round(int(v.strip().split()[0])/1024,1)
print("CURRENT VM MEMORY (MB):",mem)
if mem.get("MemAvailable",0)<(cand/"model.onnx").stat().st_size/1024**2*1.5:
    print("WARNING: insufficient free physical memory for safe side-by-side execution")
print("FINAL DECISION: RESEARCH-ONLY. No live model or service was modified.")
PY
