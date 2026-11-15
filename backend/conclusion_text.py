"""The words of the Product Conclusion card, built only from claims that can be traced to reviews.

The DECISION (recommended / mixed / caution / not_recommended / not_enough) is made by dashboard_utils._conclusion from
the hazard verdict and the sentiment shares, and is never changed here. This module decides what the card SAYS about
that decision, and it says only what is supported:

  * the mood is described from the real positive, neutral and negative shares, never inferred from one of them;
  * a praised or criticised feature is named only when distinct reviews support it (aspects.py), and the wording
    carries how many ("one reviewer", "some", "several", "many", "most"), never more than the evidence allows;
  * safety, authenticity and defect reports come from the existing hazard checker and are worded as what reviewers
    REPORT: nothing here says a product is safe, unsafe, genuine or counterfeit;
  * delivery, packaging and seller comments never make a product "well reviewed"; when they are all there is, the
    card says the product itself is barely described;
  * with no usable review text, nothing about features is said at all.
"""

from __future__ import annotations

from typing import Any

import aspects as asp
from aspect_profiles import EVIDENCE_POLICY, PRODUCT, SERVICE, TRUST

RECOMMEND_SHARE = 0.75  # kept equal to dashboard_utils.CONCLUSION_RECOMMEND_SHARE; passed in so there is one source


def and_list(items: list[str]) -> str:
    items = [item for item in items if item]
    if len(items) <= 1:
        return "".join(items)
    if len(items) == 2:
        return f"{items[0]} and {items[1]}"
    return ", ".join(items[:-1]) + f" and {items[-1]}"


def reviews(count: int) -> str:
    return "1 review" if count == 1 else f"{count} reviews"


def _capital(text: str) -> str:
    return text[:1].upper() + text[1:]


# --- the mood, from the real shares -------------------------------------------------------------------------------------
def percents(shares: dict[str, float] | None) -> tuple[int, int, int] | None:
    """Positive, neutral-or-unclear and negative as whole percentages that add up to 100."""
    if not shares:
        return None
    raw = [shares.get("positive", 0.0) * 100, shares.get("uncertain", 0.0) * 100, shares.get("negative", 0.0) * 100]
    floors = [int(value) for value in raw]
    order = sorted(range(3), key=lambda i: raw[i] - floors[i], reverse=True)
    for i in order[: 100 - sum(floors)]:
        floors[i] += 1
    return floors[0], floors[1], floors[2]


def mood_sentence(shares: dict[str, float] | None, usable: int) -> str:
    """One accurate sentence about the sentiment. It names the largest group and never calls a minority a majority."""
    split = percents(shares)
    if split is None:
        return "The reviews could not be summarized as positive or negative."
    pos, neu, neg = split
    if neu >= 50:
        return (
            f"Approximately {pos}% of the analyzed sentiment was positive and {neg}% negative; "
            f"most reviews ({neu}%) were neutral or did not express a clear opinion."
        )
    if neg > 50:
        return f"About {neg}% of the {usable} reviews were negative, {pos}% positive and {neu}% neutral or unclear."
    if pos >= 50:
        return f"About {pos}% of the {usable} reviews were positive, {neu}% neutral or unclear and {neg}% negative."
    return f"Opinions were spread out: {pos}% positive, {neu}% neutral or unclear and {neg}% negative."


def feeling(shares: dict[str, float] | None, recommend_share: float = RECOMMEND_SHARE) -> str | None:
    """A word for the mood that the shares actually justify, or None when no word is honest."""
    split = percents(shares)
    if split is None:
        return None
    pos, neu, neg = split
    if pos / 100 >= recommend_share:
        return "predominantly positive"
    if neg > 50:
        return "mostly negative"
    if neu >= 50:
        return "mostly neutral or unclear"
    if pos >= 50:
        return "leaning positive"
    return "mixed"


