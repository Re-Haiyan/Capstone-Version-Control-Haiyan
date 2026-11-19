"""Narrow clause meanings for concern detectors; never changes sentiment.

Full-clause matches are deliberate: an added fault, limitation, negation or
mixed complaint must make these rules abstain. Other clauses remain independent.
"""
from __future__ import annotations

import re

REVISION = "fan-concern-context-1"
_BANK = r"power\s*bank"
_SUCCESS = re.compile(
    rf"(?:"
    rf"(?:gumagana|gagana|umaandar|umandar)(?:\s+(?:nga|naman|po|rin|din|na|magdamag|ko|ginamit|sya|siya|ito)){{0,8}}\s+(?:sa|s|on)\s+(?:isang\s+)?{_BANK}"
    rf"|(?:(?:it|the fan)\s+)?(?:works?|runs?|operates?)(?:\s+(?:normally|well|fine|overnight)){{0,2}}\s+(?:on|with|using)\s+(?:(?:a|the)\s+)?{_BANK}"
    rf"|(?:kasi|dahil)\s+{_BANK}\s+lang\s+gagana\s+na"
    rf")", re.I,
)
_QUIET = re.compile(
    r"(?:"
    r"(?:malakas\s+(?:(?:ang|yung|ung)\s+)?hangin\s+at\s+)?(?:hindi|di)\s+(?:(?:po|naman|sya|siya)\s+){0,2}maingay"
    r"|(?:strong\s+air\s*flow\s+and\s+)?(?:(?:it|the fan)\s+is\s+)?not\s+noisy"
    r"|(?:(?:it|the fan)\s+)?(?:runs?|operates?)\s+quietly"
    r")", re.I,
)


def operation_reason(category: str | None, label: str, normalized: str) -> str | None:
    """Explain only an explicit whole clause in the relevant appliance category.

    This never inspects stars, initial sentiment, model confidence or whether
    evidence is model-only. It interprets specific operation/noise wording.
    """
    if category != "small_appliance":
        return None
    text = normalized.strip(" \t\r\n.!?,;")
    if label == "defect" and _SUCCESS.fullmatch(text):
        return "explicit successful power-bank operation, not a malfunction"
    if label == "quality" and _QUIET.fullmatch(text):
        return "explicit quiet operation or strong airflow with denied noise, not poor output"
    return None
