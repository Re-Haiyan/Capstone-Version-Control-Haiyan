#!/usr/bin/env bash
# Guarded update for the *actual VM* via an authenticated operator SSH session.
# Never performs changes unless --apply is explicitly passed.
set -euo pipefail
if [[ "${1:-}" != "--apply" ]]; then
  echo "No changes. Use --apply only after release CI passes and GitHub deployment is reviewed."
  exit 0
fi
REPO="${DEFAKETIVE_REPO:-$HOME/defaketive}"
SITE="${DEFAKETIVE_SITE:-https://defaketive.duckdns.org}"
EXPECTED="2c6e056befe0ad7a24652bd12d4d28f7af236a8f"
cd "$REPO"
test -d .git || { echo "Not a VM Git checkout" >&2; exit 1; }
test -z "$(git status --porcelain --untracked-files=no)" || { echo "Dirty VM checkout: abort" >&2; exit 1; }
OLD="$(git rev-parse HEAD)"
if [[ "$OLD" != "$EXPECTED" ]]; then
  echo "Unexpected live VM SHA $OLD; do not reset or guess" >&2; exit 1
fi
test -x backend/.venv/bin/python
test -s backend/defaketive.db
test -s backend/instance/accounts.db
sudo systemctl is-active --quiet defaketive
curl -fsS --max-time 20 "$SITE/" >/dev/null
backend/.venv/bin/python scripts/check_admin_default.py backend/instance/accounts.db
STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
SAVE="$HOME/defaketive-release-backup-$STAMP"
install -d -m 700 "$SAVE"
# Use SQLite's ONLINE backup API: plain cp can miss WAL writes while the site runs.
backend/.venv/bin/python - "$SAVE" <<'PY'
import sqlite3
import sys
from pathlib import Path
backup_dir = Path(sys.argv[1])
for source_name, output_name in (
    ("backend/defaketive.db", "defaketive.db"),
    ("backend/instance/accounts.db", "accounts.db"),
):
    source_path = Path(source_name).resolve()
    target_path = backup_dir / output_name
    with sqlite3.connect(f"file:{source_path}?mode=ro", uri=True) as source:
        with sqlite3.connect(str(target_path)) as target:
            source.backup(target)
            if target.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
                raise RuntimeError(f"Backup failed integrity check: {output_name}")
    target_path.chmod(0o600)
PY
printf '%s\n' "$OLD" > "$SAVE/old.sha"
sha256sum "$SAVE/defaketive.db" "$SAVE/accounts.db" > "$SAVE/sha256.txt"
git fetch --no-tags origin deployment
TARGET="$(git rev-parse FETCH_HEAD)"
git merge-base --is-ancestor "$OLD" "$TARGET" || { echo "Release does not descend from live code" >&2; exit 1; }
test -z "$(git diff --name-only "$OLD" "$TARGET" -- backend/sentiment-analysis backend/requirements.txt scripts/requirements-lock.txt)" || {
  echo "Release changes shipped sentiment/hazard/category files; abort" >&2; exit 1;
}
sudo install -d -m 755 /etc/systemd/system/defaketive.service.d
printf '[Service]\nEnvironment="DEFAKETIVE_CONCLUSION_REASONS=0"\n' | sudo tee /etc/systemd/system/defaketive.service.d/00-conclusions-off.conf >/dev/null
sudo systemctl daemon-reload
echo "Code target $TARGET. Explanations OFF. Backups at $SAVE"
git merge --ff-only "$TARGET"
if ! bash deploy/setup-server.sh; then
  echo "Update failed; previous code SHA: $OLD; backups: $SAVE" >&2
  exit 1
fi
sudo systemctl is-active --quiet defaketive
curl -fsS --max-time 20 http://127.0.0.1:8080/ >/dev/null
curl -fsS --max-time 20 "$SITE/" >/dev/null
backend/.venv/bin/python scripts/check_admin_default.py backend/instance/accounts.db
echo "VM responding at $TARGET; explanations remain OFF."
echo "Backups: $SAVE. Check saved reports, negative warnings, admin and logs before enabling explanations."
