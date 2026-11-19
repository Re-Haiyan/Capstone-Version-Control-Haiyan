"""Prepare isolated shopper fixtures or sample bounded live Lazada connector cases.

Run only from an isolated checkout. No production database is modified.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import signal
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "backend"), str(ROOT / "backend/sentiment-analysis"), str(ROOT / "tests")]


def prepare():
    import dashboard_utils as du
    from data_store import save_products
    from defaketive_sentiment.category_context import _profiles
    from test_product_category import TITLES, PC3_TITLES
    examples = {category: title for title, category in {**TITLES, **PC3_TITLES}.items()}
    products = []
    for index, (category, profile) in enumerate(_profiles()["profiles"].items()):
        products.append({"name": examples[category], "platform": "lazada",
                         "link": f"https://www.lazada.com.ph/products/acceptance-i{9000000000 + index}.html",
                         "comments": [{"content": profile[k + "_phrases"][0], "rating": star} for k, star in (("positive", 5), ("negative", 1))]})
    products.extend([
        {"name": "Acceptance Phone Charger Positive Hazard", "platform": "lazada",
         "link": "https://www.lazada.com.ph/products/acceptance-i9000000090.html",
         "comments": [{"content": "Excellent charger, great quality, fast charging, very happy and highly recommended! The cable sparked once.", "rating": 5}]},
        {"name": "Acceptance Empty Charger", "platform": "lazada",
         "link": "https://www.lazada.com.ph/products/acceptance-i9000000091.html", "comments": []},
    ])
    analyzed = du.analyze_products(products)
    save_products(analyzed, source="isolated-shopper-acceptance")
    (ROOT / "backend/instance").mkdir(exist_ok=True)
    report = [{"link": p["link"], "category": p["product_category"], "name": p["name"],
               "conclusion": du.badge_view(p),
               "initial_labels": [r["sentiment_analysis"]["sentiment"]["initial_label"] for r in p["comments"]]} for p in analyzed]
    (ROOT / "backend/instance/shopper-fixtures.json").write_text(json.dumps(report, indent=2))
    print(json.dumps({"products": len(analyzed), "hazard": report[-2], "empty": report[-1]}, indent=2))


def live():
    scraper = ROOT / "backend/lazada-scraper/src/lazada_scraper.py"
    folder = ROOT / "backend/instance/shopper-live"
    folder.mkdir(parents=True, exist_ok=True)
    cases = {
        "keyword": ["phone charger"],
        "direct": ["--product-url", "https://www.lazada.com.ph/products/pdp-i5246060610-s31099995054.html"],
        "category": ["--category-url", "https://www.lazada.com.ph/shop-mobiles/"],
    }
    report = []
    for name, query in cases.items():
        command = [sys.executable, str(scraper), *query, "-n", "1", "-r", "1", "--pages", "1", "--window", "headless",
                   "--never-show-window", "--reviews-from", "feed", "--no-verification-pause", "--verification-timeout", "10",
                   "--pagination-retries", "0", "--max-review-pages", "1", "--output", str(folder / f"{name}.json")]
        with (folder / f"{name}.log").open("w") as stream:
            process = subprocess.Popen(command, cwd=ROOT / "backend", stdout=stream, stderr=subprocess.STDOUT, start_new_session=True)
            try:
                code = process.wait(timeout=60)
                state = "completed" if code == 0 else "blocked"
            except subprocess.TimeoutExpired:
                os.killpg(process.pid, signal.SIGTERM)
                process.wait(timeout=10)
                code, state = None, "blocked_timeout"
        log = (folder / f"{name}.log").read_text(errors="replace")
        report.append({"case": name, "state": state, "exit_code": code, "log_tail": log[-2500:]})
    (folder / "report.json").write_text(json.dumps(report, indent=2))
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=["prepare", "live"])
    args = parser.parse_args()
    if not (ROOT / ".shopper-acceptance").is_file() or ROOT == Path("/home/azureuser/defaketive"):
        parser.error("An isolated checkout with a .shopper-acceptance marker is required")
    (prepare if args.mode == "prepare" else live)()
