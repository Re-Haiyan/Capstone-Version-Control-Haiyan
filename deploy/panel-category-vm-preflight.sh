#!/usr/bin/env bash
# Guarded, read-only preflight for panel category pc6. Run on Azure VM via
# an authenticated operator terminal. NEVER deploys, changes branches,
# restarts a service, or edits SQLite. Requires an isolated candidate checkout.
set -euo pipefail

MODE="${1:-}"
if [[ "$MODE" != "--check" && "$MODE" != "--paired" ]]; then
  echo "Usage: EXPECTED_VM_SHA=<full-40-hex> CANDIDATE_SHA=<full-40-hex> DEFAKETIVE_CANDIDATE=<absolute-path> $0 --check|--paired" >&2
  exit 2
fi
REPO="${DEFAKETIVE_REPO:-$HOME/defaketive}"
CANDIDATE="${DEFAKETIVE_CANDIDATE:-}"
SITE="${DEFAKETIVE_SITE:-https://defaketive.duckdns.org}"
MAX_REVIEWS="${DEFAKETIVE_AUDIT_REVIEWS:-900}"
DB="${DEFAKETIVE_DB:-$REPO/backend/defaketive.db}"
SERVICE="${DEFAKETIVE_SERVICE:-defaketive}"
OLD_SHA="${EXPECTED_VM_SHA:-}"
CANDIDATE_SHA="${CANDIDATE_SHA:-}"
[[ "$OLD_SHA" =~ ^[0-9a-f]{40}$ && "$CANDIDATE_SHA" =~ ^[0-9a-f]{40}$ ]] || {
  echo "Both full expected commit SHAs are mandatory. Never guess the running VM SHA." >&2
  exit 2
}
[[ -d "$REPO/.git" && -d "$CANDIDATE" && "$REPO" != "$CANDIDATE" ]] || {
  echo "Need distinct live and candidate Git checkouts" >&2
  exit 1
}
[[ "$(cd "$REPO" && git rev-parse HEAD)" == "$OLD_SHA" ]] || {
  echo "VM HEAD differs from approved EXPECTED_VM_SHA: NO-GO" >&2
  exit 1
}
[[ "$(cd "$CANDIDATE" && git rev-parse HEAD)" == "$CANDIDATE_SHA" ]] || {
  echo "Candidate HEAD differs from approved CANDIDATE_SHA: NO-GO" >&2
  exit 1
}
[[ -z "$(git -C "$REPO" status --porcelain --untracked-files=no)" ]] || {
  echo "Live VM tracked working tree is dirty: NO-GO" >&2
  exit 1
}
[[ -z "$(git -C "$CANDIDATE" status --porcelain --untracked-files=no)" ]] || {
  echo "Candidate tracked working tree is dirty: NO-GO" >&2
  exit 1
}
PYTHON="$REPO/backend/.venv/bin/python"
[[ -x "$PYTHON" && -s "$DB" ]] || { echo "Missing live Python environment or saved-reviews DB" >&2; exit 1; }
[[ -f "$CANDIDATE/research/panel_category_release_audit.py" ]] || {
  echo "Candidate lacks paired audit implementation" >&2; exit 1
}
systemctl is-active --quiet "$SERVICE" || { echo "DeFaketive service inactive" >&2; exit 1; }
curl -fsS --max-time 15 http://127.0.0.1:8080/ >/dev/null || {
  echo "Local app HTTP health failed" >&2; exit 1
}
curl -fsS --max-time 15 "$SITE/" >/dev/null || {
  echo "Public app HTTP health failed" >&2; exit 1
}
MODEL_REL="backend/sentiment-analysis/models/sentiment_onnx/xlmr_firecs_v1/model.onnx"
[[ -f "$REPO/$MODEL_REL" && -f "$CANDIDATE/$MODEL_REL" ]] || {
  echo "ONNX model file missing" >&2; exit 1
}
OLD_MODEL_SHA="$(sha256sum "$REPO/$MODEL_REL" | cut -d ' ' -f 1)"
NEW_MODEL_SHA="$(sha256sum "$CANDIDATE/$MODEL_REL" | cut -d ' ' -f 1)"
[[ "$OLD_MODEL_SHA" == "$NEW_MODEL_SHA" ]] || {
  echo "Candidate would alter shipped XLM-RoBERTa model: NO-GO" >&2; exit 1
}
# Preserve the learned hazard model's sentiment SHA gate, tokenizer, thresholds
# and five-label auxiliary models. Unexpected artifact drift is a hard stop.
CRITICAL_ASSETS=(
  backend/sentiment-analysis/models/sentiment_onnx/xlmr_firecs_v1/tokenizer.json
  backend/sentiment-analysis/models/sentiment_onnx/xlmr_firecs_v1/manifest.json
  backend/sentiment-analysis/models/hazard_classifier_v6/manifest.json
  backend/sentiment-analysis/models/hazard_classifier_v6/defect.joblib
  backend/sentiment-analysis/models/hazard_classifier_v6/safety.joblib
  backend/sentiment-analysis/models/extra_labels_v1/manifest.json
  backend/sentiment-analysis/models/extra_labels_v1/not_as_described.joblib
  backend/sentiment-analysis/models/extra_labels_v1/quality.joblib
  backend/sentiment-analysis/models/reference_baselines_v1.json
  backend/sentiment-analysis/defaketive_sentiment/lexicons/hazard_parameters_v1.json
)
for asset in "${CRITICAL_ASSETS[@]}"; do
  if [[ ! -f "$REPO/$asset" || ! -f "$CANDIDATE/$asset" ]] || ! cmp -s "$REPO/$asset" "$CANDIDATE/$asset"; then
    echo "Critical model/config asset differs: $asset; NO-GO" >&2
    exit 1
  fi
