"""Rules s3: false safety alarms, and heat in spellings the rules miss (18 Oct 2026).

The candidate of research/PREREGISTRATION_round20.md, written from the
training rounds (1-16, 18 and 19) and checked part by part
(research/check_round20_rules.py). A safety flag is removed only when every
hazard word of the sentence lies inside a look-alike; a real report written
beside one keeps its flag.

    feature        a protection feature, not an event: "Overheat protection
                   included", "prevent overheating", "short circuit protection"
    denial         a denial with words between: "without any noticeable
                   overheating", "d tulad ng ibng charger na umiinit"
    weather        the weather, the room or the season: "init ng Pilipinas",
                   "tag-init", "ibilad sa init"
    idiom          "mainit ang ulo", "uminit ulo ko" (not "ulo ng charger")
    other_meaning  "ng lobo" (a balloon), "maga- sound", "spark of", a "burnt"
                   colour, burnt food, "sumabog yung amoy"
    fragile        "delikado" with a breaking or handling word and no other
                   hazard: "delikado sya mabagsak", "delikado ipagamit sa bata"
    other_device   the reviewer's own phone or adapter, or a previous unit:
                   "uminit ng iphone adapter ko", "yung una ko kasi lumobo"
    comfort        warmth on the ear with a comfort reason and no failure
    spelling       (adds a flag) "over heated", "maiinit", "became unusually
                   hot"

S3_OFF names parts switched off, for the part-by-part check only.

Rules s4 (19 Oct 2026; research/PREREGISTRATION_round23.md) add one part, read
only when s3_removes is asked for it (hazard_model.S4_RULES_OFF):

    previous       a previous unit in English, beside a swelling, heat, fire or
                   explosion word: "the first I have just have a bloated
                   battery", "my old one exploded"; not "the first time", "the
                   other day", nor with "also", "too" or "this one"
"""

import re

S3_REVISION = "s3"
S3_OFF: set[str] = set()
HAZARD = re.compile(
    r"(?<![a-z])(?:hot|heat\w*|overheat\w*|over[\s-]*(?:heat|hit)\w*|burn\w*|burnt|fire|flame\w*|smok\w*|spark\w*|shock\w*|"
    r"electrocut\w*|grounded|ground|melt\w*|explod\w*|explosion|combust\w*|bloat\w*|swell\w*|swollen|short[\s-]?circuit|hazard\w*|danger\w*|"
    r"init|mainit|uminit|umiinit|iinit|nainit|naiinit|maiinit|napakainit|nag-?\s?iinit|nag-?\s?init|nangangainit|mag\s?init|"
    r"usok|umusok|umuusok|nausok|umosok|sunog|nasunog|masunog|nagsunog|apoy|umapoy|kuryente|nakuryente|kinuryente|"
    r"tunaw|natunaw|sumabog|sasabog|sumasabog|pumutok|putok|lumobo|lumolobo|lobo|maga|namaga|umbok|delikado\w*)(?![a-z])",
    re.I,
)
_HEAT = r"(?:overheat\w*|over[\s-]*(?:heat|hit)\w*|heat\w*|hot|init|mainit|uminit|umiinit|iinit|nainit|naiinit|nag-?\s?iinit|nag-?\s?init|mag\s?init|nangangainit)"
_FILL = (r"(?:naman|nman|nmn|po|sya|siya|xa|cya|ganun|ganon|gaano|masyado|masyadong|madaling|madali|mabilis|basta|agad|so|that|very|"
         r"any|noticeable|noticed|experienced|experience|felt|feel|detect\w*|nag|ng|yung|ung|the|a|an|ko|ako|akong|maramdamang|"
         r"maramdaman|at|ever|even|really|talaga|totally|or|mag|issues?|problems?|nagka|nagkaroon|parin|pa|rin|din|man|lang|lng|po\.?)")
