"""Read what reviewers say about a product's own features, one clause at a time, and keep the proof.

For every review this module records which feature (an "aspect": softness, battery life, fit ...) a clause praises
or criticises, with the review's id, the exact words and where they sit in the review. Nothing here is a model; the
rules are small tables (aspect_profiles.py) and a handful of reading rules that can be checked by hand:

  1. A review is cut into clauses with the project's own segmenter (a contrast word such as "pero" or "but" starts a
     new clause), so "ang ganda ng amoy pero sobrang drying" is two statements.
  2. A clause is skipped, and counted as skipped, when it only wonders or recalls a fear ("akala ko fake"), compares
     with something else ("mas maganda kaysa..."), or is sarcastic or contradicted by its own emoji.
  3. Negation is read within four words before the cue: a negated praise word is a complaint ("hindi malambot"), and
     a negated complaint word is a denial ("hindi naman fake"), which is never counted as praise of anything.
  4. A review that says it has not used the product yet cannot praise how it performs.
  5. A review rated one or two stars that praises a feature is set aside (shown as excluded), because the stars and
     the words disagree and the commonest cause is sarcasm or a different order.
  6. A review counts once for an aspect. If it praises and criticises the same aspect it counts for neither side.
  7. Copied reviews (already flagged, or the same words again) count once.

The result says how many DISTINCT reviews support each side of each aspect, and carries the quotations. It makes no
claim about the product beyond "these reviewers wrote this".
"""

from __future__ import annotations

import hashlib
import importlib.util
import re
import sys
import unicodedata
from collections import OrderedDict
from pathlib import Path
from typing import Any, Iterable, Sequence

import aspect_profiles as profiles
from aspect_profiles import (
    ASPECT_RULES_VERSION,
    COMPARISON,
    EVIDENCE_POLICY,
    HABIT,
    HYPOTHETICAL,
    NEGATIVE_EMOJI,
    NEGATORS,
    NO_EXPERIENCE,
    POSITIVE_EMOJI,
    PROMOTION,
    PROMPT_LABEL,
    PRODUCT,
    RELIEF,
    SARCASM,
    SERVICE,
    TRUST,
    Aspect,
)

_NORM: Any = None


def _normalizer() -> Any:
    """The project's shared text normaliser and segmenter (taglish-norm-1.0.0), loaded once."""
    global _NORM
    if _NORM is None:
        package = Path(__file__).resolve().parent / "sentiment-analysis"
        file = package / "defaketive_sentiment" / "text_norm.py"
        try:
            # text_norm.py uses only the standard library. Importing it as part of its package would also import the sentiment
            # models (numpy, scikit-learn, joblib: about 7 s on a fast PC, and slower on a small server) the first time a
            # product page is opened. Loading the one file avoids that; it reads the same word lists, so the segmentation is the same.
            spec = importlib.util.spec_from_file_location("defaketive_text_norm_standalone", file)
            module = importlib.util.module_from_spec(spec)  # type: ignore[arg-type]
            sys.modules[spec.name] = module  # type: ignore[union-attr]
            spec.loader.exec_module(module)  # type: ignore[union-attr]
            _NORM = module
        except Exception:
            if str(package) not in sys.path:
                sys.path.insert(0, str(package))
            from defaketive_sentiment import text_norm

            _NORM = text_norm
    return _NORM


# Short spellings the shared normaliser leaves alone and the tables are written against.
_SHORT = {"d": "hindi", "di": "hindi", "hnd": "hindi", "hnde": "hindi", "hndi": "hindi", "hindu": "hindi", "indi": "hindi", "ndi": "hindi", "wla": "wala", "ung": "yung", "nmn": "naman", "mhina": "mahina", "pngit": "pangit", "gnda": "ganda", "mganda": "maganda", "sulit": "sulit"}
_TOKEN = re.compile(r"[\w']+|[^\w\s]", re.UNICODE)
_WORD = re.compile(r"[\w']+", re.UNICODE)
_FIL = frozenset(
    "ang ng sa na yung ko mo po naman pero hindi di ito siya sya lang talaga sobrang mga kasi pa din rin ba nya niya nga "
    "mabilis maganda ganda sakin akin namin nila yan yun dito dun kaya may wala walang ako ka kayo sila".split()
)
_ENG = frozenset("the is it and this very good not but my was for with i to of a are so too have has had really".split())
_NEGATOR_FORMS = {word.replace("'", "").replace("’", "") for word in NEGATORS} | set(NEGATORS)