done
echo "All learned hazard, auxiliary label, threshold, tokenizer and model assets match"
echo "Live SHA: $OLD_SHA"
echo "Candidate SHA: $CANDIDATE_SHA"
echo "XLM-RoBERTa ONNX SHA256 unchanged"
# The category revision bump invalidates saved analysis versions. The web app
# can recompute these on catalog load; report the actual pending workload.
"$PYTHON" - "$DB" <<'PY'
import sqlite3
import sys
from pathlib import Path
db = Path(sys.argv[1]).resolve(strict=True)
with sqlite3.connect(f"file:{db.as_posix()}?mode=ro", uri=True) as con:
    products = con.execute("SELECT COUNT(*) FROM products").fetchone()[0]
    reviews = con.execute("SELECT COUNT(*) FROM reviews WHERE length(content) >= 12").fetchone()[0]
print(f"Saved products: {products}; eligible review texts: {reviews}")
print("WARNING: category version pc6 can mark saved analyses stale; benchmark reanalysis on isolated staging before production restart.")
PY
free -m | head -n 2
df -h "$REPO" | tail -n 1
if [[ "$MODE" == "--check" ]]; then
  echo "READ-ONLY PREFLIGHT PASSED. This is not approval to deploy."
  exit 0
fi
[[ "$MAX_REVIEWS" =~ ^[1-9][0-9]*$ ]] || { echo "Invalid review limit" >&2; exit 2; }
TMPDIR_PRIVATE="$(mktemp -d)"
chmod 700 "$TMPDIR_PRIVATE"
trap 'rm -rf "$TMPDIR_PRIVATE"' EXIT
# Both commands read the same LIVE DB with SQLite mode=ro, but run separate
# processes so the Python import tree corresponds to each commit.
export TOKENIZERS_PARALLELISM=false
export OPENBLAS_NUM_THREADS=1
export OMP_NUM_THREADS=1
"$PYTHON" "$CANDIDATE/research/panel_category_release_audit.py" scan \
  --checkout "$REPO" --database "$DB" --limit "$MAX_REVIEWS" \
  --out "$TMPDIR_PRIVATE/baseline.json"
"$PYTHON" "$CANDIDATE/research/panel_category_release_audit.py" scan \
  --checkout "$CANDIDATE" --database "$DB" --limit "$MAX_REVIEWS" \
  --out "$TMPDIR_PRIVATE/candidate.json"
"$PYTHON" "$CANDIDATE/research/panel_category_release_audit.py" compare \
  --baseline "$TMPDIR_PRIVATE/baseline.json" \
  --candidate "$TMPDIR_PRIVATE/candidate.json" \
  --out "$TMPDIR_PRIVATE/aggregate.json" --strict
echo "PAIRED READ-ONLY VM AUDIT PASSED. Still requires reviewed release SHA, backups, live E2E and operator authorization."