# --- what the aspects say ----------------------------------------------------------------------------------------------
def _split(result: dict[str, Any]) -> dict[str, list[dict[str, Any]]]:
    """Praised, criticised, contested and unresolved aspects, from distinct-review counts."""
    policy = EVIDENCE_POLICY
    out: dict[str, list[dict[str, Any]]] = {"praised": [], "criticised": [], "contested": [], "trust": [], "service": []}
    for row in result.get("aspects", []):
        pos, neg = row["positive"]["reviews"], row["negative"]["reviews"]
        if row["kind"] == SERVICE:
            out["service"].append(row)
            continue
        if row["kind"] == TRUST:
            out["trust"].append(row)
            continue
        low, high = min(pos, neg), max(pos, neg)
        if low >= policy["contested_min_reviews"] and low >= policy["contested_ratio"] * high:
            out["contested"].append(row)
        elif pos > neg:
            out["praised"].append(row)
        elif neg > pos:
            out["criticised"].append(row)
        # equal and small: neither side is stated; the card's evidence list still shows both counts
    out["praised"].sort(key=lambda r: (-r["positive"]["reviews"], r["id"]))
    out["criticised"].sort(key=lambda r: (-r["negative"]["reviews"], r["id"]))
    return out


def _tiers(rows: list[dict[str, Any]], side: str, usable: int) -> list[tuple[str, list[dict[str, Any]]]]:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        grouped.setdefault(asp.tier_word(row[side]["reviews"], usable), []).append(row)
    rank = ["most", "many", "several", "some", "one"]
    return [(word, grouped[word]) for word in rank if word in grouped]


def _subject(word: str) -> str:
    return "One reviewer" if word == "one" else f"{_capital(word)} reviewers"


def _short_subject(word: str) -> str:
    return "one" if word == "one" else word


def _complaint_phrase(rows: list[dict[str, Any]]) -> str:
    """"problems with battery life and display, and dryness": labels that need "problems with" share one, the rest stand alone."""
    labels = [row["label"] for row in rows if row["complaint"] == f"problems with {row['label']}"]
    plain = [row["complaint"] for row in rows if row["complaint"] != f"problems with {row['label']}"]
    return and_list(([f"problems with {and_list(labels)}"] if labels else []) + plain)


def _reasons(concerns: list[str], blamed: list[dict[str, Any]]) -> list[str]:
    """The reasons for a warning in the headline: the hazard checker's concerns first, then the criticised features
    under a single "problems with ..." so the phrase is not repeated.

    Found by the quality audit: "defects" (the hazard checker) and "faults or failure to work" (an aspect) say the same thing, and a
    headline that lists both, then adds more, reads as a list and not as a sentence. So the aspect is dropped when "defects" is
    already named, and the headline never names more than three reasons in all."""
    if "defects" in concerns:
        blamed = [row for row in blamed if row["id"] != "functionality"]
    named = concerns[:3]
    room = 3 - len(named)
    return named + ([_complaint_phrase(blamed[:room])] if blamed and room > 0 else [])


def _chain(parts: list[str]) -> str:
    """", several mentioned X and some mentioned Y": later tiers follow the first, with "and" only before the last."""
    if not parts:
        return ""
    return ", " + ", ".join(parts[:-1]) + (", and " if len(parts) > 1 else "") + parts[-1]


def praise_sentence(rows: list[dict[str, Any]], usable: int, limit: int) -> str:
    rows = rows[:limit]
    tiers = _tiers(rows, "positive", usable)
    if not tiers:
        return ""
    first_word, first_rows = tiers[0]
    rest = [f"{_short_subject(word)} mentioned {and_list([r['label'] for r in group])}" for word, group in tiers[1:]]
    return f"{_subject(first_word)} praised {and_list([r['label'] for r in first_rows])}{_chain(rest)}."


def complaint_sentence(rows: list[dict[str, Any]], usable: int, limit: int) -> str:
    rows = rows[:limit]
    tiers = _tiers(rows, "negative", usable)
    if not tiers:
        return ""
    first_word, first_rows = tiers[0]
    rest = [f"{_short_subject(word)} mentioned {_complaint_phrase(group)}" for word, group in tiers[1:]]
    return f"{_subject(first_word)} reported {_complaint_phrase(first_rows)}{_chain(rest)}."


