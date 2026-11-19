"""Narrow clause meanings for concern detectors; never changes sentiment.

Full-clause matches are deliberate: an added fault, limitation, negation or
mixed complaint must make these rules abstain. Other clauses remain independent.
"""
from __future__ import annotations

import re

REVISION = "fan-concern-context-2"
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
    # Sentence splitting retains the conjunction on the second clause.
    success_text = re.sub(r'^(?:but|pero|kaso)\s+', '', text, flags=re.I)
    if label == "defect" and _SUCCESS.fullmatch(success_text):
        return "explicit successful power-bank operation, not a malfunction"
    if label == "quality" and _QUIET.fullmatch(text):
        return "explicit quiet operation or strong airflow with denied noise, not poor output"
    return None


def phrase_reason(category: str | None, label: str, text: str,
                  span: tuple[int, int], review_context: str | None = None) -> str | None:
    """Interpret one matched cue, never erase other cues in a mixed sentence.

    Category and local grammatical subject matter. A neighborhood outage is
    not missing power at the motor; low consumption is not weak airflow. The
    caller retains the original text and this reason for inspection/export.
    """
    if category != "small_appliance":
        return None
    start, end = span
    while start < end and text[start] in " \t.,;:":
        start += 1
    while end > start and text[end - 1] in " \t.,;:":
        end -= 1
    phrase = text[start:end]

    def cue(pattern: str) -> bool:
        return any(m.start('cue') <= start and end <= m.end('cue')
                   for m in re.finditer(pattern, text, re.I))

    if label == 'not_as_described':
        if re.fullmatch(r'(?:only\s+\d+(?:\.\d+)?\s*w(?:atts?)?|\d+(?:\.\d+)?\s*w(?:atts?)?\s+lang)', phrase):
            # A contrast can be split into adjacent sentences/clauses by the
            # normalizer. Keep the original review context for rating claims.
            context = review_context or text
            ratings = {float(n) for n in re.findall(r'\b(\d+(?:\.\d+)?)\s*w(?:atts?)?\b', context, re.I)}
            disputed = len(ratings) > 1 and re.search(
                r'\b(?:advertis\w*|promis\w*|claim\w*|description|listing|nakalagay|dapat|supposed|instead|imbes|mislead\w*|rated|ordered|order|inorder|nakasulat|labelled|labeled|says?|said|hindi|not)\b', context, re.I)
            if not disputed:
                return 'ordinary operating wattage; no advertised-versus-received rating is asserted'
        if cue(r'\bmas\s+mahal\s+(?:\w+\s+){0,3}sa\s+(?P<cue>ibang\s+same\s+product)\b'):
            return 'price comparison with other products, not a different item received'
        if cue(r'\bkahapon\s+(?P<cue>kulang\s+na\s+order)\s+received\s+na\s+agad\b'):
            return 'abstain: ambiguous order-timing wording does not establish a missing-item claim'
    if label == 'quality':
        if cue(r'\b(?P<cue>mahina)\s+(?:(?:din|rin|sya|siya|lang|ang)\s+){0,4}(?:kumain\s+ng\s+charge|(?:consume|konsumo)\s+ng\s+kuryente)\b'):
            return 'low electricity or battery consumption, not weak airflow'
        if cue(r'\b(?:kala|akala)\s+ko\s+(?P<cue>mahina)\s+lang\s+malakas\s+pala\b'):
            return 'earlier expectation of weak airflow explicitly retracted by actual strong airflow'
        if cue(r'\bsa\s+(?P<cue>mumurahin)\s+ko\s+na\s+power\s*bank\b'):
            return 'cheap describes the external power bank, not the reviewed appliance'
    if label == 'defect':
        if cue(r'\b(?:dito\s+sa\s+)?(?:lugarnmin|lugar\s+namin|neighbou?rhood)\s+(?:laging\s+|has\s+)?(?P<cue>walang\s+power|no\s+power)\b'):
            return 'power outage in the reviewer location, not loss of power inside the appliance'
        if cue(r'\bquiet\s*:\s*(?:(?:it|the|fan|makes|almost)\s+){0,5}(?P<cue>no\s+sound)\b'):
            return 'explicit quiet-operation field, not missing audio output'
        if cue(r'\bnot\s+sure\s+if\s+(?:it\s+|it\s+is\s+|its\s+)?(?P<cue>defective)\b'):
            return 'abstain: reviewer speculates about a defect; assess the stated operating complaint separately'
    return None