# "Excellent build quality., Great value for money., Perfect length for my setup.," Lazada lets a buyer tick suggested
# phrases; the same block then appears under dozens of reviews. It says nothing about what THIS buyer found, and
# counting it would make one template look like many independent endorsements.
MENU_TAGS = re.compile(r"[.!?],\s*\S")
# The same block without full stops: "Impressive sound quality, Convenient wireless connectivity, Crystal clear calls,".
# Two or more capitalised phrases after commas, or a labelled capitalised phrase that ends in a comma.
_MENU_COMMAS = re.compile(r",\s+[A-Z][a-z]+")
_MENU_LABELLED = re.compile(r"^\s*[A-Za-z][A-Za-z ]{2,28}:\s*[A-Z][^,]*,\s*$")


_MENU_TRAILING = re.compile(r"[.!?]?,[^\w]*$")
_MENU_MIDWORD = re.compile(r"(?<=[a-z0-9,.]\s)[A-Z][a-z]{2,}")
_FIRST_PERSON = re.compile(r"\b(?:i|i'm|i've|my|me|mine|we|our|ko|ako|akin|sakin|saken|namin|ginamit|nagamit|nabili|binili|bumili)\b", re.I)


def _is_menu_block(clause: str) -> bool:
    """A block of phrases the marketplace suggests to the buyer, not the buyer's own sentence.

    Recognised by its shape: ".,"; two or more capitalised phrases after commas; one such phrase when the block ends in
    a comma; three capitalised words in the middle of the clause; or a capitalised list of two or more phrases that has
    no "I", "my" or "ko" in it. This errs on the side of leaving a claim out: a terse genuine "Good quality, Fast
    delivery." is lost, a template counted as an endorsement is not.
    """
    commas = len(_MENU_COMMAS.findall(clause))
    list_like = clause[:1].isupper() and commas >= 1 and len(clause.split()) >= 4 and not _FIRST_PERSON.search(clause)
    return bool(
        MENU_TAGS.search(clause)
        or commas >= 2
        or (commas >= 1 and _MENU_TRAILING.search(clause))
        or len(_MENU_MIDWORD.findall(PROMPT_LABEL.sub(" ", clause))) >= 3
        or list_like
        or _MENU_LABELLED.match(clause)
    )
_STRETCH = re.compile(r"(.)\1{2,}")


def _collapse(match: "re.Match[str]") -> str:
    # "gandaaaa" -> "ganda", "gooood" -> "good": runs of three or more are cut to one letter, or two for o and e,
    # which double in real words (good, sweet).
    letter = match.group(1)
    return letter * 2 if letter in "oe" else letter


def fold(text: Any) -> str:
    """Lower-cased text with stretched letters cut back and the common short spellings spelt out.

    Matching runs on this and quoting never does. The project's affix-folding normaliser is NOT used here on purpose:
    it turns "umiinit" into "init" and "nag-lag" into "naglag", and the aspect tables are written for the words as
    reviewers type them. Clause cutting still uses the project's segmenter (text_norm.segment_sentences).
    """
    value = unicodedata.normalize("NFKC", str(text or "")).lower().replace("’", "'").replace("‘", "'")
    value = _STRETCH.sub(_collapse, value)
    return " ".join(_SHORT.get(token, token) for token in value.split())