def contested_sentence(rows: list[dict[str, Any]]) -> str:
    if not rows:
        return ""
    row = rows[0]
    pos, neg = row["positive"]["reviews"], row["negative"]["reviews"]
    return f"Reviewers disagree about {row['label']}: {reviews(pos)} praised it and {reviews(neg)} criticised it."


def _mainly(rows: list[dict[str, Any]], side: str, named: int) -> bool:
    total = sum(r[side]["reviews"] for r in rows)
    top = sum(r[side]["reviews"] for r in rows[:named])
    return total > 0 and top / total >= EVIDENCE_POLICY["mainly_share"]


# --- hazards, as reported ------------------------------------------------------------------------------------------------
def hazard_sentences(mentions: dict[str, int], state: str, hazards: str) -> list[str]:
    out: list[str] = []
    safety = mentions.get("safety", 0)
    if safety:
        out.append(
            f"{'One review describes' if safety == 1 else f'{safety} reviews describe'} a possible safety problem ({hazards}). "
            f"{'This report has' if safety == 1 else 'These reports have'} not been independently verified; read {'it' if safety == 1 else 'them'} first."
        )
    fake = mentions.get("counterfeit", 0)
    if fake:
        out.append(f"{'One review questions' if fake == 1 else f'{fake} reviews question'} whether the product is genuine.")
    return out


def _concern_phrases(mentions: dict[str, int]) -> list[str]:
    safety, fake, defect = (mentions.get(name, 0) for name in ("safety", "counterfeit", "defect"))
    out = []
    if safety:
        out.append("possible safety problems")
    if defect:
        out.append("defects")
    if fake:
        out.append("doubts about authenticity")
    return out


# --- the card -------------------------------------------------------------------------------------------------------------
# The balanced last sentence. It interprets; it never adds a fact (every fact is in a counted sentence above it).
CLOSING = {
    "recommended": "Overall, feedback is favorable, although individual experiences vary.",
    "mixed": "Because experiences differ, it is worth reading the complaints before you decide.",
    "caution": "Read the reported problems before you decide.",
    "not_recommended": "Buyers may want to read the complaints and compare alternatives before deciding.",
    "not_enough": "",
}


def evidence_status(result: dict[str, Any] | None) -> str:
    """"unavailable" (no usable review text), "limited" (reviews barely describe the product) or "supported"."""
    if not result or not result.get("reviews_considered"):
        return "unavailable"
    policy = EVIDENCE_POLICY
    considered = result["reviews_considered"]
    if result["product_reviews"] < policy["limited_min_reviews"] or result["product_reviews"] / considered < policy["limited_min_share"]:
        return "limited"
    return "supported"


def why_items(result: dict[str, Any], usable: int) -> list[dict[str, Any]]:
    """The expandable "Why this conclusion?" list: every line is a count that can be reproduced from the reviews."""
    items: list[dict[str, Any]] = []
    for row in result.get("aspects", []):
        for side, polarity in (("positive", "positive"), ("negative", "negative")):
            data = row[side]
            if not data["reviews"]:
                continue
            name = row["label"] if polarity == "positive" else row["complaint"]
            text = f"{_capital(name)}: {reviews(data['reviews'])} {'supporting' if polarity == 'positive' else 'concerning'}"
            items.append(
                {
                    "aspect": row["id"],
                    "kind": row["kind"],
                    "polarity": polarity,
                    "reviews": data["reviews"],
                    "text": text,
                    "quotes": data["quotes"],
                    "review_ids": data["review_ids"],
                    "ids_truncated": data["ids_truncated"],
                }
            )
    rank = {PRODUCT: 0, TRUST: 1, SERVICE: 2}
    items.sort(key=lambda i: (rank[i["kind"]], i["polarity"] != "positive", -i["reviews"], i["aspect"]))
    return items