PARTS = {
    "feature": [
        re.compile(r"(?:overheat\w*|over[\s-]?heat\w*|short[\s-]?circuit|over[\s-]?(?:voltage|current|charg\w*)|thermal|temperature|heat)"
                   r"(?:\s*[,/&]\s*(?:and\s+)?(?:overheat\w*|short[\s-]?circuit|over[\s-]?(?:voltage|current|charg\w*)))*"
                   r"(?:\s+(?:and|&)\s+(?:overheat\w*|short[\s-]?circuit|over[\s-]?(?:voltage|current|charg\w*)))?"
                   r"\s+(?:protection|protect\w*|prevention|guard|resistan\w*|proof|control|dissipation|sink|management)", re.I),
        re.compile(r"(?:prevent\w*|avoid\w*|against|protect\w*\s+(?:from|against)|guards?\s+against|peace\s+of\s+mind\s+against|"
                   r"(?:no|without)\s+(?:risk\s+of\s+)?)\s+(?:[\w-]+\s+){0,3}?(?:overheat\w*|over[\s-]?heat\w*|short[\s-]?circuit\w*|over[\s-]?charg\w*)", re.I),
        re.compile(r"flame[\s-]?retardant|fire[\s-]?(?:proof|resistant|retardant)|explosion[\s-]?proof|anti[\s-]?explosion", re.I),
    ],
    "denial": [
        re.compile(rf"(?<![a-z])(?:no|not|never|without|walang|wala|hindi|hinde|hnd|di|dipo|d|haven'?t|hasn'?t|didn'?t|doesn'?t|don'?t|isn'?t|wasn'?t|wont|won'?t)"
                   rf"\s+(?:{_FILL}\s+){{0,4}}{_HEAT}", re.I),
        re.compile(rf"(?<![a-z])(?:hindi|di|d|not|unlike|unlike\s+other)\s+(?:tulad|katulad|gaya|kagaya|like)?\s*(?:ng|nung|sa|of)?\s*"
                   rf"(?:ibang|ibng|other|iba|previous|dati)\s+(?:[\w']+\s+){{0,3}}(?:na\s+|that\s+)?{_HEAT}", re.I),
    ],
    "weather": [
        re.compile(rf"{_HEAT}\s+(?:na\s+)?(?:ng|nung|ngayong|ngayon|sa|of|in|dito|po\s+dito)?\s*(?:po\s+)?(?:panahon|weather|summer|tag-?\s?init|pilipinas|philippines|"
                   rf"araw|tanghali|room|kwarto|bahay|tindahan|bukid|labas|outside|season|klima|climate|maghapon|dito)", re.I),
        re.compile(r"tag-?\s?init|(?:ibilad|ebilad|bilad)\s+sa\s+init|init\s+na\s+init\s+ako|(?:kapag|pag)\s+mainit(?:\s+talaga)?(?=\W*$|\W*\.\.)", re.I),
        re.compile(rf"(?:room|kwarto|bahay|tindahan|bukid|dito|outside|labas)\s+(?:[\w']+\s+){{0,4}}(?:kasi|kc|dahil|because|sa)\s+(?:sobrang|super|ang|napaka)?\s*{_HEAT}"
                   rf"|(?:sobrang|super|ang)\s+{_HEAT}\s+(?:dw\s+|daw\s+)?(?:po\s+)?(?:kc\s+|kasi\s+)?sa\s+(?:room|kwarto|bahay|labas|dito)", re.I),
        re.compile(rf"(?:nung|noong)\s+(?:super|sobrang)\s+{_HEAT}\s+\(?\s*(?:saktong\s+)?(?:tanghali|summer|araw)", re.I),
    ],
    "idiom": [
        re.compile(r"(?:init\w*|mainit|uminit|iinit|nag-?iinit)\s+(?:talaga\s+|na\s+|pa\s+)?(?:ang\s+|yung\s+|ung\s+)?ulo(?!\s+(?:ng|nung|of)\s)(?=\W|$|\s+(?:ko|q|mo|nyo|namin|natin|sa|kaysa|kesa|ni))", re.I),
        re.compile(r"(?:init|inet)\s+ng\s+ulo\s+(?:ko|q|mo|nyo|namin)", re.I),
    ],
    "other_meaning": [
        re.compile(r"(?:ng|sana\s+ng|pang|ang)\s+lobo(?!\s*(?:battery|batt|na\s+battery))|lobo\s+ng\s+(?:mga\s+)?(?:floater|salbabida|balloon)", re.I),
        re.compile(r"\bmaga[-\s]+(?:sound|da\b|nda)", re.I),
        re.compile(r"spark\s+(?:of|joy)|tecno\s+spark|spark\s+\d+", re.I),
        re.compile(r"burnt\s+(?:orange|sienna|umber|ang\s+order|shade|color)|(?:tan|shade|color|kulay)\s+(?:\w+\s+){0,2}burnt|burn\s+(?:alkaline|slimming|coffee)|fat\s+burn\w*", re.I),
        re.compile(r"(?:lasang\s+)?sunog\s+(?:na\s+)?(?:sunog\s+)?(?:\w+\s+){0,2}?(?:parchment|steak|pork\w*|meat|rice|kanin|pagkain|ulam)(?![a-z])|lasang\s+sunog|pagkain\s+sunog", re.I),
        re.compile(r"sumabog\s+(?:agad\s+)?(?:yung\s+|ang\s+)?(?:amoy|bango|scent|smell)", re.I),
        # s5: a grounded plug is a three-pin plug, not a shock: "grounded po ang cord", "grounded yung lightning pin"
        re.compile(r"grounded\s+(?:po\s+|naman\s+|na\s+)?(?:ang\s+|yung\s+|ung\s+)?(?:cord|plug|wire|outlet|socket|extension|pin|lightning|usb)"
                   r"|(?:cord|plug|wire|outlet|socket)\s+(?:is\s+|are\s+|po\s+)?grounded", re.I),
    ],
    "fragile": [
        re.compile(r"delikado\w*(?=(?:\W+\w+){0,8}?\W+(?:mabagsak|bagsak|masira|masisira|nasisira|maipit|matabig|maligwak|balot|bubble|buble|packaging|cartoon|carton|bata|kids?|wire))"
                   r"|(?:packaging|balot|wire)\W+(?:\w+\W+){0,4}?delikado\w*", re.I),
    ],
    "other_device": [
        re.compile(rf"(?:adapter|adaptor|charger|cp|phone|iphone|celfon|cellphone|fon|laptop)\s+(?:ko|q|namin)\s+(?:[\w']+\s+){{0,3}}?{_HEAT}"
                   rf"|{_HEAT}\s+(?:[\w']+\s+){{0,2}}?(?:ng\s+|yung\s+|ung\s+)?(?:iphone\s+)?(?:adapter|adaptor|charger|cp|phone|celfon|fon)\s+(?:ko|q)", re.I),
        re.compile(rf"(?:heats?\s+up|overheat\w*|hot)\s+my\s+(?:phone|iphone|laptop)|my\s+(?:phone|iphone)\s+(?:\w+\s+){{0,3}}(?:hot|heat\w*)", re.I),
        re.compile(r"(?:iphone|phone|celfon|cellphone|cp)\s+stops\s+charging\s+when\s+it'?s\s+too\s+hot", re.I),
        re.compile(rf"{_HEAT}\s+(?:pa\s+|pang\s+)?(?:ang|yung|ung)\s+(?:celfon|cellphone|cp|phone)\s+(?:kesa|kaysa|than)", re.I),
        re.compile(r"(?:my|ko|q)\s+(?:[\w']+\s+){0,2}(?:cellphone|phone|iphone|cp)\s+(?:\w+\s+){0,2}(?:gets|got|becomes?|is|was)\s+(?:so\s+|very\s+|too\s+)?hot", re.I),
        re.compile(r"(?:yung\s+|ung\s+)?(?:una|dati|previous|old|last)\s+(?:ko\s+|kong\s+)?(?:[\w']+\s+){0,3}?(?:lumobo|swell\w*|burn\w*|nasunog|sumabog)", re.I),
        re.compile(r"(?:palitan|replace)\s+(?:[\w']+\s+){0,6}?(?:lumobo|swollen|swell\w*)", re.I),
    ],
    "comfort": [
        re.compile(rf"{_HEAT}\s+(?:[\w']+\s+){{0,2}}sa\s+(?:tenga|tainga|taynga|tinga|ears?|leeg|neck|ulo)", re.I),
        re.compile(rf"(?:comfortable|comportable|komportable)\s+sa\s+(?:tenga|tainga|tinga)\s+(?:[\w']+\s+){{0,2}}{_HEAT}", re.I),
    ],
}
COMFORT_WORD = re.compile(r"(?<![a-z])(?:comfortable|comportable|komportable|masakit|sakit|foam|cushion|makapal|matagal\s+(?:ginagamit|gamitin|suot|isuot)|pag\s+matagal|long\s+(?:use|hours))(?![a-z])", re.I)
ITEM = re.compile(r"(?<![a-z])(?:powerbank|power\s*bank|charger|adapter|adaptor|cable|cord|plug|item|unit|earbuds?|headset|speaker)(?![a-z])(?!\s+(?:ko|q|namin)(?![a-z]))", re.I)
FAILURE = re.compile(r"(?<![a-z])(?:sira|ayaw|di\s+na\s+(?:gagana|gumana)|hindi\s+na\s+gumana|not\s+working|stops?|namatay|namamatay|charg\w*|nagcha\w*)(?![a-z])", re.I)
SPELLING = [
    re.compile(r"(?<![a-z])(?:nag\s*o+\s*)?over\s+(?:heat|hit)\w*", re.I),
    re.compile(r"(?<![a-z])(?:maiinit|nangangainit|nangainit)(?![a-z])", re.I),
    re.compile(r"(?<![a-z])(?:became|becomes|become|gets|got|getting|went|goes|turned|turns)\s+(?:(?!not\b)\w+\s+){0,2}hot(?![a-z])", re.I),
    # s5 (appended, so the numbers above are unchanged): fire, melting, a swelling battery, a misspelt short circuit
    re.compile(r"(?<![a-z])(?:ignit\w*|caught|catch(?:es|ing)?|causes?|caused|causing)\s+(?:a\s+|an\s+|the\s+)?fire(?![a-z])|(?<![a-z])nag-?\s?liyab", re.I),
    re.compile(r"(?<![a-z])(?:wires?|cables?|cords?|plug|prongs?|charger|adapter|adaptor|casing)(?:\s+(?!(?:not|no|never|won'?t|wouldn'?t|doesn'?t|don'?t|didn'?t|can'?t|cannot|hindi|di|walang)(?![\w']))[\w']+){0,5}?\s+(?:also\s+)?(?:melt(?:s|ed|ing)?|natunaw|tumunaw)(?![a-z])"
               r"|(?<![a-z])melt(?:s|ed|ing)?\s+(?:the\s+|my\s+|its\s+)?(?:wires?|cables?|cords?|plug|prongs?|charger|adapter|adaptor)(?![a-z])", re.I),
    re.compile(r"(?<![a-z])batter(?:y|ies)\s+(?:[\w']+\s+){0,7}?(?:bloat\w*|swell\w*|swollen)(?![a-z])"
               r"|(?<![a-z])(?:bloated|swollen|swelling)\s+(?:[\w']+\s+)?batter(?:y|ies)", re.I),
    re.compile(r"(?<![a-z])(?:shrt|shotr|shor|shot)[\s-]?circuit|(?<![a-z])short[\s-]?(?:sirkit|sircuit)|(?<![a-z])shortcircuit", re.I),
]
S5_REVISION = "s5"
S4_REVISION = "s4"
PREVIOUS_UNIT = re.compile(
    r"(?<![a-z])(?:the|my|our)\s+(?:very\s+)?(?:first|previous|old|older|last|former)"
    r"(?!\s+(?:time|times|day|days|night|nights|week|weeks|month|months|hour|hours|minute|minutes|use|uses|usage|charge|"
    r"charging|try|few|couple|moment|second|seconds)(?![a-z]))"
    rf"(?:\s+[\w']+){{0,6}}?\s+(?:{_HEAT}|bloat\w*|swell\w*|swollen|explod\w*|burn\w*|burnt|fire|melt\w*|smok\w*|lumobo|sumabog|nasunog)(?![a-z])",
    re.I,
)
THIS_ONE_TOO = re.compile(
    r"(?<![a-z])(?:also|too|again|as\s+well|same|both|rin|din|ulit|this\s+(?:one|unit|item|pair|time)|the\s+(?:new|second|replacement)|"
    r"(?:new|second|2nd|replacement)\s+(?:one|unit|item|pair))(?![a-z])",
    re.I,
)
NEGATED_BEFORE = re.compile(r"(?<![a-z])(?:no|not|never|without|walang|wala|hindi|di|d|haven'?t|didn'?t|doesn'?t|don'?t|won'?t|wouldn'?t|can'?t|cannot|sana|baka|might|hope)\s+(?:\w+\s+){0,3}$", re.I)


