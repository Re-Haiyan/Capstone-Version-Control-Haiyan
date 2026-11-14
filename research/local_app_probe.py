"""Start the app locally on a spare port, query it, stop it. Used to see how the app behaves with a given code state.

    backend\\.venv\\Scripts\\python.exe research\\local_app_probe.py [port]

Reads only: /api/saved/products (does each saved report say it was checked with the current checker?), /api/picks, /api/stats/public,
/api/auth/me, and the home page; times each. The local database is opened by the app but nothing is written by these GETs.
"""
import json, os, pathlib, subprocess, sys, time, urllib.request

ROOT = pathlib.Path(__file__).resolve().parent.parent
port = int(sys.argv[1]) if len(sys.argv) > 1 else 8099
env = {**os.environ, "PYTHONUTF8": "1"}
for key in [k for k in env if k.startswith("DEFAKETIVE_")]:
    del env[key]
log = open(ROOT / "research" / "cache" / "local_server.log", "w")
proc = subprocess.Popen([str(ROOT / "backend" / ".venv" / "Scripts" / "python.exe"), str(ROOT / "serve.py"), "--port", str(port)], cwd=str(ROOT), env=env, stdout=log, stderr=subprocess.STDOUT)
base = f"http://127.0.0.1:{port}"


def get(path, timeout=120):
    t = time.time()
    with urllib.request.urlopen(base + path, timeout=timeout) as r:
        body = r.read()
        return r.status, body, round(time.time() - t, 2), dict(r.headers)


try:
    for _ in range(60):
        try:
            get("/", 5); break
        except Exception:
            time.sleep(2)
    out = {}
    status, body, secs, headers = get("/")
    out["home"] = {"status": status, "seconds": secs, "x-content-type-options": headers.get("X-Content-Type-Options"), "x-frame-options": headers.get("X-Frame-Options")}
    status, body, secs, headers = get("/api/stats/public"); out["stats"] = {"status": status, "seconds": secs, "body": json.loads(body)}
    status, body, secs, headers = get("/api/auth/me"); out["me"] = {"status": status, "seconds": secs, "keys": sorted(json.loads(body))}
    status, body, secs, headers = get("/api/picks"); picks = json.loads(body)["products"]
    out["picks"] = {"status": status, "seconds": secs, "count": len(picks), "cache-control": headers.get("Cache-Control"), "have_badge_view": sum(1 for p in picks if (p.get("badge_view") or {}).get("available")),
                    "have_conclusion": sum(1 for p in picks if (p.get("badge_view") or {}).get("conclusion"))}
    status, body, secs, headers = get("/api/saved/products"); saved = json.loads(body)
    items = saved.get("products") if isinstance(saved, dict) else saved
    flags = [p.get("checked_with_current") for p in items or []]
    out["saved_products"] = {"status": status, "seconds": secs, "count": len(items or []), "checked_with_current_true": sum(1 for f in flags if f is True), "checked_with_current_false": sum(1 for f in flags if f is False), "missing": sum(1 for f in flags if f is None)}
    print(json.dumps(out, indent=1))
finally:
    proc.terminate()
    try:
        proc.wait(timeout=15)
    except Exception:
        proc.kill()
