"""Capture the live view of saved products through the real endpoint /api/saved/detail. Read-only GETs, one at a time.

    python capture.py before 120      (or: after 120, same seed, same products)
"""
import json
import random
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
SITE = "https://defaketive.duckdns.org"
tag, count = sys.argv[1], int(sys.argv[2])
links = json.load(open(HERE / "links.json", encoding="utf-8"))
random.Random(7).shuffle(links)
sample = links[:count]
out = []
started = time.time()
for index, link in enumerate(sample):
    url = SITE + "/api/saved/detail?" + urllib.parse.urlencode({"link": link})
    t0 = time.time()
    try:
        raw = urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "defaketive-deploy-check"}), timeout=90).read()
        data = json.loads(raw)
    except Exception as exc:  # recorded, never hidden
        out.append({"link": link, "error": str(exc)[:200]})
        continue
    product = data["product"]
    view = product.get("badge_view") or {}
    conclusion = view.get("conclusion") or {}
    out.append({
        "link": link, "name": product.get("name"), "state": view.get("state"), "decision": conclusion.get("decision"),
        "headline": conclusion.get("headline"), "lead": conclusion.get("lead"), "summary": conclusion.get("summary"), "text": conclusion.get("text"),
        "assessment": conclusion.get("assessment"), "has_evidence": "evidence" in conclusion, "has_body": bool(conclusion.get("body")), "warnings": conclusion.get("warnings"),
        "badges": [(b.get("category"), b.get("mentions")) for b in view.get("badges", [])], "reviews_analyzed": view.get("reviews_analyzed"),
        "bytes": len(raw), "seconds": round(time.time() - t0, 2),
    })
    time.sleep(0.25)
json.dump(out, open(HERE / f"{tag}.json", "w", encoding="utf-8"), ensure_ascii=False)
ok = [r for r in out if "error" not in r]
print(f"{tag}: {len(ok)} of {len(out)} ok in {time.time() - started:.0f}s; errors: {len(out) - len(ok)}")
