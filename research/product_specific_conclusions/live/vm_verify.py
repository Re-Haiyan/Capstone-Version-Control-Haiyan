"""Run ON THE VM, read-only: the deployed code on the real saved products, explanations on versus off.

Nothing is written to the database. Output: a JSON summary on stdout (no reviewer names).
"""
import json
import os
import sys
import time

os.environ["DEFAKETIVE_CONCLUSION_REASONS"] = "1"
sys.path.insert(0, os.path.abspath("backend"))
os.chdir("backend")
import dashboard_utils as du  # noqa: E402
from data_store import load_saved_products  # noqa: E402

assert du.REASONS_ENABLED
picks = set(json.load(open("/tmp/pick_links.json")))
products = load_saved_products()
out = {"products": len(products), "changed": [], "explained": 0, "limited": 0, "lines": 0, "quotes": 0, "quote_problems": [], "hazard_without_warning": [], "times_ms": [], "errors": [], "samples": []}
for product in products:
    link = str(product.get("link") or "")
    try:
        off = du.badge_view(product)
        t0 = time.perf_counter()
        on = du.badge_view(product, aspects=True)
        out["times_ms"].append(round(1000 * (time.perf_counter() - t0), 1))
    except Exception as exc:
        out["errors"].append([link[:80], repr(exc)[:160]])
        continue
    a, b = off.get("conclusion") or {}, on.get("conclusion") or {}
    same = (off.get("state") == on.get("state") and a.get("decision") == b.get("decision") and a.get("headline") == b.get("headline")
            and [(x.get("category"), x.get("mentions")) for x in off.get("badges", [])] == [(x.get("category"), x.get("mentions")) for x in on.get("badges", [])])
    if not same:
        out["changed"].append([link[:80], off.get("state"), on.get("state"), a.get("decision"), b.get("decision")])
    evidence = b.get("evidence")
    comments = [c for c in (product.get("comments") or []) if isinstance(c, dict)]
    by_id = {str(c.get("comment_id") or c.get("id") or f"review-{i}"): str(c.get("content") or "") for i, c in enumerate(comments)}
    quoted = {}
    if evidence:
        out["explained"] += 1
        out["limited"] += b.get("evidence_status") != "available" if "evidence_status" in b else 0
        for line in evidence.get("why", []):
            out["lines"] += 1
            for q in line.get("quotes", []):
                out["quotes"] += 1
                text = by_id.get(str(q.get("review_id")))
                shown = str(q.get("text") or "")
                body = shown[:-1].rstrip() if shown.endswith("…") else shown
                problem = None
                if text is None:
                    problem = "review id not found"
                elif body not in text:
                    problem = "quotation not in the review"
                elif q.get("span") and text[q["span"][0]:q["span"][1]] != body and not shown.endswith("…"):
                    problem = "span does not match"
                if problem:
                    out["quote_problems"].append([link[:80], problem, shown[:80]])
                quoted[str(q.get("review_id"))] = text
    hazards = {x.get("category"): x.get("mentions") for x in on.get("badges", []) if x.get("mentions")}
    serious = on.get("state") in ("safety_warning", "possible_safety_issue", "possible_counterfeit_or_defect")
    if evidence and serious and not b.get("warnings"):
        out["hazard_without_warning"].append([link[:80], on.get("state"), hazards])
    if link in picks:
        out["samples"].append({
            "name": str(product.get("name"))[:90], "state": on.get("state"), "decision": b.get("decision"), "headline": b.get("headline"),
            "lead": b.get("lead"), "summary": b.get("summary"), "body": b.get("body"), "warnings": b.get("warnings"), "assessment_note": b.get("assessment_note"),
            "evidence_status": b.get("evidence_status"), "hazard_badges": hazards, "reviews": len(comments),
            "why": [{"text": l.get("text"), "polarity": l.get("polarity"), "kind": l.get("kind"), "reviews": l.get("reviews"),
                     "quotes": [{"shown": q.get("text"), "stars": q.get("rating"), "full_review": (quoted.get(str(q.get("review_id"))) or "")[:420]} for q in l.get("quotes", [])]}
                    for l in (evidence or {}).get("why", [])],
        })
times = sorted(out.pop("times_ms"))
out["first_read_ms"] = {"median": times[len(times) // 2], "p95": times[int(len(times) * 0.95)], "max": times[-1]} if times else None
print(json.dumps(out, ensure_ascii=False))
