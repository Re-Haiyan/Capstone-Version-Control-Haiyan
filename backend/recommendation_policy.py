"""Recommendation decisions: the policy that runs today, reproduced exactly, and an EXPERIMENTAL candidate beside it.

NOTHING HERE IS WIRED INTO THE LIVE CARD. dashboard_utils._conclusion still makes every decision. This module exists so that
the two policies can be run on the same products and compared (research/product_specific_conclusions/
recommendation_policy_compare.py) and so that the candidate, if the team adopts it, is a tested function and not a rewrite.

The five decision values are the existing ones: recommended, mixed, caution, not_recommended, not_enough. No new value.

THE POLICY THAT RUNS TODAY (current_decision). Reproduced from dashboard_utils._conclusion and checked against it by
tests/test_recommendation_policy.py on every saved product and on a grid of share and state combinations:
  insufficient_evidence                                    -> not_enough
  safety_warning                                           -> not_recommended          (never lowered by sentiment)
  possible_safety_issue / possible_counterfeit_or_defect   -> not_recommended if positive share < 50%, else caution
  reviews_may_be_unreliable                                -> caution
  no_warning_signs                                         -> recommended if positive >= 75% and its lower bound >= 65%,
                                                              mixed if positive >= 50%, else not_recommended
The weak point: every "else" above looks at the POSITIVE share only. 45% positive / 20% neutral / 35% negative, and 25%
positive / 65% neutral / 10% negative, both fall under "positive < 50%" and become not_recommended.

THE CANDIDATE (candidate_decision), from the proposed principles, NOT validated thresholds:
  - the hazard overrides are unchanged: safety_warning stays not_recommended; unreliable stays caution; insufficient stays not_enough;
  - "negative dominates" replaces "positive < 50%": the negative share is a majority, or at least NEG_DOMINANT and larger than
    the positive share. Only then is a product not_recommended;
  - with a hazard concern (possible safety issue, possible fake or defect): not_recommended when negative dominates or a third
    or more of the reviews are negative; otherwise caution. The concern stays on the card either way, and the product is not
    called "not recommended" merely because most reviews were neutral. (A first draft used "dominates" alone; the comparison
    showed it would soften a product with 8 defect reports and 41% negative reviews, so the hazard rule was tightened.)
  - with no warning, if positive and negative together are under OPINION_MIN of the reviews, nobody said enough to conclude:
    not_enough (the wording of that card would need to say "too few clear opinions", not "too few reviews");
  - otherwise mixed (or recommended, unchanged).
NEG_DOMINANT and OPINION_MIN are round numbers chosen to be easy to argue about. No shopper outcome or human judgement was used.
The comparison shows how many products move for other values, so nobody has to take these on trust.
"""

from __future__ import annotations

from typing import Any

# The thresholds of the live policy. They are re-stated here and checked against dashboard_utils by a test, so they cannot drift apart.
RECOMMEND_SHARE = 0.75
RECOMMEND_BOUND = 0.65
MIXED_SHARE = 0.50

# The candidate's thresholds (experimental).
NEG_DOMINANT = 0.35
NEG_MAJORITY = 0.50
OPINION_MIN = 0.30

HAZARD_CONCERN_STATES = ("possible_safety_issue", "possible_counterfeit_or_defect")


def current_decision(state: str, shares: dict[str, float] | None, lower_bound: float = 0.0) -> str | None:
    """The decision dashboard_utils._conclusion makes today, or None where it makes none (no warning and no sentiment)."""
    positive = shares["positive"] if shares else None
    if state == "insufficient_evidence":
        return "not_enough"
    if state == "safety_warning":
        return "not_recommended"
    if state in HAZARD_CONCERN_STATES:
        return "not_recommended" if positive is not None and positive < MIXED_SHARE else "caution"
    if state == "reviews_may_be_unreliable":
        return "caution"
    if state != "no_warning_signs" or positive is None:
        return None
    if positive >= RECOMMEND_SHARE and lower_bound >= RECOMMEND_BOUND:
        return "recommended"
    if positive >= MIXED_SHARE:
        return "mixed"
    return "not_recommended"


def negative_dominates(shares: dict[str, float]) -> bool:
    positive, negative = shares["positive"], shares["negative"]
    return negative > NEG_MAJORITY or (negative >= NEG_DOMINANT and negative > positive)


def candidate_decision(state: str, shares: dict[str, float] | None, lower_bound: float = 0.0) -> tuple[str | None, str]:
    """(decision, the rule that decided it) under the experimental candidate policy."""
    if state == "insufficient_evidence":
        return "not_enough", "too few reliable reviews"
    if state == "safety_warning":
        return "not_recommended", "safety warning (override, unchanged)"
    if state == "reviews_may_be_unreliable":
        return "caution", "reviews may be unreliable (unchanged)"
    if shares is None:
        return current_decision(state, shares, lower_bound), "no sentiment: unchanged"
    if state in HAZARD_CONCERN_STATES:
        # A hazard concern is not softened when a third or more of the reviews are negative, even if the positive share is a little higher.
        if negative_dominates(shares) or shares["negative"] >= NEG_DOMINANT:
            return "not_recommended", "hazard concern and a third or more of reviews are negative"
        return "caution", "hazard concern, fewer than a third of reviews are negative"
    if state != "no_warning_signs":
        return current_decision(state, shares, lower_bound), "unchanged"
    if shares["positive"] >= RECOMMEND_SHARE and lower_bound >= RECOMMEND_BOUND:
        return "recommended", "strongly positive with enough reviews (unchanged)"
    if negative_dominates(shares):
        return "not_recommended", "negative reviews dominate"
    if shares["positive"] + shares["negative"] < OPINION_MIN:
        return "not_enough", "too few clear opinions (most reviews neutral or unclear)"
    return "mixed", "neither positive nor negative reviews dominate"


def explain(old: str | None, new: str | None, shares: dict[str, float] | None) -> str:
    """One plain sentence for a changed decision."""
    if shares is None or old == new:
        return ""
    pos, neu, neg = (round(shares[k] * 100) for k in ("positive", "uncertain", "negative"))
    return f"{old} -> {new}: {pos}% positive, {neu}% neutral or unclear, {neg}% negative."