def language_of(text: str) -> str:
    """"en", "fil" or "taglish": a rough label for the quotation, from common function words only."""
    words = [word.lower() for word in _WORD.findall(text)]
    fil = sum(word in _FIL for word in words)
    eng = sum(word in _ENG for word in words)
    if fil and eng:
        return "taglish"
    if fil:
        return "fil"
    return "en"


_CONSUMES = frozenset(
    "working work works gumagana gumana functioning defect defects defective problem problems issue issues damage damaged "
    "damages sira complaint complaints fake scratches scratch dents dent overpowering matapang masangsang".split()
)


def _negated(text: str, start: int) -> bool:
    """Whether the cue at `start` sits under a negation: one of the four words before it, inside its own clause."""
    piece = re.split(r"[.!?;:,]|\b(?:pero|pro|but|and|at|kaso|kaya|kasi|although|though|yet)\b", text[:start])[-1]
    words = _WORD.findall(piece)
    previous = words[-4:]
    last = None
    for position, word in enumerate(previous):
        if word.replace("’", "'") in NEGATORS or word.replace("'", "") in _NEGATOR_FORMS:
            last = position
    if last is None:
        # "does not irritate or cause any breakouts": "or" and "nor" carry the negation to the next item, further than four words.
        wide = words[-9:]
        for position, word in enumerate(wide):
            if word.replace("’", "'") in NEGATORS or word.replace("'", "") in _NEGATOR_FORMS:
                last = position
        return last is not None and any(word in ("or", "nor") for word in wide[last + 1 :])
    # "no defects good packaging", "not working ok naman yung tunog": the negation was used up by the word right after it.
    return not any(word in _CONSUMES for word in previous[last + 1 :])


def _relieved(text: str, start: int) -> bool:
    piece = re.split(r"[.!?;:,]", text[:start])[-1]
    return bool(RELIEF.search(" ".join(_WORD.findall(piece)[-5:])))


def _clause_polarity(aspect: Aspect, text: str) -> tuple[str | None, str]:
    """("positive" | "negative" | "denied" | None, how it was decided) for one aspect in one folded clause."""
    verdicts: set[str] = set()
    denied = False
    if aspect.quick is None or not aspect.quick.search(text):
        return None, "none"
    if aspect.skip_if is not None and aspect.skip_if.search(text):
        return None, "none"
    for pattern in aspect.pos:
        for match in pattern.finditer(text):
            if _negated(text, match.start()):
                if not aspect.problem_only:
                    verdicts.add("negative")  # "hindi malambot": a complaint about softness
            else:
                verdicts.add("positive")
    for pattern in aspect.neg:
        for match in pattern.finditer(text):
            if aspect.neg_guard is not None and aspect.neg_guard.search(text):
                continue
            if _negated(text, match.start()) or (aspect.problem_only and _relieved(text, match.start())):
                denied = True  # "walang sira", "nawala ang rashes": the problem is denied, not reported
            else:
                verdicts.add("negative")
    if "positive" in verdicts and "negative" in verdicts:
        return None, "conflict"
    if verdicts:
        return next(iter(verdicts)), "cue"
    if denied:
        return "denied", "denied"
    return None, "none"


def _emoji_polarity(text: str) -> str | None:
    positive, negative = bool(POSITIVE_EMOJI.search(text)), bool(NEGATIVE_EMOJI.search(text))
    return "positive" if positive and not negative else "negative" if negative and not positive else None


def _bounded(clauses: Iterable[str], limit: int) -> Iterable[str]:
    """Cut an over-long clause (a rambling review the segmenter could not split) into pieces at word breaks, so the
    patterns never scan a huge string. Each piece is still a verbatim slice of the review."""
    for clause in clauses:
        while len(clause) > limit:
            cut = clause.rfind(" ", 0, limit)
            cut = cut if cut > limit // 2 else limit
            yield clause[:cut]
            clause = clause[cut:].lstrip()
        if clause:
            yield clause


