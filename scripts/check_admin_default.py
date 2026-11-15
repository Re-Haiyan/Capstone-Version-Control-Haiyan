"""Read-only check: is the main admin account of an accounts database still using the default password that the source code and the README
publish? It prints only yes/no and never prints a password or a hash. Exit code 0 = the default is NOT active, 1 = it IS active, 2 = no admin
account found or the file could not be read.

    python scripts/check_admin_default.py                      (backend/instance/accounts.db)
    python scripts/check_admin_default.py path/to/accounts.db  (a backup, before restoring it)

Run it on the server before and after every deployment, and on any backup before restoring it: a backup made before the password was
changed brings the default back.
"""
import sqlite3
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE))
import admin_api  # noqa: E402
from werkzeug.security import check_password_hash  # noqa: E402

path = Path(sys.argv[1]) if len(sys.argv) > 1 else HERE / "backend" / "instance" / "accounts.db"
try:
    with sqlite3.connect(f"file:{path.as_posix()}?mode=ro", uri=True) as connection:
        row = connection.execute("SELECT password_hash FROM users WHERE email = ?", (admin_api.ADMIN_EMAIL,)).fetchone()
except sqlite3.Error as error:
    print(f"could not read {path}: {type(error).__name__}")
    sys.exit(2)
if row is None:
    print("no main admin account in this database")
    sys.exit(2)
active = bool(check_password_hash(row[0], admin_api.ADMIN_PASSWORD))
print("DEFAULT ADMIN PASSWORD IS STILL ACTIVE" if active else "default admin password is not active")
sys.exit(1 if active else 0)
