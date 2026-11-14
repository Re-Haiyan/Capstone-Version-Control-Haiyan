"""Post-deployment smoke test: public, read-only checks of a running DeFaketive site. Standard library only; writes nothing to the site.

    python scripts/smoke_test.py https://defaketive.duckdns.org
    python scripts/smoke_test.py http://127.0.0.1:5000 --save-baseline before.json      (run on the OLD version, before deploying)
    python scripts/smoke_test.py https://defaketive.duckdns.org --compare before.json    (run on the NEW version, right after deploying)

Checks: the home page and security headers; the public stats; the sign-in state route; /api/picks (every pick has a report, a
conclusion card, and every highlighted range lies inside its quote); a static asset; the saved-report list (how many reports were checked
with the running checker: after a deployment that changes the rules this is expected to be 0 until scripts/recheck_products.py runs).
--compare lists any pick whose verdict state or conclusion card differs from the baseline: right after deploying, before a re-check, there
must be none (saved reports are shown as stored). Exit code 0 only if every check passes.
"""
import json
import re
import sys
import time
import urllib.request

DECISIONS = {"recommended", "mixed", "caution", "not_recommended", "not_enough"}
results = []


def record(name, ok, detail=""):
    results.append((name, ok, detail))
    print(("PASS  " if ok else "FAIL  ") + name + (f"  ({detail})" if detail else ""))


def get(base, path, timeout=60):
    t = time.time()
    request = urllib.request.Request(base + path, headers={"User-Agent": "defaketive-smoke-test"})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return response.status, response.read(), dict(response.headers), round(time.time() - t, 2)


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    base = (args[0] if args else "http://127.0.0.1:5000").rstrip("/")
    opt = {}
    for i, a in enumerate(sys.argv[1:]):
        if a in ("--save-baseline", "--compare") and i + 2 <= len(sys.argv[1:]) - 0:
            opt[a] = sys.argv[1:][i + 1]
    print(f"smoke test of {base}")
    try:
        status, body, headers, secs = get(base, "/")
        record("home page answers 200 with HTML", status == 200 and "text/html" in headers.get("Content-Type", ""), f"{secs}s")
        record("security headers on the home page", headers.get("X-Content-Type-Options") == "nosniff" and headers.get("X-Frame-Options") == "DENY")
        assets = re.findall(r'(?:href|src)="(/_app/[^"]+\.(?:css|js))"', body.decode("utf-8", "ignore"))
        if assets:
            status2, _, _, _ = get(base, assets[0])
            record("a built asset is served", status2 == 200, assets[0][:50])
        else:
            record("a built asset is referenced by the home page", False, "none found")
        status, body, headers, secs = get(base, "/api/stats/public")
        stats = json.loads(body)
        record("public stats report products and reviews", status == 200 and stats.get("products", 0) > 0 and stats.get("reviews", 0) > 0, str(stats))
        status, body, headers, secs = get(base, "/api/auth/me")
        me = json.loads(body)
        record("sign-in state route answers for a guest", status == 200 and "guest" in me and "user" in me)
        status, body, headers, secs = get(base, "/api/picks")
        picks = json.loads(body).get("products", [])
        record("/api/picks is never cached", "no-store" in headers.get("Cache-Control", ""))
        record("/api/picks returns products", status == 200 and len(picks) > 0, f"{len(picks)} products, {secs}s")
        bad_view = [p.get("link") for p in picks if not (p.get("badge_view") or {}).get("available")]
        record("every pick carries a report", not bad_view, f"{len(bad_view)} without")
        bad_card = [p.get("link") for p in picks if ((p.get("badge_view") or {}).get("conclusion") or {}).get("decision") not in DECISIONS]
        record("every pick carries a conclusion card with a known decision", not bad_card, f"{len(bad_card)} without")
        outside = quotes = 0
        for p in picks:
            for badge in (p.get("badge_view") or {}).get("badges") or []:
                for quote in badge.get("evidence") or []:
                    quotes += 1
                    text = str(quote.get("text") or "")
                    for h in quote.get("highlights") or []:
                        rng = h if isinstance(h, (list, tuple)) else (h.get("span") if isinstance(h, dict) else None)
                        if rng and not (0 <= rng[0] < rng[1] <= len(text) and text[rng[0]:rng[1]].strip()):
                            outside += 1
        record("every highlighted range lies inside its quote", outside == 0, f"{quotes} quotes checked, {outside} bad")
        status, body, headers, secs = get(base, "/api/saved/products", timeout=120)
        saved = json.loads(body)
        items = saved.get("products") if isinstance(saved, dict) else saved
        flags = [p.get("checked_with_current") for p in items or []]
        print(f"INFO  saved reports: {len(items or [])}; checked with the running checker: {sum(1 for f in flags if f is True)}, not: {sum(1 for f in flags if f is False)} ({secs}s)")
        record("saved-report list answers", status == 200 and len(items or []) > 0)
        snapshot = {p.get("link"): {"state": (p.get("badge_view") or {}).get("state"), "decision": ((p.get("badge_view") or {}).get("conclusion") or {}).get("decision")} for p in picks}
        if "--save-baseline" in opt:
            json.dump(snapshot, open(opt["--save-baseline"], "w"), indent=1)
            print(f"INFO  baseline of {len(snapshot)} picks saved to {opt['--save-baseline']}")
        if "--compare" in opt:
            before = json.load(open(opt["--compare"]))
            changed = [(k, before[k], snapshot[k]) for k in before if k in snapshot and before[k] != snapshot[k]]
            missing = [k for k in before if k not in snapshot]
            record("no pick changed verdict or card since the baseline", not changed, f"{len(changed)} changed, {len(missing)} no longer in the picks")
            for k, a, b in changed[:10]:
                print(f"      {k[-40:]}: {a} -> {b}")
    except Exception as error:  # noqa: BLE001
        record("the site answered", False, repr(error)[:120])
    failed = [r for r in results if not r[1]]
    print(f"\n{len(results) - len(failed)} of {len(results)} checks passed")
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