def _stars(value: Any) -> float | None:
    """A star rating as a number. Saved reports hold numbers; raw scans hold strings ("5"); anything else is unknown."""
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value) if 0 < value <= 5 else None
    try:
        number = float(str(value).strip())
    except (TypeError, ValueError):
        return None
    return number if 0 < number <= 5 else None


def _compact(content: str) -> tuple[list[int], str]:
    """The review without whitespace, and where each remaining character sat in the original."""
    positions = [i for i, ch in enumerate(content) if not ch.isspace()]
    return positions, "".join(content[i] for i in positions)


def _locate(index: tuple[list[int], str], clause: str) -> list[int] | None:
    """[start, end) of the clause in the original review, found without regard to the whitespace the segmenter changed."""
    positions, flat = index
    target = "".join(ch for ch in clause if not ch.isspace())
    if not target:
        return None
    start = flat.find(target)
    if start < 0:
        return None
    return [positions[start], positions[start + len(target) - 1] + 1]


def _verbatim(content: str, span: list[int] | None, clause: str, limit: int) -> tuple[str, list[int] | None]:
    """The words shown for a claim: the original slice of the review (whitespace collapsed), cut at a word if long."""
    if span is None:  # the segmenter's text could not be found in the review; show it, but claim no position
        return _short_text(" ".join(clause.split()), limit), None
    piece = content[span[0] : span[1]]
    if len(" ".join(piece.split())) <= limit:
        return " ".join(piece.split()), span
    cut = piece[:limit].rsplit(None, 1)[0] if len(piece[:limit].split()) > 1 else piece[:limit]
    cut = cut.rstrip(",;:- \n\t")
    return " ".join(cut.split()) + "…", [span[0], span[0] + len(cut)]


def _short_text(text: str, limit: int) -> str:
    return text if len(text) <= limit else text[:limit].rsplit(" ", 1)[0].rstrip(",;:-") + "…"


def _text_key(text: str) -> str:
    return hashlib.sha1(re.sub(r"\W+", "", fold(text)).encode("utf-8")).hexdigest()


class _Side:
    __slots__ = ("ids", "quotes", "low_star", "no_experience")

    def __init__(self) -> None:
        self.ids: "OrderedDict[str, None]" = OrderedDict()
        self.quotes: list[dict[str, Any]] = []
        self.low_star = 0
        self.no_experience = 0


