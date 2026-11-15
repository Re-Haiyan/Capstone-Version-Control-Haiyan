"""Phase 4 rights-cleared review intake with product grouping and leak checks.

This is a DATA-INTEGRITY tool, not a labeler, model trainer, test-score
calculator or scraper.  It will not invent reviews or read F2 model output.

Input is local UTF-8 JSON Lines, one real review per line. The required fields
and usage are in README.md. Source raw files and all output datasets must stay
OUTSIDE the repository. In particular, the F2 output is written to a separate
local vault directory and never displayed by this script.

Usage:
    python research/product_specific_conclusions/phase4/intake.py --input /private/real_reviews.jsonl \
      --dev-output /private/phase4-dev --final-vault /private/phase4-final --confirm-rights
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import re
import sys
import unicodedata
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from urllib.parse import urlsplit

RESEARCH = Path(__file__).resolve().parent.parent
ROOT = RESEARCH.parent.parent
HISTORICAL_PACK = RESEARCH / "human_eval_pack"
HISTORICAL_PHASE3 = RESEARCH / "phase3" / "data"

# Frozen before any Phase 4 rows exist: no tuning split assignments to outcomes.
SPLIT_SALT = "defaketive-phase4-product-splits-2026-11-15-v1"
TARGET = {"D3": 300, "V3": 150, "F2": 200}
REQUIRED = frozenset({
    "marketplace", "listing_id", "listing_url", "listing_title",
    "category", "group", "language", "review_text", "stars",
    "collection_date", "source_kind", "source_id", "rights_confirmed",
})
SOURCE_KINDS = frozenset({"authorized_export", "licensed_dataset", "team_owned"})
LANGUAGES = frozenset({"en", "fil", "taglish", "other", "unknown"})
SAFE_ID = re.compile(r"^[A-Za-z0-9_.:-]{2,140}$")
MARKETPLACE = re.compile(r"^[a-z][a-z0-9_-]{1,39}$")
PII = (
    ("email", re.compile(r"\b[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}\b")),
    ("contact_number", re.compile(r"(?<!\d)(?:\+?63|0)9\d{9}(?!\d)|(?<!\d)\d{11,15}(?!\d)")),
    ("url_in_review", re.compile(r"https?://|www\.", re.I)),
    ("otp_or_secret", re.compile(r"\b(?:OTP|one[- ]time pass(?:code|word)|verification code|password|"
                                   r"access token|secret key)\b", re.I)),
)
F2_FIELDNAMES = ("review_id", "product_hash", "category", "group", "language", "stars",
                 "source_kind", "source_id", "collection_date", "review_text")
DEV_FIELDNAMES = F2_FIELDNAMES
MAX_ROWS = 50_000
MAX_LINE_BYTES = 30_000


class IntakeError(ValueError):
    """Input or safety precondition failed. Outputs are not research-ready."""


def norm(text: str) -> str:
    text = unicodedata.normalize("NFKC", text).casefold()
    return " ".join(re.findall(r"[^\W_]+", text, flags=re.UNICODE))


def words(text: str) -> frozenset[str]:
    return frozenset(norm(text).split())


def sha(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def split_for(marketplace: str, listing_id: str) -> str:
    digest = sha(SPLIT_SALT + "\x00" + marketplace.casefold() + "\x00" + listing_id.casefold())
    n = int(digest, 16) % 1000
    return "D3" if n < 500 else "V3" if n < 750 else "F2"


def product_hash(marketplace: str, listing_id: str) -> str:
    return sha("phase4-product\x00" + marketplace.casefold() + "\x00" + listing_id.casefold())[:24]


def historic_link_hash(link: str) -> str:
    """Phase 3 used raw SHA1(link)[:12] and stored no links."""
    return hashlib.sha1(link.encode("utf-8")).hexdigest()[:12]


def jaccard(left: frozenset[str], right: frozenset[str]) -> float:
    if not left or not right:
        return 0.0
    return len(left & right) / len(left | right)


class OverlapIndex:
    """All nonempty texts, with an inverted-token index for exact/near matches.

    A pair with Jaccard >=0.80 must share at least one token; therefore
    candidates from shared-token postings cannot produce false negatives.
    """
    def __init__(self) -> None:
        self.exact: set[str] = set()
        self.docs: list[frozenset[str]] = []
        self.postings: dict[str, set[int]] = defaultdict(set)

    def add(self, text: str) -> None:
        n = norm(text)
        if not n or n in self.exact:
            return
        toks = words(n)
        idx = len(self.docs)
        self.exact.add(n)
        self.docs.append(toks)
        for token in toks:
            self.postings[token].add(idx)

    def is_duplicate(self, text: str) -> bool:
        n = norm(text)
        if not n or n in self.exact:
            return True
        toks = words(n)
        if not toks:
            return True
        possible: set[int] = set()
        for token in toks:
            possible.update(self.postings.get(token, ()))
        m = len(toks)
        for idx in possible:
            historic = self.docs[idx]
            k = len(historic)
            # Jaccard >=0.8 implies the smaller token set has >=0.8
            # the tokens of the larger; avoids unnecessary intersections.
            if min(m, k) * 5 < max(m, k) * 4:
                continue
            if jaccard(toks, historic) >= 0.8:
                return True
        return False


@dataclass(frozen=True)
class Entry:
    marketplace: str
    listing_id: str
    listing_url: str
    listing_title: str
    category: str
    group: str
    language: str
    review_text: str
    stars: int
    collection_date: str
    source_kind: str
    source_id: str

    @property
    def canonical_key(self) -> str:
        return self.marketplace.casefold() + ":" + self.listing_id.casefold()

    @property
    def split(self) -> str:
        return split_for(self.marketplace, self.listing_id)

    @property
    def hashed_product(self) -> str:
        return product_hash(self.marketplace, self.listing_id)


def parse_entry(raw: object, line_no: int) -> Entry:
    if not isinstance(raw, dict) or set(raw) != REQUIRED:
        missing = sorted(REQUIRED - set(raw)) if isinstance(raw, dict) else sorted(REQUIRED)
        extra = sorted(set(raw) - REQUIRED) if isinstance(raw, dict) else []
        raise IntakeError(f"line {line_no}: required fields mismatch; missing={missing}, extra={extra} "
                          "(reviewer identifiers and unknown fields are prohibited)")
    if any(not isinstance(raw[name], str) for name in REQUIRED - {"stars"}):
        raise IntakeError(f"line {line_no}: all fields other than stars must be strings")
    if raw["rights_confirmed"] != "yes":
        raise IntakeError(f"line {line_no}: source rights must be explicitly confirmed")
    if raw["source_kind"] not in SOURCE_KINDS:
        raise IntakeError(f"line {line_no}: source_kind must be authorized_export, licensed_dataset or team_owned")
    market = raw["marketplace"].strip().lower()
    ident = raw["listing_id"].strip()
    if not MARKETPLACE.fullmatch(market) or not SAFE_ID.fullmatch(ident):
        raise IntakeError(f"line {line_no}: invalid marketplace/listing identifier")
    url = raw["listing_url"].strip()
    parsed = urlsplit(url)
    if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password:
        raise IntakeError(f"line {line_no}: listing_url must be a public HTTPS listing URL, without credentials")
    if raw["language"] not in LANGUAGES:
        raise IntakeError(f"line {line_no}: language must be en, fil, taglish, other or unknown")
    if not SAFE_ID.fullmatch(raw["source_id"]):
        raise IntakeError(f"line {line_no}: source_id must be a non-identifying batch code")
    try:
        d = date.fromisoformat(raw["collection_date"])
        if d > date.today():
            raise ValueError("future collection date")
    except ValueError as e:
        raise IntakeError(f"line {line_no}: collection_date must be a real nonfuture YYYY-MM-DD") from e
    stars = raw["stars"]
    if isinstance(stars, bool) or not isinstance(stars, int) or not 1 <= stars <= 5:
        raise IntakeError(f"line {line_no}: stars must be integer 1..5")
    title = raw["listing_title"].strip()
    text = raw["review_text"].strip()
    if not (8 <= len(title) <= 250) or not (20 <= len(norm(text)) <= 4000):
        raise IntakeError(f"line {line_no}: title or review length out of allowed bounds")
    for field, value in (("listing_title", title), ("review_text", text)):
        for name, expression in PII:
            if expression.search(value):
                raise IntakeError(f"line {line_no}: {field} contains possible {name}; sanitize before intake")
    if not (raw["category"].strip() and raw["group"].strip()):
        raise IntakeError(f"line {line_no}: category/group must be populated")
    if any(len(raw[n]) > 100 for n in ("category", "group")):
        raise IntakeError(f"line {line_no}: category/group too long")
    return Entry(
        market, ident, url, title, raw["category"].strip(), raw["group"].strip(),
        raw["language"], text, stars, raw["collection_date"], raw["source_kind"], raw["source_id"]
    )


def read_input(path: Path) -> list[Entry]:
    records: list[Entry] = []
    with path.open("rb") as stream:
        for line_no, line in enumerate(stream, 1):
            if line_no > MAX_ROWS or len(line) > MAX_LINE_BYTES:
                raise IntakeError("input exceeds row/line limits")
            if not line.strip():
                continue
            try:
                raw = json.loads(line.decode("utf-8"))
            except (ValueError, UnicodeError) as e:
                raise IntakeError(f"line {line_no}: invalid UTF-8 JSON") from e
            records.append(parse_entry(raw, line_no))
    if not records:
        raise IntakeError("empty input; no Phase 4 data collected")
    return records


def _csv_rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as stream:
        return list(csv.DictReader(stream))


def historical_index(pack: Path = HISTORICAL_PACK, phase3: Path = HISTORICAL_PHASE3
                     ) -> tuple[OverlapIndex, set[str], set[str]]:
    """Read historical data ONLY for exclusion, never for model improvement.

    All 5,946 locked reviews, Phase 3 D1/D2/F texts and full product titles
    are excluded. The Phase 3 manifest has only legacy short SHA1(link) hashes,
    so compare those too. If any source is missing, fail closed.
    """
    index = OverlapIndex()
    old_titles: set[str] = set()
    old_hashes: set[str] = set()
    for row in _csv_rows(pack / "reviews.csv"):
        index.add(row["review_text"])
    for row in _csv_rows(pack / "card_sheet_A.csv"):
        old_titles.add(norm(row["product"]))
    for split in ("D1", "D2", "F"):
        for row in _csv_rows(phase3 / f"sheet_{split}.csv"):
            index.add(row["review_text"])
    for row in _csv_rows(phase3 / "data_manifest.csv"):
        if row["product_hash"]:
            old_hashes.add(row["product_hash"])
    if len(old_titles) < 35 or len(index.docs) < 100 or not old_hashes:
        raise IntakeError("historical exclusion set is unexpectedly incomplete; refusing intake")
    return index, old_titles, old_hashes


def title_overlaps(title: str, old_titles: set[str]) -> bool:
    candidate = norm(title)
    if not candidate:
        return True
    for old in old_titles:
        if candidate == old or candidate.startswith(old + " ") or old.startswith(candidate + " "):
            return True
        # Some historical titles are cropped at 100 characters. A close
        # token match is deliberately rejected rather than assumed fresh.
        x, y = words(candidate), words(old)
        if len(x) >= 4 and len(y) >= 4 and jaccard(x, y) >= 0.80:
            return True
    return False


def build(entries: list[Entry], historic: tuple[OverlapIndex, set[str], set[str]]) -> dict:
    index, old_titles, old_hashes = historic
    selected: dict[str, list[dict]] = {"D3": [], "V3": [], "F2": []}
    reasons: Counter[str] = Counter()
    product_info: dict[str, tuple[str, str, str]] = {}
    seen_prod: set[str] = set()
    for entry in entries:
        key = entry.canonical_key
        product_info.setdefault(key, (norm(entry.listing_title), entry.category, entry.group))
        if product_info[key] != (norm(entry.listing_title), entry.category, entry.group):
            raise IntakeError("conflicting product title/category for a canonical listing ID")
        # Re-running against an unsorted input must yield the same result.
    for entry in sorted(entries, key=lambda x: (x.hashed_product, sha(norm(x.review_text)))):
        key = entry.canonical_key
        if key not in seen_prod:
            seen_prod.add(key)
        if historic_link_hash(entry.listing_url) in old_hashes or title_overlaps(entry.listing_title, old_titles):
            reasons["historical_product_overlap"] += 1
            continue
        if index.is_duplicate(entry.review_text):
            reasons["historical_or_internal_duplicate"] += 1
            continue
        index.add(entry.review_text)
        review_id = sha("phase4-review\x00" + entry.hashed_product + "\x00" + norm(entry.review_text))[:24]
        selected[entry.split].append({
            "review_id": review_id, "product_hash": entry.hashed_product,
            "category": entry.category, "group": entry.group, "language": entry.language,
            "stars": entry.stars, "source_kind": entry.source_kind,
            "source_id": entry.source_id, "collection_date": entry.collection_date,
            "review_text": entry.review_text,
        })
    product_splits: dict[str, set[str]] = defaultdict(set)
    for split, rows in selected.items():
        for row in rows:
            product_splits[row["product_hash"]].add(split)
    if any(len(values) != 1 for values in product_splits.values()):
        raise IntakeError("product leakage across splits")
    counts = {split: len(rows) for split, rows in selected.items()}
    by_split_products = {
        split: len({r["product_hash"] for r in rows})
        for split, rows in selected.items()
    }
    complete = all(counts[s] >= target for s, target in TARGET.items())
    return {
        "rows": selected,
        "manifest": {
            "phase": "4", "method": "rights-cleared real reviews only; AI-only labels not yet collected",
            "salt_sha256": sha(SPLIT_SALT),
            "split_rule": "SHA256(salt + NUL + marketplace + NUL + listing_id) % 1000: D3 < 500; V3 < 750; F2 otherwise",
            "rows_submitted": len(entries),
            "rows_accepted": sum(counts.values()),
            "rows_rejected_by_reason": dict(sorted(reasons.items())),
            "counts": counts,
            "product_counts": by_split_products,
            "targets": TARGET,
            "research_ready": complete,
            "ready_explanation": (
                "Targets met by row count only. Additional category/language coverage and "
                "provenance/AI label checks are required before using data to choose a model."
                if complete else "Insufficient new reviews to meet all predeclared D3/V3/F2 targets"
            ),
            "language_counts": {
                split: dict(sorted(Counter(row["language"] for row in rows).items()))
                for split, rows in selected.items()
            },
            "category_counts": {
                split: dict(sorted(Counter(row["category"] for row in rows).items()))
                for split, rows in selected.items()
            },
            "f2_visibility": "Sealed into separately restricted local vault; never print F2 rows or include them in development output",
            "labels": "NONE; no model accuracy or human reference inferred",
            "privacy": "Automated checks only; a separate restricted human privacy review is still necessary",
        },
    }


def _outside_repo(path: Path) -> bool:
    resolved = path.resolve()
    return resolved != ROOT.resolve() and ROOT.resolve() not in resolved.parents


def _write_private(path: Path, fieldnames: tuple[str, ...], rows: list[dict]) -> None:
    fd = os.open(str(path), os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    path.chmod(0o600)


def emit(report: dict, dev_output: Path, final_vault: Path) -> None:
    """Write once to distinct off-repo locations; fail if destinations exist."""
    if not _outside_repo(dev_output) or not _outside_repo(final_vault):
        raise IntakeError("outputs MUST be outside the Git repository")
    if dev_output.resolve() == final_vault.resolve() or (
        dev_output.resolve() in final_vault.resolve().parents or
        final_vault.resolve() in dev_output.resolve().parents
    ):
        raise IntakeError("F2 vault and development output must be disjoint")
    if dev_output.exists() or final_vault.exists():
        raise IntakeError("destination already exists; cannot overwrite existing data")
    dev_output.mkdir(mode=0o700, parents=True)
    final_vault.mkdir(mode=0o700, parents=True)
    _write_private(dev_output / "D3.csv", DEV_FIELDNAMES, report["rows"]["D3"])
    _write_private(dev_output / "V3.csv", DEV_FIELDNAMES, report["rows"]["V3"])
    _write_private(final_vault / "F2_SEALED_DO_NOT_OPEN.csv", F2_FIELDNAMES, report["rows"]["F2"])
    manifest = dict(report["manifest"])
    manifest["f2_vault_file_sha256"] = hashlib.sha256(
        (final_vault / "F2_SEALED_DO_NOT_OPEN.csv").read_bytes()
    ).hexdigest()
    manifest["f2_vault_file_count"] = len(report["rows"]["F2"])
    fd = os.open(str(dev_output / "manifest.json"), os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as stream:
        json.dump(manifest, stream, indent=2, ensure_ascii=False)
        stream.write("\n")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--dev-output", required=True, type=Path)
    parser.add_argument("--final-vault", required=True, type=Path)
    parser.add_argument("--confirm-rights", action="store_true",
                        help="Confirm source access and review usage rights; do not guess or fabricate this")
    parser.add_argument("--dry-run", action="store_true",
                        help="Validate and report counts but write NO files")
    args = parser.parse_args()
    try:
        if not args.confirm_rights:
            raise IntakeError("--confirm-rights required; permission cannot be inferred")
        if not _outside_repo(args.input):
            raise IntakeError("raw input MUST reside outside this Git repository")
        if not _outside_repo(args.dev_output) or not _outside_repo(args.final_vault):
            raise IntakeError("outputs MUST reside outside the Git repository")
        entries = read_input(args.input)
        historical = historical_index()
        report = build(entries, historical)
        if not args.dry_run:
            emit(report, args.dev_output, args.final_vault)
        safe = {k: v for k, v in report["manifest"].items()
                if k in ("counts", "product_counts", "rows_submitted", "rows_accepted",
                         "rows_rejected_by_reason", "research_ready", "ready_explanation")}
        print(json.dumps(safe, indent=2, sort_keys=True))
        if not report["manifest"]["research_ready"]:
            print("NOT RESEARCH READY: new real review targets have not been met.", file=sys.stderr)
    except (IntakeError, OSError) as err:
        parser.exit(2, f"Phase 4 intake refused: {err}\n")


if __name__ == "__main__":
    main()