def s3_removes(raw: str, previous: bool = False) -> set[str]:
    """The parts that read every hazard word of the sentence as a look-alike; empty when any stays a report.
    previous adds rules s4's part."""
    text = " ".join(str(raw).split())
    hazards = [m.span() for m in HAZARD.finditer(text)]
    if not hazards:
        return set()
    spans, used = [], set()
    for part, patterns in PARTS.items():
        if part in S3_OFF or part == "fragile":
            continue
        for p in patterns:
            for m in p.finditer(text):
                spans.append((m.start(), m.end(), part))
    if FAILURE.search(text) or not COMFORT_WORD.search(text):
        spans = [s for s in spans if s[2] != "comfort"]
    if ITEM.search(text):
        spans = [s for s in spans if s[2] != "other_device" or re.search(r"lumobo|swell|burn|nasunog|sumabog|una|dati|previous|old", text[s[0]:s[1]], re.I)]
    if previous and not THIS_ONE_TOO.search(text):
        for m in PREVIOUS_UNIT.finditer(text):
            spans.append((m.start(), m.end(), "previous"))
    if "fragile" not in S3_OFF:
        others = [h for h in hazards if not re.match(r"delikado", text[h[0]:h[1]], re.I)]
        if all(any(s <= a and b <= e for s, e, _ in spans) for a, b in others):
            for m in PARTS["fragile"][0].finditer(text):
                spans.append((m.start(), m.end(), "fragile"))
    for a, b in hazards:
        covering = [part for s, e, part in spans if s <= a and b <= e]
        if not covering:
            return set()
        used.add(covering[0])
    return used


def s3_adds(raw: str) -> str | None:
    """The spelling part that finds heat the word list misses, unless a look-alike explains it."""
    if "spelling" in S3_OFF:
        return None
    text = " ".join(str(raw).split())
    spans = [m.span() for part in ("feature", "denial", "other_device", "weather", "idiom") for p in PARTS[part] for m in p.finditer(text)]
    for n, p in enumerate(SPELLING):
        m = p.search(text)
        if m and not NEGATED_BEFORE.search(text[: m.start()]) and not any(s <= m.start() and m.end() <= e for s, e in spans):
            return f"spelling:{n}"
    return None