def extract(
    comments: Sequence[dict[str, Any]],
    category: str | None = None,
    group: str | None = None,
) -> dict[str, Any]:
    """Aspect evidence for one product's reviews. Pure and deterministic: the same reviews give the same answer."""
    policy = EVIDENCE_POLICY
    aspects = profiles.aspects_for(category, group)
    sides: dict[str, dict[str, _Side]] = {aspect.id: {"positive": _Side(), "negative": _Side()} for aspect in aspects}
    denied_ids: dict[str, set[str]] = {aspect.id: set() for aspect in aspects}
    excluded = {"truncated_reviews": 0, "promotional": 0, "habit": 0, "duplicate": 0, "duplicate_text": 0, "empty": 0, "hypothetical": 0, "comparison": 0, "sarcasm_or_emoji": 0, "conflict": 0, "menu_tag": 0}
    seen_text: set[str] = set()
    considered = 0
    no_experience_reviews = 0
    product_reviews: set[str] = set()
    service_reviews: set[str] = set()
    kinds = {aspect.id: aspect.kind for aspect in aspects}
    norm = _normalizer()

    for index, review in enumerate(comments or []):
        if not isinstance(review, dict):
            continue
        content = str(review.get("content") or "").strip()
        if review.get("is_duplicate") or review.get("included_in_analysis") is False:
            excluded["duplicate"] += 1
            continue
        if len(content) < 2:
            excluded["empty"] += 1
            continue
        if len(content) > policy["max_review_chars"]:
            content = content[: policy["max_review_chars"]]  # a review is read up to this length; the rest is not (and is counted)
            excluded["truncated_reviews"] += 1
        if PROMOTION.search(content):
            excluded["promotional"] += 1
            continue
        key = _text_key(content)
        if key in seen_text:
            excluded["duplicate_text"] += 1
            continue
        seen_text.add(key)
        considered += 1
        review_id = str(review.get("comment_id") or review.get("id") or f"review-{index}")
        rating = _stars(review.get("rating"))
        low_star = rating is not None and rating <= policy["contradiction_max_stars"]
        index = _compact(content)
        no_experience = bool(NO_EXPERIENCE.search(fold(content)))
        no_experience_reviews += no_experience
        claims: dict[tuple[str, str], dict[str, Any]] = {}
        for clause in _bounded(norm.segment_sentences(content), policy["max_clause_chars"]):
            if _is_menu_block(clause):
                excluded["menu_tag"] += 1  # a block of tags picked from the marketplace's menu, not the buyer's own words
                continue
            text = fold(PROMPT_LABEL.sub(" ", clause))
            if HABIT.search(text):
                excluded["habit"] += 1
                continue
            if HYPOTHETICAL.search(text):
                excluded["hypothetical"] += 1
                continue
            if COMPARISON.search(text):
                excluded["comparison"] += 1
                continue
            if SARCASM.search(text):
                excluded["sarcasm_or_emoji"] += 1
                continue
            emoji = _emoji_polarity(clause)
            not_used_yet = bool(NO_EXPERIENCE.search(text))  # "di pa nagagamit": no opinion yet, in either direction
            labelled = bool(PROMPT_LABEL.search(clause))
            for aspect in aspects:
                if not_used_yet and aspect.kind == PRODUCT:
                    continue
                if labelled and aspect.id == "authenticity":
                    continue  # "Effectiveness:legit": the answer belongs to the prompt it follows, and here "legit" means "it works"
                polarity, how = _clause_polarity(aspect, text)
                if how == "conflict":
                    excluded["conflict"] += 1
                    continue
                if polarity is None and aspect.topic and emoji and any(topic.search(text) for topic in aspect.topic):
                    polarity, how = emoji, "emoji"
                if polarity is None:
                    continue
                if polarity == "denied":
                    if aspect.denial_is_positive:
                        polarity = "positive"
                    else:
                        denied_ids[aspect.id].add(review_id)
                        continue
                if how == "cue" and emoji and emoji != polarity:
                    excluded["sarcasm_or_emoji"] += 1  # "ganda ng amoy 😡": words and face disagree, so neither is trusted
                    continue
                span = _locate(index, clause)
                claim = claims.setdefault((aspect.id, polarity), {"clause": clause, "span": span, "how": how})
                if len(clause) < len(claim["clause"]) and len(clause) > 12:
                    claim.update(clause=clause, span=span)
        for (aspect_id, polarity), claim in claims.items():
            side = sides[aspect_id][polarity]
            if polarity == "positive" and kinds[aspect_id] == PRODUCT:
                if no_experience:
                    side.no_experience += 1
                    continue
                if low_star:
                    side.low_star += 1
                    continue
            if review_id in side.ids:
                continue
            side.ids[review_id] = None
            shown, span = _verbatim(content, claim["span"], claim["clause"], policy["quote_chars"])
            if len(side.quotes) < policy["quotes_per_side"] + 4:  # a few spare so the best two can be chosen below
                side.quotes.append(
                    {
                        "review_id": review_id,
                        "text": shown,
                        "span": span,
                        "language": language_of(claim["clause"]),
                        "rating": rating,
                        "evidence": "clear" if claim["how"] == "cue" else claim["how"],
                    }
                )
            if kinds[aspect_id] == PRODUCT:
                product_reviews.add(review_id)
            elif kinds[aspect_id] == SERVICE:
                service_reviews.add(review_id)

    rows: list[dict[str, Any]] = []
    for aspect in aspects:
        pos, neg = sides[aspect.id]["positive"], sides[aspect.id]["negative"]
        both = set(pos.ids) & set(neg.ids)
        if not pos.ids and not neg.ids:
            continue
        positive_ids = [rid for rid in pos.ids if rid not in both]
        negative_ids = [rid for rid in neg.ids if rid not in both]
        # a review that praised and criticised the same aspect counts for neither; it still shows as "mixed"
        rows.append(
            {
                "id": aspect.id,
                "label": aspect.label,
                "praise": aspect.praise,
                "complaint": aspect.complaint,
                "kind": aspect.kind,
                "problem_only": aspect.problem_only,
                "positive": _side_out(positive_ids, pos, policy),
                "negative": _side_out(negative_ids, neg, policy),
                "mixed_reviews": len(both),
                "denied_reviews": len(denied_ids[aspect.id]),
                "excluded_praise": {"low_star": pos.low_star, "not_used_yet": pos.no_experience},
            }
        )
    rows.sort(key=lambda row: (-max(row["positive"]["reviews"], row["negative"]["reviews"]), row["id"]))
    return {
        "version": ASPECT_RULES_VERSION,
        "profile": profiles.profile_key(category, group),
        "reviews_considered": considered,
        "product_reviews": len(product_reviews),
        "service_reviews": len(service_reviews),
        "not_used_yet_reviews": no_experience_reviews,
        "skipped_clauses": excluded,
        "aspects": rows,
    }