def compose(
    *,
    decision: str,
    state: str,
    usable: int,
    shares: dict[str, float] | None,
    mentions: dict[str, int],
    result: dict[str, Any] | None,
    noun: str,
    hazards: str,
    recommend_share: float = RECOMMEND_SHARE,
) -> dict[str, Any] | None:
    """The lead, the paragraph and the evidence for one product, or None when the reviews have no usable text."""
    status = evidence_status(result)
    if status == "unavailable" or result is None:
        return None
    policy = EVIDENCE_POLICY
    considered = result["reviews_considered"]
    split = _split(result)
    praised = [r for r in split["praised"] if r["positive"]["reviews"] >= 1]
    lead_praise = [r for r in praised if r["positive"]["reviews"] >= policy["lead_min_reviews"]][: policy["lead_max_aspects"]]
    criticised = split["criticised"]
    lead_blame = [r for r in criticised if r["negative"]["reviews"] >= policy["lead_min_reviews"]][: policy["lead_max_aspects"]]
    concerns = _concern_phrases(mentions)
    happy = bool(shares) and shares["positive"] >= recommend_share
    thing = f"this {noun}"

    # Every headline begins "Based on customer reviews" and says only what the counts allow: "generally well received" needs the
    # decision to be `recommended`; a feature is named only with the evidence policy's minimum; "most" is never used here.
    if decision == "not_enough":
        lead = f"Based on customer reviews, there are too few to say whether {thing} is worth buying."
    elif status == "limited":
        lead = _limited_lead(decision, thing, result, concerns)
    elif decision == "recommended":
        if lead_praise:
            how = "mainly " if _mainly(praised, "positive", len(lead_praise)) else ""
            lead = f"Based on customer reviews, {thing} is generally well received, {how}for {and_list([r['label'] for r in lead_praise])}."
        else:
            lead = f"Based on customer reviews, {thing} is generally well received, with no single feature standing out."
    elif decision == "mixed":
        if lead_praise and (lead_blame or concerns or split["contested"]):
            blame = and_list(_reasons(concerns, lead_blame) or [split["contested"][0]["label"] + " (reviewers disagree)"])
            lead = f"Based on customer reviews, opinions on {thing} are mixed: some praise {and_list([r['label'] for r in lead_praise])}, while the reviews also report {blame}."
        else:
            lead = f"Based on customer reviews, opinions on {thing} are mixed, with no single feature standing out."
    elif decision == "caution":
        reasons = _reasons(concerns, lead_blame)
        # No quantity word here ("some reviewers"): a concern with one report would be overstated, and the counts are in the
        # warnings and in "Why this conclusion?". "Include reports of" says only that they are in the reviews.
        if reasons:
            tail = f"the reviews include reports of {and_list(reasons)}"
        elif split["contested"]:
            tail = f"reviewers disagree about {split['contested'][0]['label']}"
        else:
            tail = "concerns were reported"
        reasons = reasons or [tail]
        if lead_praise and happy and reasons:
            lead = f"Based on customer reviews, {thing} is praised for {and_list([r['label'] for r in lead_praise])}, but {tail}."
        elif happy:
            lead = f"Based on customer reviews, {thing} has favorable feedback, but {tail}."
        else:
            lead = f"Based on customer reviews, think twice about {thing}: {tail}."
    else:  # not_recommended
        reasons = _reasons(concerns, lead_blame)
        if reasons:
            lead = f"Based on customer reviews, {thing} raises concerns: the reviews include reports of {and_list(reasons)}."
        else:
            lead = f"Based on customer reviews, {thing} drew few positive reviews."

    # Each sentence has a priority. When the card would run past the word budget (it has to read on a phone), the lowest
    # priorities go first; the hazard and mood sentences never do. Everything dropped is still in "Why this conclusion?".
    parts: list[tuple[int, str]] = []
    limit = policy["text_max_aspects"]

    def add(priority: int, text: str) -> None:
        if text:
            parts.append((priority, text))

    if status == "supported" or praised:
        add(5, praise_sentence(praised, considered, limit))
    add(6, complaint_sentence(criticised, considered, limit))
    add(2, contested_sentence(split["contested"]))
    warnings = hazard_sentences(mentions, state, hazards)
    for sentence in warnings:
        add(9, sentence)
    trust = [r for r in split["trust"] if r["positive"]["reviews"] >= policy["lead_min_reviews"] and not r["negative"]["reviews"]]
    if trust and not mentions.get("counterfeit"):
        add(1, f"{_subject(asp.tier_word(trust[0]['positive']['reviews'], considered))} described it as genuine.")
    if criticised and all(r["negative"]["reviews"] == 1 for r in criticised[:limit]) and not concerns:
        add(3, "These complaints were isolated reports.")
    if status == "limited" and decision != "not_enough":
        add(6, _limited_detail(result))
    # With too few reviews no percentage is shown (the team's rule for this card): a share of three reviews is not a finding.
    add(9, f"Only {reviews(usable)} could be analyzed." if decision == "not_enough" else mood_sentence(shares, usable))
    add(4, CLOSING.get(decision, ""))
    while len(lead.split()) + sum(len(text.split()) for _, text in parts) > policy["target_words"]:
        droppable = [part for part in parts if part[0] < 9]
        if not droppable:
            break
        parts.remove(min(droppable, key=lambda part: part[0]))
    paragraph = " ".join(text for _, text in parts)
    # `summary` keeps every sentence, warnings included (older readers show only that). `body` is the same without the warnings, and
    # `warnings` are the hazard sentences on their own, so the card can set them apart and never fold them into a collapsed section.
    body = " ".join(text for _, text in parts if text not in warnings)

    note = "Limited product-specific feedback." if status == "limited" else None
    return {
        "lead": lead,
        "summary": paragraph,
        "body": body,
        "warnings": list(warnings),
        "assessment_note": note,
        "evidence_status": status,
    }