def _side_out(ids: list[str], side: _Side, policy: dict[str, Any]) -> dict[str, Any]:
    keep = set(ids)
    quotes = [quote for quote in side.quotes if quote["review_id"] in keep]
    return {
        "reviews": len(ids),
        "review_ids": ids[: policy["ids_per_side"]],
        "ids_truncated": len(ids) > policy["ids_per_side"],
        "quotes": quotes[: policy["quotes_per_side"]],
    }


# --- caching: aspect extraction is the only costly step, and a saved product's reviews do not change ----------------
_CACHE: "OrderedDict[tuple[Any, ...], dict[str, Any]]" = OrderedDict()
_CACHE_SIZE = 256


def _signature(comments: Sequence[dict[str, Any]]) -> str:
    digest = hashlib.sha1()
    for review in comments or []:
        if isinstance(review, dict):
            digest.update(f"{review.get('comment_id')}|{review.get('rating')}|{review.get('is_duplicate')}|{review.get('included_in_analysis')}|{review.get('content')}".encode("utf-8", "ignore"))
    return digest.hexdigest()


def cached_extract(link: str, comments: Sequence[dict[str, Any]], category: str | None, group: str | None) -> dict[str, Any]:
    """`extract`, remembered per product. The key holds a digest of the reviews, so edited reviews are read again."""
    key = (link, category, group, ASPECT_RULES_VERSION, len(comments or []), _signature(comments))
    hit = _CACHE.get(key)
    if hit is not None:
        _CACHE.move_to_end(key)
        return hit
    result = extract(comments, category, group)
    _CACHE[key] = result
    while len(_CACHE) > _CACHE_SIZE:
        _CACHE.popitem(last=False)
    return result


def clear_cache() -> None:
    _CACHE.clear()


# --- evidence wording -----------------------------------------------------------------------------------------------
def tier_word(count: int, usable: int | None = None) -> str:
    """"one", "some", "several", "many" or "most" for a number of DISTINCT reviews. "Most" needs a majority of a real sample."""
    policy = EVIDENCE_POLICY
    if usable and count >= policy["most_min_reviews"] and count / usable >= policy["most_share"]:
        return "most"
    word = "one"
    for floor, name in policy["tiers"]:
        if count >= floor:
            word = name
    return word


def iter_claims(result: dict[str, Any]) -> Iterable[tuple[dict[str, Any], str, dict[str, Any]]]:
    for row in result.get("aspects", []):
        for polarity in ("positive", "negative"):
            if row[polarity]["reviews"]:
                yield row, polarity, row[polarity]