def _service_names(result: dict[str, Any]) -> list[str]:
    return [r["label"] for r in result["aspects"] if r["kind"] == SERVICE and (r["positive"]["reviews"] or r["negative"]["reviews"])]


def _limited_lead(decision: str, thing: str, result: dict[str, Any], concerns: list[str]) -> str:
    """The headline when the reviews barely describe the product itself. The decision value is the existing one; the words
    qualify it. "Most reviews discuss delivery" is said only when delivery, packaging or seller reviews really are a majority."""
    service = _service_names(result)
    about = and_list(service[:2])
    focus = ""
    if service and result["service_reviews"] > result["product_reviews"]:
        word = asp.tier_word(result["service_reviews"], result["reviews_considered"])
        focus = f"{'one review discusses' if word == 'one' else f'{word} reviews discuss'} {about} rather than how {thing} performs"
    if decision == "recommended":
        if focus:
            return f"Although customer feedback is generally positive, {focus}."
        return f"Based on customer reviews, feedback on {thing} is favorable, but there is limited evidence about how it performs."
    if decision == "mixed":
        tail = focus or "there is limited evidence about how it performs"
        return f"Based on customer reviews, opinions on {thing} are mixed, and {tail}."
    if decision in ("caution", "not_recommended") and concerns:
        opener = f"think twice about {thing}" if decision == "caution" else f"{thing} raises concerns"
        return f"Based on customer reviews, {opener}: the reviews include reports of {and_list(concerns[:3])}, and few reviews describe how it performs."
    if focus:
        return f"Based on customer reviews, {focus}."
    return f"Based on customer reviews, few reviews describe how {thing} performs, so the feedback says little about the product itself."


def _limited_detail(result: dict[str, Any]) -> str:
    service = [r for r in result["aspects"] if r["kind"] == SERVICE and r["positive"]["reviews"] > r["negative"]["reviews"]]
    if service:
        names = and_list([r["label"] for r in service[:2]])
        return f"Feedback on {names} is positive, but there is not enough product-specific evidence to describe how it performs."
    return "There is not enough product-specific evidence to describe how it performs."
