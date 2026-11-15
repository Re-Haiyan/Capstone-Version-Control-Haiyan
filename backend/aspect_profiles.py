"""What shoppers talk about, by kind of product: the data behind the product-specific conclusion.

Everything the extractor (aspects.py) knows about a product type lives here, as data, so a new product type or a
new aspect is a table entry and not new code. Nothing in this file says a product HAS a quality; an aspect is only
a list of words reviewers use when they praise or criticise it. A claim reaches a shopper only when real review
text contains those words (see aspects.py for how a clause is read).

Reading the tables
- An aspect has `pos` and `neg` phrases (regular expressions over the lower-cased, normalised clause), an optional
  `topic` (words that name it without judging it) and a `kind`:
    product  what the product does or is: used in the headline and the praise and complaint sentences.
    trust    is it genuine: shown, but never counted as a benefit of the product.
    service  delivery, packaging, seller: counted only to tell "reviews talk about the product" from "reviews talk
             about the parcel". It never makes a product "recommended".
- `problem_only` aspects (dryness, itching, overheating ...) have no praise side: a reviewer who writes "hindi
  nakakadry" has denied a problem, which is not a benefit anyone reported.
- Profiles are looked up by the listing's product category (product_category.py), then its group, then GENERAL.
  A profile lists only the aspects that are specific to it; the GENERAL aspects are always added behind them, and a
  profile aspect with the same id replaces the general one.
- Phrases are written for English, Filipino and Taglish together, with the common short spellings. They were
  written from the saved review pool and the team's rules, not trained, so each one can be read and argued with.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field, replace
from typing import Iterable

ASPECT_RULES_VERSION = "asp3"  # bump when a table or the reading rules change; cached results are keyed on it

# ---------------------------------------------------------------------------------------------------------------
# How much evidence a sentence needs. These are policy, not statistics: no outcome of shoppers was used to set
# them (see research/product_specific_conclusions/README.md, "Evidence policy"). The reviews analysed are a
# star-stratified sample of what a product has, so none of these words speaks for ALL its buyers.
EVIDENCE_POLICY = {
    # (smallest number of distinct reviews, wording). The first row that fits from the bottom up is used.
    "tiers": ((1, "one"), (2, "some"), (4, "several"), (10, "many")),
    # "most reviewers" needs at least this share of the analysed reviews AND this many reviews: never from a handful.
    "most_share": 0.5,
    "most_min_reviews": 10,
    # An aspect is named in the headline only when this many different reviews support it.
    "lead_min_reviews": 2,
    # ... and at most this many aspects, so the headline stays a sentence and not a list.
    "lead_max_aspects": 2,
    # The lead and the paragraph together stay near this many words so the card reads on a phone. Lower-priority
    # sentences are dropped to fit; safety and sentiment sentences never are. (The panel asked for about 55-100.)
    "target_words": 100,
    "text_max_aspects": 3,
    # "mainly" is used only when the aspects named hold at least this share of all praise (or all complaints).
    "mainly_share": 0.6,
    # Praise and complaint about the same aspect are "contested" when the smaller side has at least this many reviews
    # and at least this fraction of the larger side.
    "contested_min_reviews": 2,
    "contested_ratio": 0.4,
    # Product evidence is "limited" when fewer than this many different reviews say anything about the product
    # itself (or fewer than this share of the analysed reviews do).
    "limited_min_reviews": 3,
    "limited_min_share": 0.05,
    # Reviews rated this low or lower that PRAISE something are not counted: a star rating that contradicts the
    # words is often sarcasm or a different order. They stay visible as excluded evidence.
    "contradiction_max_stars": 2,
    # Reading limits, so one rambling or keyword-stuffed review cannot cost seconds: a review is read up to this many characters
    # (longer ones are counted as truncated), and a clause longer than the second number is cut into pieces.
    "max_review_chars": 5000,
    "max_clause_chars": 600,
    # Longest quotation kept per aspect and side, and how many quotations travel with the conclusion.
    "quote_chars": 160,
    "quotes_per_side": 2,
    "ids_per_side": 40,
}

PRODUCT, TRUST, SERVICE = "product", "trust", "service"


@dataclass(frozen=True)
class Aspect:
    id: str
    label: str  # the noun phrase used after "praised the ..." and "problems with ..."
    pos: tuple[re.Pattern[str], ...] = ()
    neg: tuple[re.Pattern[str], ...] = ()
    topic: tuple[re.Pattern[str], ...] = ()
    kind: str = PRODUCT
    problem_only: bool = False
    problem: str = ""  # the noun phrase for a complaint when "problems with <label>" would be wrong
    denial_is_positive: bool = False  # "hindi naman fake": denying the problem IS the statement (authenticity only)
    neg_guard: re.Pattern[str] | None = None  # a clause matching this is not read as a complaint about this aspect
    sentence_pos: str = ""  # optional wording after "praised": defaults to "the <label>"
    skip_if: re.Pattern[str] | None = None  # a clause matching this says nothing about this aspect, praise or complaint ("their website was user-friendly")
    quick: re.Pattern[str] | None = field(default=None, compare=False, repr=False)  # any cue at all: one search to reject a clause

    def __post_init__(self) -> None:
        parts = [pattern.pattern for pattern in self.pos + self.neg]
        object.__setattr__(self, "quick", re.compile("|".join(f"(?:{part})" for part in parts), re.I) if parts else None)

    @property
    def complaint(self) -> str:
        return self.problem or f"problems with {self.label}"

    @property
    def praise(self) -> str:
        return self.sentence_pos or f"the {self.label}"


def _re(parts: Iterable[str]) -> tuple[re.Pattern[str], ...]:
    return tuple(re.compile(part, re.I) for part in parts)


# Small helpers so a table says "good + sound" and not forty hand-written alternations.
_GAP = r"(?:\s+(?:ang|na|ng|nang|sa|po|nya|niya|nito|ay|is|are|was|very|so|sobrang|talaga|naman|masyadong?|really|super|yung|yong|ko|my|the|a)\b)*\s+"


def pair(adjectives: str, nouns: str) -> list[str]:
    """"<adjective> <noun>" and "<noun> <adjective>", in either order, with the little words Filipino puts between."""
    return [rf"\b(?:{adjectives}){_GAP}(?:{nouns})\b", rf"\b(?:{nouns}){_GAP}(?:{adjectives})\b"]


# --- shared wording -------------------------------------------------------------------------------------------
GOOD = r"maganda|ganda|good|great|excellent|amazing|nice|ok|okay|goods?|solid|best|superb|awesome|astig|swabe|panalo|top|perfect|impressive|sulit"
BAD = r"pangit|panget|bad|poor|terrible|awful|worst|disappointing|mahina|sablay|palpak|mediocre|useless|lousy|bulok"

FRAGRANCE = Aspect(
    "fragrance",
    "fragrance",
    pos=_re(
        [
            r"\b(?:mabango|bango|bangu|mabangu)\b",
            r"\b(?:ganda|sarap|bango|ok|astig|bagay)\s+(?:ng|ang|nang|ng\s+mga)\s+(?:amoy|scent|fragrance|pabango)\b",
            r"\bamoy\s+(?:nya|niya|nito|po|ay|ng\s+\w+)?\s*(?:ay\s+)?(?:maganda|mabango|masarap|ok|okay|sarap|ganda)\b",
            r"\b(?:smells?|smelled)\s+(?:so\s+|very\s+|really\s+)?(?:good|great|nice|amazing|lovely|fresh|heavenly|divine|clean)\b",
            r"\b(?:good|great|nice|lovely|pleasant|sweet|fresh|amazing)\s+(?:scent|smell|fragrance|aroma)\b",
            r"\b(?:scent|fragrance|smell|aroma)\s+(?:is\s+|was\s+)?(?:good|great|nice|lovely|pleasant|sweet|fresh|amazing)\b",
            r"\blove\s+(?:the|its|this)\s+(?:scent|smell|fragrance)\b",
        ]
    ),
    neg=_re(
        [
            r"\b(?:mabaho|baho|nakakasuka)\b",
            r"\b(?:pangit|panget|sangsang|matapang)\s+(?:ng|ang|na|nang)?\s*(?:amoy|scent|fragrance)\b",
            r"\b(?:strong|bad|awful|weird|chemical|artificial|unpleasant|funny|harsh|medicinal)\s+(?:smell|scent|odou?r|fragrance)\b",
            r"\b(?:smells?|smelled)\s+(?:so\s+|very\s+)?(?:bad|awful|weird|funny|off|chemical|terrible|strong)\b",
            r"\bamoy\s+(?:nya|niya|nito|po)?\s*(?:ay\s+)?(?:pangit|panget|matapang|masangsang|kemikal)\b",
        ]
    ),
)

BATTERY_NOUNS = r"battery(?:\s+life)?|baterya|playtime|battery\s+backup|charge\s+hold"
BATTERY = Aspect(
    "battery",
    "battery life",
    pos=_re(
        pair(r"long|good|great|solid|excellent|all[- ]day|matagal|tipid|malakas|ok|okay|goods?|reliable|impressive|maganda|ganda|tumatagal|lasts?", BATTERY_NOUNS)
        + [r"\b(?:tipid|matagal|di\s+agad|hindi\s+agad)\s+(?:sa\s+)?(?:malowbat|lowbat|maubos|ma-?drain)\b", r"\bbattery\s+lasts?\b"]
    ),
    neg=_re(
        pair(r"mahina|weak|poor|bad|short|mabilis|mabilis\s+maubos|terrible|awful|pangit|panget|disappointing|bulok", BATTERY_NOUNS)
        + [
            r"\b(?:battery|baterya)\s+(?:drains?|drained|dies|died|nauubos|nauubusan)\b",
            r"\bdrains?\s+(?:fast|quickly)\b",
            r"\b(?:malowbat|lowbat|nauubos|maubos|nauubusan)\s+(?:agad|na\s+agad|ng\s+battery|ang\s+battery)\b",
            r"\bmabilis\s+(?:malowbat|lowbat|maubos|ma-?drain|maubusan)\b",
        ]
    ),
)

CHARGING_NOUNS = r"charg\w*|pag-?charge|pagcharge"
CHARGING = Aspect(
    "charging",
    "charging",
    pos=_re(
        [
            r"\b(?:fast|mabilis|quick|super\s+fast|good|ok|okay)\s+(?:na\s+)?charg\w*\b",
            r"\bcharg\w*\s+(?:is\s+|was\s+|ay\s+)?(?:fast|mabilis|quick|ok|okay|maayos|good|great)\b",
            r"\bmabilis\s+(?:mag-?charge|ma-?charge|mag\s+charge)\b",
        ]
    ),
    neg=_re(
        [
            r"\b(?:slow|mabagal|bagal)\s+(?:na\s+)?charg\w*\b",
            r"\bcharg\w*\s+(?:is\s+|was\s+|ay\s+)?(?:slow|mabagal|bagal|issue|problem|failure)s?\b",
            r"\b(?:hindi|di|ayaw|d)\s+(?:nag-?|ma-?|na)charg\w*\b",
            r"\bayaw\s+(?:mag-?\s*)?charge\b",
            r"\bcharging\s+(?:issues?|problems?|failures?)\b",
            r"\bwalang\s+charging\b",
            r"\b(?:nag-?|di\s+)stop\s+(?:sa\s+)?charg\w*\b",
        ]
    ),
)

OVERHEATING = Aspect(
    "overheating",
    "overheating",
    neg=_re(
        [
            r"\boverheat\w*\b",
            r"\b(?:umiinit|uminit|nag-?init|naiinit|ininit|sobrang\s+init|ang\s+init|mainit)\b",
            r"\b(?:heats?\s+up|heating\s+up|gets?\s+(?:very\s+|too\s+|really\s+)?hot|getting\s+hot|runs?\s+hot|too\s+hot)\b",
            r"\bnag-?hot\b",
        ]
    ),
    neg_guard=re.compile(r"\b(?:panahon|summer|tag-?init|weather|init\s+ng\s+araw)\b", re.I),
    problem_only=True,
    problem="overheating",
)

SHUTDOWNS = Aspect(
    "shutdowns",
    "unexpected shutdowns",
    neg=_re(
        [
            r"\b(?:nag-?shut\s?down|shuts?\s+(?:down|off)|shut\s+off)\b",
            r"\b(?:biglang|bigla\s+na)\s+(?:namatay|nag-?off|namamatay|nawalan|nawala|nag-?restart)\b",
            r"\b(?:namamatay|namatay|nag-?o-?off|nag-?auto[- ]?off|patay[- ]sindi)\b",
            r"\bturns?\s+off\s+(?:randomly|by\s+itself|suddenly|on\s+its\s+own)\b",
            r"\bnagre-?restart\b|\brestarts?\s+(?:randomly|by\s+itself)\b",
        ]
    ),
    problem_only=True,
    problem="unexpected shutdowns",
)

# --- the general aspects (every product) ------------------------------------------------------------------------
FUNCTIONALITY = Aspect(
    "functionality",
    "how well it works",
    problem="faults or failure to work",
    pos=_re(
        [
            r"\b(?:works?|worked|working)\s+(?:very\s+|so\s+|really\s+)?(?:well|great|perfectly|fine|properly|smoothly|as\s+expected|as\s+described)\b",
            r"\b(?:gumagana|gumana|nagagamit|nagwo-?work|nag-?work)\b",
            r"\b(?:effective|epektib\w*|umepekto|tumalab|nakatulong|nakakatulong)\b",
            r"\b(?:functions?|functional)\s+(?:well|properly|perfectly)\b",
            r"\bmaayos\s+(?:ang\s+)?(?:gamit|takbo|function|pagkakagawa)\b",
        ]
    ),
    neg=_re(
        [
            r"\bwalang\s+(?:epekto|nangyari|pinagbago|difference)\b",
            r"\b(?:no|zero)\s+(?:effect|difference|result|improvement)s?\b",
            r"\b(?:sira|nasira|sirang|defective|palpak|patay|useless|faulty|dead\s+on\s+arrival|doa)\b",
            r"\b(?:ayaw|di|hindi)\s+(?:mag-?)?(?:on|bumukas|umandar|gumana|mag-?start)\b",
            r"\bstopped\s+working\b",
            r"\b(?:isa|one)\s+(?:lang\s+)?(?:side\s+)?(?:lang\s+)?(?:ang\s+)?(?:gumagana|tumutunog|working)\b",
            r"\b(?:left|right)\s+(?:side\s+)?(?:is\s+)?(?:not\s+working|dead|walang\s+tunog)\b",
        ]
    ),
    # A damaged box, seal or wrapper is about the parcel, not about whether the product works.
    neg_guard=re.compile(
        r"\b(?:(?:sira|nasira|yupi|nayupi|punit|butas|basag|nabasag)(?:[- ]sira)*(?:\s+na)?\s+(?:ang\s+|yung\s+|ung\s+)?(?:box|kahon|packag\w*|balot|plastic|seal)"
        r"|packag\w*\s+(?:sira|nasira|yupi))\b",
        re.I,
    ),
)
# A plain "works" is only ever praise; "hindi gumagana" is the same word under a negation, which aspects.py reads
# as a complaint. That is why the praise words are not repeated in the complaint list.

BUILD = Aspect(
    "build",
    "build quality",
    pos=_re(
        [
            r"\b(?:matibay|sturdy|well[- ]made|well[- ]built|de[- ]kalidad|premium|solid\s+(?:na\s+)?(?:build|quality|gawa))\b",
            r"\b(?:good|great|high|nice|excellent|maganda|ganda|ok|okay|superb)\s+(?:na\s+|ang\s+|ng\s+)?(?:quality|build|kalidad|gawa|pagkakagawa|materials?)\b(?!\s+(?:nung\s+|ng\s+|of\s+|ang\s+)?(?:audios?|sound|pictures?|videos?|photos?|camera|calls?|display|screen|mic|voice))",
            r"(?<!sound\s)(?<!audio\s)(?<!photo\s)(?<!video\s)(?<!image\s)(?<!call\s)(?<!camera\s)(?<!picture\s)(?<!print\s)(?<!screen\s)(?<!display\s)(?<!mic\s)(?<!voice\s)\b(?:quality|kalidad|gawa|pagkakagawa|build)\s+(?:is\s+|ay\s+|nya\s+|niya\s+)?(?:good|great|high|nice|excellent|maganda|ganda|ok|okay|solid|superb|premium)\b",
        ]
    ),
    neg=_re(
        [
            r"\b(?:poor|low|bad|cheap|pangit|panget|mababang|mura\s+ang|chinese|so-?so)\s+(?:na\s+|ang\s+|ng\s+)?(?:quality|build|kalidad|gawa|pagkakagawa|materials?)\b(?!\s+(?:nung\s+|ng\s+|of\s+|ang\s+)?(?:audios?|sound|pictures?|videos?|photos?|camera|calls?|display|screen|mic|voice))",
            r"(?<!sound\s)(?<!audio\s)(?<!photo\s)(?<!video\s)(?<!image\s)(?<!call\s)(?<!camera\s)(?<!picture\s)(?<!print\s)(?<!screen\s)(?<!display\s)(?<!mic\s)(?<!voice\s)\b(?:quality|kalidad|gawa|pagkakagawa|build)\s+(?:is\s+|ay\s+|nya\s+|niya\s+)?(?:poor|low|bad|cheap|pangit|panget|mababa|mura|flimsy)\b",
            r"\b(?:flimsy|cheaply\s+made|cheap[- ]looking|plasticky|nagluluwag|marupok|babasagin)\b",
        ]
    ),
)

DURABILITY = Aspect(
    "durability",
    "durability",
    pos=_re(
        [
            r"\b(?:tumagal|nagtagal|tumatagal|long[- ]lasting|lasts?\s+(?:long|well|for\s+(?:months|years))|durable|matibay\s+talaga|hindi\s+agad\s+(?:nasira|masira)|di\s+agad\s+(?:nasira|masira))\b(?!\s+(?:na\s+)?(?:battery|baterya|charge|fragrance|scent|smell|amoy|bango|pabango))",
        ]
    ),
    neg=_re(
        [
            r"\b(?:agad|madaling|easily|mabilis)\s+(?:nasira|masira|nasisira|bumigay|nabasag|nagkasira|nag-?crack|na-?crack|nabali|nalaglag)\b",
            r"\b(?:nasira|sira|bumigay|nabasag|nabali|stopped\s+working|broke|broken|nag-?crack)\s+(?:agad|na\s+agad|after|pagkatapos|within|in\s+(?:\d+|a\s+few|one|two|three))\b",
            r"\b(?:after|pagkatapos(?:\s+ng)?|within)\s+(?:\d+|a\s+few|ilang|one|two|three|isang|1|2|3)\s+(?:days?|weeks?|months?|araw|linggo|buwan|uses?|washes?|gamit)\b[^.!?]{0,30}\b(?:nasira|sira|broke|broken|stopped|bumigay|nabasag|nag-?crack|natastas|kumupas|nabutas|natanggal)\b",
            r"\b(?:short|maikli)\s+(?:lifespan|buhay)\b",
            r"\bdi\s+nagtagal\b",
        ]
    ),
)

SIZE = Aspect(
    "size",
    "size",
    pos=_re(
        [
            r"\b(?:tamang|perfect|right|saktong|sakto|swak|ideal)\s+(?:na\s+)?(?:ang\s+)?(?:size|sukat|laki)\b",
            r"\b(?:size|sukat|laki)\s+(?:is\s+|ay\s+|nya\s+)?(?:perfect|just\s+right|tama|sakto|swak|accurate|ideal)\b",
            r"\btrue\s+to\s+size\b",
        ]
    ),
    neg=_re(
        [
            r"\b(?:masyadong?|too|sobrang|so)\s+(?:liit|maliit|malaki|big|small|large|tiny|bulky|heavy|mabigat)\b",
            r"\b(?:wrong|mali\s+ang)\s+size\b",
            r"\bsize\s+(?:is\s+|was\s+)?(?:off|small|big|mali|not\s+accurate|hindi\s+accurate)\b",
            r"\b(?:maliit|malaki)\s+(?:ang|na|ng)\s+(?:size|sukat)\b",
        ]
    ),
)

APPEARANCE = Aspect(
    "appearance",
    "looks",
    pos=_re(
        [
            r"\b(?:maganda|ganda|nice|good|great|beautiful|cute|stylish|sleek|pretty|elegant|premium|aesthetic|astig|lovely|gorgeous)\s+(?:ang\s+|na\s+|ng\s+)?(?:design|kulay|color|colou?r|itsura|looks?|dating|finish|packaging\s+design)\b",
            r"\b(?:design|kulay|color|colou?r|itsura|finish)\s+(?:is\s+|ay\s+|nya\s+|niya\s+)?(?:maganda|ganda|nice|beautiful|cute|stylish|sleek|pretty|elegant|premium|astig|lovely|gorgeous|great)\b",
            r"\b(?:looks?|looked)\s+(?:so\s+|very\s+|really\s+)?(?:great|good|nice|premium|elegant|beautiful|cute|expensive|stylish)\b",
            r"\bang\s+cute\b|\bastig\s+ng\s+(?:design|itsura|dating)\b",
        ]
    ),
    neg=_re(
        [
            r"\b(?:pangit|panget|ugly|ordinary|plain|cheap[- ]looking)\s+(?:ang\s+|na\s+|ng\s+)?(?:design|kulay|color|colou?r|itsura|looks?|dating|finish)\b",
            r"\b(?:design|kulay|color|colou?r|itsura|finish)\s+(?:is\s+|ay\s+|nya\s+)?(?:pangit|panget|ugly|dull|faded|plain|cheap)\b",
            r"\b(?:kumupas|nag-?fade|faded|fades)\b",
            r"\b(?:iba|different)\s+(?:ang\s+)?(?:kulay|color|colou?r)\b",
        ]
    ),
)

VALUE = Aspect(
    "value",
    "value for money",
    pos=_re(
        [
            r"\b(?:sulit|worth\s+(?:it|the\s+(?:price|money|buy)|every\s+(?:peso|penny|centavo)|buying)|value\s+for\s+money|affordable|budget[- ]friendly|bang\s+for\s+(?:the\s+)?buck|good\s+price|sulit\s+na\s+sulit)\b",
            r"\b(?:ok|okay|maganda|ganda|tama|swak)\s+(?:ang\s+|na\s+)?(?:presyo|price)\b",
            r"\bmura\s+(?:pero|but|yet|at)\s+(?:maganda|ganda|good|quality|okay|ok|matibay)\b",
        ]
    ),
    neg=_re(
        [
            r"\b(?:overpriced|sayang\s+(?:ang\s+)?(?:pera|bayad|bili)|waste\s+of\s+(?:money|time)|nasayang\s+(?:ang\s+)?pera)\b",
            r"\b(?:hindi|di|d|not)\s+(?:worth|sulit)\b",
            r"\b(?:sobrang|ang|too)\s+(?:mahal|expensive)\b",
            r"\bmahal\s+(?:masyado|para\s+sa|for\s+(?:what|the))\b",
        ]
    ),
)

AUTHENTICITY = Aspect(
    "authenticity",
    "authenticity",
    pos=_re(
        [
            r"\b(?:orig(?:inal)?|authentic|genuine)\b(?!\s+(?:price|packaging|box|receipt|na\s+presyo|colou?r|kulay|size|version|model))",
            # "legit" is a claim about the item only: not an intensifier ("legit na fast") and not about the seller or store.
            r"(?<!na\s)(?<!nga\s)\b(?:legit|legitimate)\b(?!\s+(?:na|nga|talaga|seller|shop|store|tindahan|delivery|shipping|rider|buyer|ang\s+(?:seller|shop|store)))",
        ]
    ),
    neg=_re(
        [
            r"\b(?:fake|peke|pekeng|counterfeit|knock[- ]?off|replica|imitation|class\s?a|kopya|copycat)\b",
        ]
    ),
    kind=TRUST,
    denial_is_positive=True,
    problem="doubts about its authenticity",
)

DELIVERY_NOUNS = r"deliver(?:y|ies)|pag-?deliver|na-?deliver|shipping|shipment|pagdating|rider|courier"
DELIVERY = Aspect(
    "delivery",
    "delivery",
    pos=_re(
        pair(r"fast|mabilis|quick|early|on[- ]time|ontime|speedy|maaga|prompt|swift|good|great|nice|maganda|ok|okay|maayos|smooth|excellent", DELIVERY_NOUNS)
        + [r"\b(?:dumating|arrived|nakarating)\s+(?:agad|early|on\s+time|ng\s+maaga|ng\s+mabilis|ahead|next\s+day)\b"]
    ),
    neg=_re(
        pair(r"late|slow|bagal|mabagal|matagal|delayed?|natagalan|poor|bad|pangit|panget|terrible", DELIVERY_NOUNS)
        + [r"\b(?:natagalan|naantala|delayed)\b", r"\b(?:hindi|di)\s+pa\s+dumating\b", r"\bnever\s+arrived\b", r"\bnawala\s+ang\s+(?:parcel|package|item|order)\b"]
    ),
    topic=_re([r"\b(?:deliver\w*|shipping|shipment|rider|courier|dumating|arrived|lbc|j&t|jnt|ninja\s?van|spx)\b"]),
    kind=SERVICE,
)

PACKAGING_NOUNS = r"packag\w*|packing|pagkabalot|pagkakabalot|balot|kahon|box|bubble\s?wrap|wrapping"
PACKAGING = Aspect(
    "packaging",
    "packaging",
    pos=_re(
        pair(r"well|maayos|secure|securely|neat|neatly|maganda|ganda|good|great|nice|sealed|safe|intact|protected|maingat|excellent|ok|okay|tight|mahigpit", PACKAGING_NOUNS)
        + [r"\bwell[- ](?:packed|wrapped|sealed|protected)\b", r"\b(?:maayos|maingat)\s+(?:na\s+)?(?:nakabalot|binalot)\b", r"\bnakabalot\s+(?:ng\s+)?(?:maayos|mabuti|maganda)\b"]
    ),
    neg=_re(
        pair(r"damaged|yupi|nayupi|crushed|butas|punit|nabasag|sira|nasira|bukas|opened|torn|basa|leaked|tagas|poor|pangit|panget|basag|dented|crumpled|kalat|gusot|manipis", PACKAGING_NOUNS)
        + [r"\b(?:poorly|badly)\s+(?:packed|packaged|wrapped)\b", r"\bwalang\s+(?:bubble\s?wrap|balot|protection)\b"]
    ),
    topic=_re([r"\b(?:packag\w*|packing|balot|nakabalot|kahon|box|bubble\s?wrap|wrapp\w*)\b"]),
    kind=SERVICE,
)

SELLER = Aspect(
    "seller",
    "seller service",
    pos=_re(
        [
            r"(?<!user-)(?<!user )\b(?:responsive|accommodating|friendly|helpful|mabait|maasikaso|trusted|nag-?reply|replied|sumagot|legit\s+seller|recommended\s+seller|thank\s*you\s+seller|salamat\s+seller|(?:good|great|ok|okay|best)\s+seller|mabilis\s+(?:mag-?reply|sumagot|mag-?respond))\b",
        ]
    ),
    neg=_re(
        [
            r"\b(?:rude|unresponsive|scammer|bastos|ignored|no\s+response)\b",
            r"\b(?:walang|di|hindi)\s+(?:nag-?reply|sumasagot|reply|response|sagot)\b",
            r"\bayaw\s+(?:mag-?refund|i-?refund|mag-?replace)\b",
        ]
    ),
    topic=_re([r"\b(?:seller|shop|store|tindahan|tindera|customer\s+service|refund\w*|replace\w*)\b"]),
    kind=SERVICE,
)

# --- additions from reading REAL reviews --------------------------------------------------------------------------------
# Round 1 was written after reading the DEVELOPMENT half of the project's own scans (products whose link hashes to an even number).
# Round 2 (the oiliness/dry-hair/"not as X as"/frizz/negation-scope and the skin, label and website fixes) came from reading claims
# and examples drawn from the HELD-OUT half, so that half is no longer untouched; see research/product_specific_conclusions/
# aspect_validation.md for exactly which measurement was taken before and which after.
# `_more` adds cues to an aspect without touching the original table above.
def _more(aspect: Aspect, pos: Iterable[str] = (), neg: Iterable[str] = (), guard: str | None = None, skip_if: str | None = None) -> Aspect:
    return replace(
        aspect,
        pos=aspect.pos + _re(pos),
        neg=aspect.neg + _re(neg),
        # A guard added later JOINS the aspect's own guard; it never replaces it (a replaced guard let "non greasy" through).
        neg_guard=(re.compile(f"(?:{aspect.neg_guard.pattern})|(?:{guard})", re.I) if aspect.neg_guard is not None else re.compile(guard, re.I)) if guard else aspect.neg_guard,
        skip_if=(re.compile(f"(?:{aspect.skip_if.pattern})|(?:{skip_if})", re.I) if aspect.skip_if is not None else re.compile(skip_if, re.I)) if skip_if else aspect.skip_if,
    )


_FRAG = r"fr[ae]gn?[ae]n?ce|fragarance|frangrance|fragnance|fragrence|fregnance"
FRAGRANCE = _more(
    FRAGRANCE,
    pos=[
        rf"\b(?:good|great|nice|lovely|pleasant|sweet|fresh|amazing|wonderful|subtle)\s+(?:{_FRAG}|pabango)\b",
        rf"\b(?:{_FRAG})\s*(?::\s*)?(?:is\s+|ay\s+)?(?:good|great|nice|lovely|ok|okay|subtle|amazing)\b",
        r"\b(?:smell|scent|amoy)\s+(?:is\s+|was\s+|ay\s+)?(?:so|very|really)\s+(?:good|great|nice|lovely|amazing|pleasant)\b",
    ],
)
FUNCTIONALITY = _more(
    FUNCTIONALITY,
    pos=[r"\bworks?\s+as\s+(?:it\s+should|intended|expected|described|advertised)\b", r"\b(?:all\s+)?function(?:s)?\s+(?:naman|well|properly)\b"],
    # "It doesn't work", "not working": found missing when a test sentence did not match.
    neg=[
        r"\b(?:doesn'?t|does\s+not|didn'?t|did\s+not|isn'?t|is\s+not|wasn'?t|was\s+not|won'?t|will\s+not|never|cannot|can'?t|not)\s+(?:even\s+|properly\s+|really\s+|anymore\s+)?(?:work|working|function|functioning)\b",
        r"\b(?:stopped|stop)\s+working\b",
    ],
)
BUILD = _more(
    BUILD,
    pos=[r"\b(?:good|great|nice|excellent|maganda|ganda|ok|okay|superb)\s+(?:ung|yung|yong)\s+(?:quality|kalidad|gawa)\b"],
    neg=[r"\b(?:poor|low|bad|pangit|panget|cheap)\s+(?:ung|yung|yong)\s+(?:quality|kalidad)\b"],
)
SIZE = _more(
    SIZE,
    # "ang laki ng tipid" / "laki ng sayang" are not about size, so only "liit" and "malaki pala" are read as a size complaint.
    neg=[r"\bang\s+liit\s+(?:pala|nung|ng|po)\b", r"\bmaliit\s+(?:pala|po|lang|sya|siya)\b", r"\bmalaki\s+pala\b"],
)
# "Fake ang promo" is a complaint about the promotion, not about the product.
AUTHENTICITY = _more(AUTHENTICITY, guard=r"\bfake\s+(?:ang\s+)?(?:promo|freebie|voucher|discount|review|reviews|rating|ratings|ad|sale|price|picture|pic|photo)\b")

EASE = Aspect(
    "ease",
    "ease of use",
    pos=_re([r"\beasy\s+to\s+(?:use|clean|operate|control|apply|assemble)\b", r"\buser[- ]friendly\b", r"\b(?:madaling|dali)\s+(?:lang\s+)?(?:gamitin|linisin|i-?apply)\b"]),
    neg=_re([r"\b(?:hard|difficult)\s+to\s+(?:use|clean|operate|apply|assemble)\b", r"\bmahirap\s+(?:gamitin|linisin|i-?apply)\b", r"\bcomplicated\b"]),
    # "Their website was user-friendly": the shop's website or app, not the product.
    skip_if=re.compile(r"\b(?:website|web\s?site|site|app|application|platform|checkout|lazada\s+app|shop\s+page)\b", re.I),
)
MATCHES_LISTING = Aspect(
    "matches_listing",
    "match with the listing",
    problem="items that differ from the listing",
    pos=_re(
        [
            r"\b(?:same|exactly)\s+as\s+(?:in\s+)?(?:the\s+)?(?:picture|pictures|photo|photos|pic|pics|advertised|described|listed|description|listing|ad)\b",
            r"\bas\s+(?:described|advertised|pictured|listed)\b",  # not "as shown": "as shown in the video, they covered the barcode" is a complaint
            r"\b(?:kapareho|pareho|kamukha|tugma)\s+(?:sa|ng)\s+(?:picture|pic|photo|litrato|description)\b",
            r"\btrue\s+to\s+(?:the\s+)?(?:picture|photo|description)\b",
        ]
    ),
    neg=_re(
        [
            r"\bwrong\s+(?:item|items|color|colour|size|product|variation|design|variant|flavou?r|model|order|one)\b",
            r"\bmali\s+(?:ang|na|yung|ung)?\s*(?:item|kulay|color|size|binigay|pinadala|dumating|order|design|flavor)\b",
            r"\b(?:iba|ibang)\s+(?:ang\s+|yung\s+|ung\s+|na\s+)?(?:kulay|color|item|design|dumating|binigay|pinadala|flavor|size)\b",
            r"\bnot\s+(?:the\s+)?same\s+as\s+(?:the\s+)?(?:picture|photo|advertised|listed|description)\b",
            r"\b(?:seller|shop)\s+sent\s+(?:me\s+)?(?:the\s+)?(?:wrong|different|another|white|black|red|blue|pink|green|yellow|small|large|big)\b",
            r"\b(?:incomplete|kulang\s+(?:ang|yung|ung)?\s*(?:laman|item|piraso|parts?|accessories|gamit)|missing\s+(?:parts?|items?|pieces?|accessories|cable|charger))\b",
            r"\bwalang\s+(?:kasamang\s+)?(?:cable|charger|punda|manual)\b",
        ]
    ),
)
FREEBIES = Aspect(
    "freebies",
    "promised freebies",
    problem="missing freebies or bundle items",
    pos=_re(
        [
            r"\b(?:dami|daming|maraming|nice|great)\s+(?:\w+\s+){0,2}freebies?\b",
            r"\b(?:thank(?:s|\s*you)?|salamat|tnx|tysm)\s+(?:sa\s+|for\s+(?:the\s+)?)?(?:\w+\s+){0,1}(?:freebies?|free\s+gifts?|pa-?free)\b",
        ]
    ),
    neg=_re(
        [
            r"\b(?:walang|wala|hindi|di|no|without|missing)\s+(?:man\s+|naman\s+|akong\s+)?(?:\w+\s+){0,2}(?:freebies?|free\s+gifts?|free\s+items?|b1t1|bonus)\b",
            r"\bfreebies?\s+(?:wala|missing|never|not\s+received)\b",
            r"\b(?:b1t1|buy\s*(?:1|one)\s*(?:take|get)\s*(?:1|one))\b[^.!?]{0,60}\b(?:wala|isa\s+lang|iisa|missing|not\s+received|hindi|di)\b",
            r"\bdidn'?t\s+(?:get|receive)\s+(?:any\s+)?(?:extra|free|freebies?|gift)\b",
            r"\bfake\s+(?:ang\s+)?promo\b",
        ]
    ),
    kind=SERVICE,
)
ARRIVAL = Aspect(
    "arrival",
    "condition on arrival",
    problem="items that arrived damaged",
    pos=_re(
        [
            r"\b(?:good|perfect|excellent|great)\s+condition\b",
            r"\b(?:no|walang)\s+(?:damage|damages|sira|dent|gasgas)\b",
        ]
    ),
    neg=_re(
        [
            r"\b(?:arrived|dumating|received|nareceive)\s+(?:\w+\s+){0,2}(?:damaged|broken|cracked|sira|basag|yupi|punit|nabasag|deformed)\b",
            r"\b(?:damaged|broken|basag|nabasag|sira|yupi|nayupi|punit|crushed|cracked)\s+(?:yung\s+|ung\s+|ang\s+|na\s+|the\s+)?(?:item|product|unit|heater|bottle|cover|jar|lid|seal|cap)\b",
            r"\b(?:item|product|unit)\s+(?:is\s+|was\s+|ay\s+)?(?:broken|damaged|cracked|nabasag|sira|yupi)\b",
            r"\b(?:the\s+)?seal\s+(?:is\s+|was\s+)?(?:already\s+)?(?:opened|broken|open|bukas)\b",
            r"\bmay\s+(?:yupi|dent|gasgas|basag|crack|stain|mantsa|tagas|leak)\b",
            r"\b(?:leaking|leaked|tumagas)\b",
        ]
    ),
    kind=SERVICE,
)

GENERAL = (FUNCTIONALITY, BUILD, DURABILITY, SIZE, APPEARANCE, VALUE, EASE, MATCHES_LISTING, AUTHENTICITY, DELIVERY, PACKAGING, SELLER, FREEBIES, ARRIVAL)

# --- the product-type profiles ----------------------------------------------------------------------------------
HAIR = (
    Aspect(
        "softness",
        "softness",
        pos=_re([r"\b(?:malambot|lambot|lumambot|lmbot|soft(?:er|ness)?|smooth(?:er|ness)?|makinis|kuminis|silky|sleek)\b"]),
        neg=_re([r"\b(?:magaspang|rough|matigas|tumigas|brittle|hay(?:wire)?|parang\s+dayami|straw[- ]like)\b"]),
    ),
    Aspect(
        "manageability",
        "manageability",
        pos=_re(
            [
                r"\b(?:manageable|detangl\w*|tangle[- ]free)\b",
                r"\b(?:madaling|dali)\s+(?:suklayin|i-?style|ayusin|ma-?manage)\b",
                r"\b(?:easy|easier)\s+to\s+(?:comb|style|manage|brush)\b",
                r"\b(?:hindi|di)\s+(?:na\s+)?(?:gusot|magulo|nagugusot|nagugulo)\b",
            ]
        ),
        neg=_re([r"\b(?:gusot|magulo|tangl\w*|hirap\s+suklayin|unmanageable|frizz\w*|nag-?frizz|nagugusot)\b"]),
        # "smoothening the frizzy hair": frizz is what the product fixes.
        neg_guard=re.compile(r"\b(?:smoothen\w*|smooth\w*|tame\w*|reduc\w*|control\w*|fights?|prevent\w*|get\s+rid|nawala)\b[^.!?]{0,25}\b(?:frizz\w*|tangl\w*|gusot)\b", re.I),
    ),
    FRAGRANCE,
    Aspect(
        "dryness",
        "dryness",
        neg=_re(
            [
                r"\b(?:drying|dryness|nagda?dry|nag-?dry|nakakadry|nakakatuyo|tumutuyo|nagiging\s+dry|dehydrat\w*)\b",
                # "natuyo" also says the PRODUCT dried ("pag natuyo, may white stain"), so it counts only beside hair, skin or lips.
                r"\b(?:tuyo|natuyo)\b(?=\s+(?:ang\s+|na\s+|yung\s+)?(?:buhok|balat|labi|mukha|anit|hair|skin|lips))",
                r"\b(?:sobrang|ang|so|very|too)\s+dry\b",
                r"\bdry\s+(?:hair|ang\s+buhok|na\s+buhok|scalp|feeling|feel)\b",
                r"\b(?:hair|buhok)\s+(?:ko\s+)?(?:got|became|naging|feels?)\s+dry\b",
            ]
        ),
        neg_guard=re.compile(r"\b(?:blow[- ]?dry\w*|quick[- ]?dry\w*|dry\s+(?:shampoo|conditioner|time)|mabilis\s+matuyo|natuyo\s+agad)\b", re.I),
        problem_only=True,
        problem="dryness",
    ),
    Aspect(
        "scalp_irritation",
        "scalp irritation",
        neg=_re(
            [
                r"\b(?:nangati|nangangati|makati|kati|nangangati|itchy|itching|itch|hapdi|namula|rashes?|balakubak|dandruff|nag-?flake|flaking)\b",
                r"\b(?:irritat\w*)\b",
                r"\banit\s+(?:ko\s+)?(?:nangati|namula|nasaktan|sumakit|nagka\w+)\b",
            ]
        ),
        problem_only=True,
        problem="scalp irritation or itching",
    ),
    Aspect(
        "hair_fall",
        "hair fall",
        neg=_re([r"\b(?:nalagas|nalalagas|hair\s?fall|lagas|nagkalagas|nagka-?hairfall|hair\s+loss|nag-?shed|shedding)\b"]),
        problem_only=True,
        problem="hair fall",
    ),
    Aspect(
        "functionality",
        "effect on hair",
        problem="little or no effect on hair",
        pos=FUNCTIONALITY.pos
        + _re([r"\b(?:gumanda\s+ang\s+buhok|bumuti\s+ang\s+buhok|nag-?improve|visible\s+results?|may\s+epekto|nagbago\s+ang\s+buhok|nag-?shine|shiny|makintab)\b"]),
        neg=FUNCTIONALITY.neg,
        neg_guard=FUNCTIONALITY.neg_guard,
    ),
)

SKIN = (
    Aspect(
        "texture",
        "texture",
        pos=_re(
            [
                r"\b(?:lightweight|magaan|creamy|silky|non[- ]sticky|smooth\s+(?:texture|feel|application))\b",
                r"\b(?:hindi|di)\s+(?:malagkit|sticky|mabigat)\b",
            ]
        ),
        neg=_re([r"\b(?:malagkit|sticky|chalky|gritty|clumpy|cakey|pilling|mabigat\s+sa\s+mukha|heavy\s+(?:on|feel)|streaky|patchy)\b"]),
    ),
    # Real reviews say "gentle on the skin" far more often than they describe a texture, so it is its own aspect. A product NAME
    # that contains the word ("Cetaphil Gentle Skin Cleanser") is not a claim.
    Aspect(
        "gentleness",
        "gentleness on the skin",
        pos=_re([r"\b(?:gentle|mild|soothing|non[- ]irritating)\b(?!\s+(?:skin\s+)?(?:cleanser|wash|face\s+wash|cleansing|exfoliating|formula\b))"]),
        neg=_re([r"\b(?:harsh|stinging|masakit\s+sa\s+mukha|matapang\s+sa\s+balat)\b"]),
        neg_guard=re.compile(r"\b(?:not|no|doesn'?t|isn'?t|hindi|di|walang)\s+(?:\w+\s+){0,2}harsh\b", re.I),
    ),
    Aspect(
        "absorption",
        "absorption",
        pos=_re(
            [
                r"\b(?:mabilis\s+(?:sumipsip|ma-?absorb)|sumisipsip|absorbs?(?:\s+(?:fast|quickly|easily|well))?|absorbed|absorbing|fast[- ]absorbing|nag-?absorb|ma-?absorb)\b",
            ]
        ),
        neg=_re([r"\b(?:hindi|di|d)\s+(?:ma-?absorb|nag-?absorb|sumisipsip)\b", r"\bsits?\s+on\s+(?:top|the\s+skin)\b", r"\bnag-?stay\s+sa\s+ibabaw\b"]),
    ),
    FRAGRANCE,
    Aspect(
        "oiliness",
        "oiliness",
        neg=_re([r"\b(?:oily|mamantika|nakakamantika|greasy|oiliness|nag-?oily|lumalangis|mantika)\b"]),
        neg_guard=re.compile(r"\bnon[- ]?(?:greasy|oily|sticky)\b|\bwalang\s+(?:mantika|oil)\b|\boil[- ]free\b", re.I),  # "non greasy" is praise
        problem_only=True,
        problem="an oily or greasy feel",
    ),
    Aspect(
        "skin_irritation",
        "skin irritation",
        neg=_re(
            [
                # Complaint forms only. A bare "acne" or "pimples" is as often what the product treats ("for acne-prone skin") as a reaction to it.
                r"\b(?:irritat\w*|breakouts?|nag-?break\s?out|tigyawat|rashes?|namula|nangati|nangangati|makati|allerg\w*|nag-?react|stinging|hapdi|nagbalat|nagbabalat|peeling|nasunog)\b",
                r"\b(?:nagka|nag)[- ]?(?:acne|pimples?)\b",
                r"\b(?:got|gets?|getting|have|had|developed|new|more)\s+(?:\w+\s+){0,2}(?:acne|pimples?|zits)\b",
            ]
        ),
        # "suits sensitive and acne-prone skin", "for sensitive skin": the skin the product is for.
        # Also: "for my rashes, I still use steroid cream" names the problem the buyer already had, not a reaction to this product.
        neg_guard=re.compile(
            r"\b(?:acne|sensitive|breakout)[- ]prone\b|\b(?:for|suits?|suitable\s+for|good\s+for|ideal\s+for|when\s+you\s+have)\s+(?:\w+\s+){0,3}(?:sensitive|acne)"
            r"|\b(?:for|para\s+sa)\s+(?:my|the|your|aking)?\s*(?:rashes?|acne|pimples?|eczema|skin\s+irritation|allerg\w*)\b",
            re.I,
        ),
        problem_only=True,
        problem="skin irritation, breakouts or rashes",
    ),
    Aspect(
        "functionality",
        "effect on skin",
        problem="little or no effect on skin",
        pos=FUNCTIONALITY.pos
        + _re([r"\b(?:glowing|glow|kuminis|gumanda\s+ang\s+(?:skin|balat|mukha)|brighter|moisturi[sz]\w*|hydrat\w*|clearer|nag-?glow|makinis\s+ang\s+(?:mukha|balat))\b"]),
        neg=FUNCTIONALITY.neg,
        neg_guard=FUNCTIONALITY.neg_guard,
    ),
)

PHONE = (
    BATTERY,
    Aspect(
        "camera",
        "camera quality",
        pos=_re(
            pair(
                r"maganda|ganda|clear|sharp|crisp|great|good|excellent|malinaw|ok|okay|goods?|amazing|detailed|nice|best|impressive",
                r"camera|cam|photos?|pictures?|pics?|selfies?|video\s+quality|kuha|shots?",
            )
        ),
        neg=_re(
            pair(
                r"pangit|panget|blurry|blur|malabo|grainy|poor|bad|mahina|noisy|washed\s+out|mediocre|mushy|disappointing",
                r"camera|cam|photos?|pictures?|pics?|selfies?|video\s+quality|kuha|shots?",
            )
        ),
    ),
    Aspect(
        "performance",
        "performance",
        pos=_re(
            pair(r"smooth|fast|mabilis|snappy|great|good|maayos|ok|okay|solid|powerful|malakas|swabe|lag[- ]free|impressive", r"performance|speed|processor|chip|gaming|games?|apps?|multitask\w*|takbo|bilis")
            + [r"\b(?:walang|no|zero|di|hindi)\s+(?:masyadong?\s+)?(?:lag|hang|delay)\b", r"\blag[- ]free\b", r"\bswabe\b"]
        ),
        neg=_re(
            [
                r"\b(?:laggy|lag|lags|lagging|nag-?lag|nalalag|slow|mabagal|bagal|nag-?hang|nahahang|hangs|hanging|freez\w*|nag-?freeze|stutter\w*|choppy|sluggish|nag-?crash|crashes)\b",
            ]
        ),
    ),
    CHARGING,
    Aspect(
        "display",
        "display",
        pos=_re(
            pair(
                r"clear|bright|sharp|vivid|smooth|crisp|malinaw|maliwanag|maganda|ganda|great|good|nice|beautiful|gorgeous|ok|okay|goods?",
                r"screen|display|amoled|oled|lcd|resolution|brightness|screen\s+quality|touch",
            )
        ),
        neg=_re(
            pair(r"dim|dull|pangit|panget|malabo|madilim|poor|bad|cracked|basag|unresponsive", r"screen|display|amoled|oled|lcd|resolution|brightness|touch")
            + [r"\b(?:green\s+line|dead\s+pixels?|ghost\s?touch|flicker\w*|nag-?flicker|screen\s+burn|burn[- ]in|may\s+line\s+ang\s+screen)\b"]
        ),
    ),
    OVERHEATING,
    SHUTDOWNS,
)

EARBUDS = (
    Aspect(
        "sound",
        "sound quality",
        pos=_re(
            pair(
                r"clear|crisp|great|good|amazing|excellent|rich|balanced|malinaw|malakas|ganda|maganda|ok|okay|goods?|punchy|deep|nice|solid|malutong|impressive|best",
                r"sound|audio|bass|treble|sound\s+quality|tunog|quality\s+ng\s+tunog",
            )
        ),
        neg=_re(
            pair(r"mahina|poor|bad|pangit|panget|flat|basag|muffled|tinny|lousy", r"sound|audio|bass|treble|sound\s+quality|tunog")
            + [r"\b(?:muffled|distort\w*|crackl\w*|static|tinny|hiss\w*|garbled|walang\s+bass|no\s+bass)\b"]
        ),
    ),
    Aspect(
        "comfort",
        "comfort",
        pos=_re(
            [
                r"\b(?:comfortable|komportable|comfy|snug|secure\s+fit|lightweight|magaan)\b",
                r"\b(?:hindi|di)\s+(?:masakit|nahuhulog|nalalaglag|nakakapagod)\b",
                r"\bfits?\s+(?:well|perfectly|snugly|great|nicely|securely)\b",
                r"\bsakto\s+sa\s+(?:tenga|ear|tainga)\b",
            ]
        ),
        neg=_re(
            [
                r"\b(?:masakit|sumasakit|sakit)\s+(?:sa\s+|ang\s+)?(?:tenga|ear|tainga|ears)\b",
                r"\b(?:uncomfortable|hindi\s+komportable|hindi\s+comfortable|nahuhulog|nalalaglag|loose\s+fit)\b",
                r"\bhurts?\s+(?:my\s+)?ears?\b",
                r"\b(?:hindi|di)\s+(?:kasya|sakto)\s+(?:sa\s+)?(?:tenga|ear|tainga)\b",
            ]
        ),
    ),
    Aspect(
        "connectivity",
        "Bluetooth connectivity",
        pos=_re(
            [
                r"\b(?:connects?|connected|nag-?connect|ma-?connect|pairs?|pairing|paired)\s+(?:easily|agad|fast|quickly|mabilis|well|instantly|seamlessly|properly)\b",
                r"\b(?:easily|agad|fast|quickly|mabilis|seamless)\s+(?:pairing|connection|connect\w*)\b",
                r"\bstable\s+(?:connection|bluetooth|connectivity)\b",
                r"\b(?:connection|connectivity)\s+(?:is\s+)?(?:stable|good|great|strong|maayos)\b",
                r"\b(?:walang|no)\s+(?:delay|lag|disconnect\w*|latency)\b",
            ]
        ),
        neg=_re(
            [
                r"\b(?:disconnect\w*|nag-?disconnect|nadi-?disconnect|latency)\b",
                r"\bcuts?\s*(?:out|off)\b|\bnagka?-?cut\b",
                r"\b(?:hindi|di|ayaw|d)\s+(?:ma-?|nag-?)(?:connect|pair)\b",
                r"\bunstable\s+(?:connection|bluetooth|connectivity)\b",
                r"\b(?:connection|connectivity|bluetooth)\s+(?:issues?|problems?|drops?|keeps\s+dropping)\b",
                r"\b(?:delay|lag|laggy)\b",
            ]
        ),
    ),
    Aspect(
        "microphone",
        "microphone quality",
        pos=_re(
            pair(
                r"clear|good|great|malinaw|ok|okay|goods?|crisp|loud|maganda|ganda|audible",
                r"mic|microphone|call\s+quality|calls?|voice|boses|tawag",
            )
        ),
        neg=_re(
            [
                r"\b(?:hindi|di)\s+(?:ako\s+)?(?:naririnig|marinig)\b",
                r"\b(?:can'?t|cannot)\s+hear\s+me\b",
                r"\bmic\s+(?:is\s+)?(?:not\s+working|dead|muffled|poor|bad)\b",
            ]
            + pair(r"poor|bad|pangit|panget|mahina|crackly|garbled|muffled", r"mic|microphone|call\s+quality|voice|boses")
        ),
    ),
    BATTERY,
)

POWERBANK = (
    Aspect(
        "capacity",
        "battery capacity",
        pos=_re(
            [
                r"\b(?:malaki|big|true|legit|accurate|tunay|enough|sapat|good|great)\s+(?:ang\s+|na\s+)?(?:capacity|mah)\b",
                r"\b(?:capacity|mah)\s+(?:is\s+)?(?:good|great|legit|accurate|true|malaki|sapat|enough)\b",
                r"\b(?:charges?|nacha-?charge|nakacha-?charge)\s+(?:my\s+)?(?:phone\s+)?(?:\d|two|three|four|dalawa|tatlo|apat|ilang|maraming)\s*(?:times|beses|x)?\b",
                r"\b(?:true|real)\s+to\s+(?:its\s+)?(?:mah|capacity)\b",
            ]
        ),
        neg=_re(
            [
                r"\b(?:fake|mababa|false|mas\s+maliit|hindi\s+totoo|di\s+totoo|less)\s+(?:na\s+|ang\s+|sa\s+)?(?:capacity|mah)\b",
                r"\b(?:capacity|mah)\s+(?:is\s+)?(?:fake|false|less|mababa|hindi\s+totoo|di\s+totoo|not\s+(?:true|real|accurate))\b",
                r"\b(?:isang|1|one)\s+(?:charge|beses)\s+lang\b",
                r"\b(?:ubos|nauubos|nauubusan)\s+(?:agad|ang\s+laman)\b",
                r"\b(?:hindi|di)\s+(?:umabot|pumasa)\b",
            ]
        ),
    ),
    CHARGING,
    OVERHEATING,
    SHUTDOWNS,
)

APPAREL = (
    Aspect(
        "fabric",
        "fabric",
        pos=_re(
            pair(
                r"soft|malambot|good|great|nice|quality|maganda|ganda|thick|makapal|breathable|presko|smooth|premium|comfy|stretchy|ok|okay|goods?|de-?kalidad",
                r"fabric|material|tela|cotton|texture",
            )
            + [r"\b(?:breathable|presko|makapal|hindi\s+(?:nangangati|nakakangati|manipis)|di\s+(?:nangangati|manipis))\b"]
        ),
        neg=_re(
            [
                r"\b(?:manipis|thin|see[- ]?through|kita\s+(?:ang\s+)?(?:loob|ilalim|underwear)|nangangati|makati|magaspang|rough|scratchy|itchy|nag-?shrink|shrunk|lumiit|nangunot|kulubot|nag-?pill|pilling)\b",
            ]
            + pair(r"cheap|pangit|panget|poor|mura|manipis|thin|bad", r"fabric|material|tela|cotton")
        ),
        neg_guard=re.compile(r"\b(?:presko|breathable|cool|light|magaan|summer|hindi\s+mainit)\b", re.I),
    ),
    Aspect(
        "size",
        "fit and sizing",
        pos=_re(
            [
                r"\bfits?\s+(?:perfectly|well|great|nicely|me|just\s+right|true\s+to\s+size|snugly)\b",
                r"\b(?:tama|sakto|saktong|swak)\s+(?:ang\s+|na\s+)?(?:size|sukat|fit)\b",
                r"\b(?:saktong[- ]sakto|kasya\s+(?:sakin|sa\s+akin|po|sya|siya|ang)|perfect\s+(?:fit|size)|true\s+to\s+size|nice\s+fit)\b",
                r"\b(?:size|sukat)\s+(?:is\s+)?(?:perfect|accurate|tama|sakto|true)\b",
            ]
        ),
        neg=_re(
            [
                r"\b(?:masyadong?|too|sobrang|so)\s+(?:liit|maliit|malaki|luwag|maluwag|sikip|masikip|tight|loose|small|big|large|short|maikli|haba|mahaba|long)\b",
                r"\b(?:hindi|di|d)\s+(?:kasya|sakto|tama\s+ang\s+(?:size|sukat))\b",
                r"\bruns?\s+(?:small|big|large|tight)\b",
                r"\b(?:wrong|mali\s+ang)\s+size\b",
                r"\bsize\s+(?:is\s+)?(?:off|small|big|mali|not\s+accurate|hindi\s+accurate)\b",
                r"\b(?:doesn'?t|didn'?t|not)\s+fit\b",
                r"\b(?:sumikip|naliitan|nalakihan|nasikipan|naluwagan)\b",
                r"\b(?:hindi|di)\s+(?:true|accurate)\s+(?:sa\s+)?size\b",
            ]
        ),
    ),
    Aspect(
        "stitching",
        "stitching",
        pos=_re(
            pair(
                r"neat|maayos|clean|maganda|ganda|good|great|strong|matibay|well[- ]made|solid|ok|okay",
                r"stitch\w*|tahi|seams?|finishing|zipper|zip|butones?|buttons?",
            )
        ),
        neg=_re(
            [
                r"\b(?:tastas|natastas|natatastas|hilacha|nakalawit|frayed|sloppy|loose\s+threads?|uneven\s+stitch\w*)\b",
                r"\b(?:sira|nasira|sirang)\s+(?:ang\s+)?(?:zipper|zip|butones?|buttons?)\b",
                r"\b(?:natanggal|nalaglag|nalas)\s+(?:ang\s+)?(?:butones?|buttons?|tahi)\b",
            ]
        ),
    ),
    Aspect(
        "comfort",
        "comfort",
        pos=_re(
            [
                r"\b(?:comfortable|komportable|comfy|presko|breathable|lightweight|magaan|cool\s+to\s+wear)\b",
                r"\b(?:hindi|di)\s+(?:mainit|nakakainit|nakaka-?init|makati|nangangati)\b",
            ]
        ),
        neg=_re(
            [
                r"\b(?:uncomfortable|hindi\s+komportable|hindi\s+comfortable|nakakainit|nakaka-?init|nakakairita)\b",
                r"\bmainit\s+(?:suot|isuot|sa\s+katawan|sa\s+balat)\b",
            ]
        ),
    ),
)

FOOTWEAR = (
    Aspect(
        "comfort",
        "comfort",
        pos=_re(
            [
                r"\b(?:comfortable|komportable|comfy|cushion\w*|lightweight|magaan|good\s+support|soft\s+sole)\b",
                r"\b(?:hindi|di)\s+(?:masakit|nakakapagod|nakakangalay)\b",
            ]
        ),
        neg=_re(
            [
                r"\b(?:masakit|sumasakit|sakit)\s+(?:sa\s+|ang\s+)?(?:paa|talampakan|sakong)\b",
                r"\b(?:uncomfortable|hindi\s+komportable|hindi\s+comfortable|nagka-?sugat|nasugatan|blisters?|nagpapasakit|namaga)\b",
                r"\bhurts?\s+(?:my\s+)?(?:feet|foot|heels?)\b",
            ]
        ),
    ),
    APPAREL[1],
    Aspect(
        "material",
        "material",
        pos=_re(
            pair(
                r"good|great|nice|quality|matibay|maganda|ganda|sturdy|solid|premium",
                r"material|leather|sole|rubber|stitch\w*|tahi|gawa|quality|build",
            )
            + [r"\b(?:matibay|well[- ]made)\b"]
        ),
        neg=_re(
            pair(r"cheap|pangit|panget|manipis|plastic|poor|mababang|mura", r"material|sole|quality|gawa|leather|rubber")
            + [r"\b(?:natanggal\s+ang\s+(?:sole|swelas)|natastas|natatanggal|nabutas|nag-?peel|peeling|nabitak|cracked|bumuka)\b"]
        ),
    ),
)

FOOD = (
    Aspect(
        "taste",
        "taste",
        pos=_re(
            [
                r"\b(?:masarap|sarap|yummy|delicious|tasty|flavorful|malasa)\b",
                r"\b(?:good|great|nice|amazing|ok|okay)\s+(?:taste|flavou?r)\b",
                r"\b(?:taste|lasa|flavou?r)\s+(?:is\s+|ay\s+|nya\s+)?(?:good|great|nice|masarap|ok|okay|sarap|amazing)\b",
            ]
        ),
        neg=_re(
            [
                r"\b(?:matabang|mapait|bland|lasang\s+(?:plastic|panis|sabon|kemikal|medicine|gamot|lipas))\b",
                r"\b(?:pangit|panget|bad|awful|weird|funny|off)\s+(?:ang\s+)?(?:lasa|taste|flavou?r)\b",
                r"\btastes?\s+(?:bad|awful|weird|funny|bland|off|like\s+(?:plastic|chemicals|soap))\b",
                r"\b(?:sobrang|sobra)\s+(?:tamis|alat|maalat|matamis)\b",
            ]
        ),
    ),
    Aspect(
        "freshness",
        "freshness",
        pos=_re(
            [
                r"\b(?:fresh\w*|sariwa|malutong\s+pa|crispy|crunchy|malutong)\b",
                r"\b(?:hindi|di)\s+(?:panis|stale|lipas|basa|inamag)\b",
            ]
        ),
        neg=_re(
            [
                r"\b(?:stale|lipas|panis|inamag|amag|moldy|mold|spoiled|bulok|lamog|uod|ipis|langgam|nabasa|basa\s+na|lumambot)\b",
                r"\bmalambot\s+na\s+(?:ang\s+)?(?:chips|biscuit|cookies|crackers|chichirya)\b",
            ]
        ),
    ),
    Aspect(
        "expiry",
        "expiry date",
        pos=_re(
            [
                r"\b(?:long|mahaba|malayo|far|okay|ok)\s+(?:pa\s+)?(?:ang\s+)?(?:expir\w*|expiry|best\s+before|date)\b",
                r"\bexpir\w*\s+(?:date\s+)?(?:is\s+)?(?:long|far|malayo|mahaba|ok|okay|pa)\b",
            ]
        ),
        neg=_re(
            [
                r"\b(?:expired|nag-?expire|nag-?expired)\b",
                r"\b(?:malapit|near|short|maikli)\s+(?:na\s+)?(?:sa\s+)?(?:expir\w*|expiry|best\s+before|date)\b",
                r"\bexpir\w*\s+(?:date\s+)?(?:is\s+)?(?:soon|near|short|malapit)\b",
                r"\bpast\s+(?:its\s+)?expir\w*\b",
            ]
        ),
        problem="a short or past expiry date",
    ),
    Aspect(
        "quantity",
        "quantity",
        pos=_re(
            pair(
                r"generous|marami|maraming|madami|punong-?puno|puno|sulit|full|big|malaki|enough|sapat|complete|kumpleto|swak",
                r"quantity|portion|serving|laman|dami|amount|content",
            )
        ),
        neg=_re(
            [
                r"\b(?:kaunti|konti|onti|kulang|puro\s+hangin|hangin\s+lang|mas\s+marami\s+ang\s+hangin|half[- ]empty|incomplete)\b",
                r"\b(?:maliit|mas\s+maliit)\s+(?:ang\s+)?(?:laman|serving|portion|pack|dami)\b",
                r"\b(?:hindi|di)\s+(?:kumpleto|puno|full)\b",
            ]
        ),
    ),
    Aspect(
        "texture",
        "texture",
        pos=_re([r"\b(?:crunchy|crispy|malutong|creamy|tender|juicy|moist|chewy)\b"]),
        neg=_re([r"\b(?:matigas|tough|soggy|nanigas|nag-?tigas|rubbery|gritty)\b"]),
    ),
)

APPLIANCE = (
    Aspect(
        "performance",
        "performance",
        pos=_re(
            [
                r"\b(?:powerful|strong|efficient|performs?\s+well|great\s+performance)\b",
                r"\b(?:malakas)\s+(?:ang\s+|na\s+)?(?:hangin|lamig|init|motor|suction|hatak|takbo|power|lakas)\b",
                r"\b(?:mabilis|fast)\s+(?:uminit|mag-?init|lumamig|mag-?luto|magluto|kumulo|mag-?blend|cook\w*|cool\w*|heat\w*|boil\w*|blend\w*|spin\w*)\b",
                r"\b(?:lumalamig|umiinit|nagbo-?boil)\s+(?:agad|ng\s+mabilis|na\s+mabilis)\b",
                r"\bcools?\s+(?:fast|well|quickly)\b",
                r"\b(?:even(?:ly)?)\s+(?:heat|cook)\w*\b",
            ]
        ),
        neg=_re(
            [
                r"\b(?:underpowered|poor\s+performance|barely\s+(?:cools?|heats?|works?|blows?))\b",
                r"\b(?:mahina|weak)\s+(?:ang\s+|na\s+)?(?:hangin|lamig|init|motor|suction|hatak|takbo|power|lakas|performance)\b",
                r"\b(?:hindi|di|d)\s+(?:ito\s+)?(?:lumalamig|umiinit|uminit|naiinit|kumukulo|malakas|powerful|nag-?blend|nagbo-?boil)\b",
                r"\b(?:walang)\s+(?:hangin|lamig|init)\b",
                r"\bdi\s+(?:malamig|mainit)\b",
            ]
        ),
    ),
    Aspect(
        "noise",
        "noise level",
        pos=_re(
            [
                r"\b(?:tahimik|quiet|silent|low\s+noise|quiet\s+operation)\b",
                r"\b(?:walang|hindi|di)\s+(?:masyadong?\s+)?(?:ingay|maingay)\b",
            ]
        ),
        neg=_re(
            [
                r"\b(?:maingay|ingay|noisy|nakaka-?ingay|rattl\w*|humming|buzzing|vibrat\w*|lagitik|kalansing|ugong)\b",
                r"\b(?:sobrang|ang)\s+lakas\s+ng\s+tunog\b",
            ]
        ),
        problem="noise",
    ),
    Aspect(
        "power_use",
        "power consumption",
        pos=_re(
            [
                r"\b(?:tipid|nakakatipid|nakatipid)\s+(?:sa|ng)\s+(?:kuryente|power|electricity|konsumo)\b",
                r"\b(?:energy[- ]efficient|power[- ]saving|inverter)\b",
                r"\b(?:hindi|di)\s+(?:nakaka-?)?taas\s+(?:ng|sa)\s+(?:bill|kuryente)\b",
                r"\bbumaba\s+(?:ang\s+)?(?:bill|kuryente)\b",
            ]
        ),
        neg=_re(
            [
                r"\bmalakas\s+(?:sa|ang)\s+(?:kuryente|konsumo|power)\b",
                r"\b(?:mataas|tumaas|sumipa|lumobo)\s+(?:ang\s+)?(?:bill|kuryente|konsumo)\b",
                r"\b(?:power[- ]hungry|grabe\s+(?:ang\s+)?kuryente|ang\s+laki\s+ng\s+bill)\b",
                r"\b(?:high|mataas)\s+(?:power|electric|electricity)\s+(?:consumption|bill|usage)\b",
            ]
        ),
    ),
)

MOTORCYCLE = (
    Aspect(
        "fitment",
        "fitment",
        pos=_re(
            [
                r"\b(?:fits?|kasya|swak|sakto|bagay|tugma)\s+(?:perfectly|well|great|nicely|po|sa|ang|na|sakto|talaga|ito|siya|sya|naman)\b",
                r"\b(?:direct|exact|perfect|tamang|saktong)[- ](?:fit|fitment|size|sukat)\b",
                r"\bplug[- ]?(?:and|n)[- ]?play\b",
                r"\bcompatible\b",
            ]
        ),
        neg=_re(
            [
                r"\b(?:hindi|di|d)\s+(?:kasya|swak|sakto|bagay|tugma|compatible|nagfit|fit|magkasya)\b",
                r"\b(?:doesn'?t|didn'?t|won'?t|not)\s+fit\b",
                r"\bincompatible\b",
                r"\b(?:wrong|mali\s+ang|maling)\s+(?:size|model|part|fit|item)\b",
                r"\b(?:kailangan|need(?:s|ed)?)\s+(?:pang\s+|to\s+)?(?:i-?)?(?:modif\w*|palitan|ibahin|gumawa|drill\w*|file|gilingin|adjust\w*)\b",
                r"\b(?:maluwag|masikip|malaki|maliit)\s+(?:ang\s+)?(?:butas|size|sukat)\b",
            ]
        ),
    ),
    Aspect(
        "performance",
        "performance",
        pos=_re(
            [
                r"\b(?:bumilis|lumakas|humatak|gumaan|umangat|naging\s+(?:smooth|malakas|mabilis))\b",
                r"\b(?:malakas|matulin|maganda|ganda|solid|maayos)\s+(?:ang\s+|na\s+|ng\s+)?(?:hatak|arangkada|preno|brake|takbo|kapit|ilaw|performance|response|suspension|shock)\b",
                r"\b(?:hatak|arangkada|preno|brake|kapit|ilaw|response|suspension|performance)\s+(?:ay\s+|is\s+)?(?:malakas|maganda|ganda|solid|maayos|great|good|smooth|excellent)\b",
                r"\bsmooth\s+(?:na\s+)?(?:ang\s+)?(?:takbo|arangkada|andar|ride)\b",
            ]
        ),
        neg=_re(
            [
                r"\b(?:bumagal|humina|lumabo|lumala|nanginginig)\b",
                r"\b(?:mahina|poor|pangit|panget|bad|mabagal)\s+(?:ang\s+|na\s+|ng\s+)?(?:hatak|arangkada|preno|brake|takbo|kapit|ilaw|performance|response|suspension)\b",
                r"\b(?:hatak|arangkada|preno|brake|kapit|ilaw|response|suspension|performance)\s+(?:ay\s+|is\s+)?(?:mahina|pangit|panget|bad|poor|mabagal)\b",
                r"\b(?:walang|no)\s+(?:improvement|pinagbago|hatak|kagat|epekto)\b",
                r"\b(?:hindi|di)\s+(?:humatak|bumilis|kumagat|nag-?improve|kumapit)\b",
            ]
        ),
    ),
    Aspect(
        "durability",
        "durability",
        pos=_re([r"\b(?:matibay|tumagal|long[- ]lasting|hindi\s+kinakalawang|di\s+kinakalawang|no\s+rust|walang\s+kalawang|stainless)\b"]),
        neg=DURABILITY.neg
        + _re([r"\b(?:kinalawang|kalawang|rust\w*|nabali|nagasgas|nabaluktot|nag-?bend|deformed|bumigay)\b"]),
    ),
)

# --- real-review additions to the profiles (development half; see the note above GENERAL) ----------------------------------
def _patch(profile: tuple[Aspect, ...], changes: dict[str, tuple[list[str], list[str]]], extra: tuple[Aspect, ...] = ()) -> tuple[Aspect, ...]:
    return tuple(_more(a, *changes[a.id]) if a.id in changes else a for a in profile) + extra


MIXABILITY = Aspect(
    "mixability",
    "mixability",
    pos=_re(
        [
            r"\b(?:mixes|mixed|dissolves?|dissolved)\s+(?:very\s+|really\s+)?(?:well|easily|smoothly|fast|quickly)\b",
            r"\b(?:easy|easily)\s+(?:to\s+)?(?:mix|dissolve)\w*\b",
            r"\bnatutunaw\s+(?:ng\s+)?(?:maayos|mabuti|mabilis)\b",
        ]
    ),
    neg=_re(
        [
            r"\bpoor\s+mixab\w+\b",
            r"\b(?:clump(?:s|y|ing)?|bukol(?:-?bukol)?)\b",
            r"\b(?:hindi|di)\s+(?:natutunaw|ma-?mix|nagma-?mix)\b",
            r"\bhard\s+to\s+(?:mix|dissolve)\b",
        ]
    ),
)
# "moisturizes dry hair", "for dry hair": dry hair is who the product is for, not a complaint about it.
_DRYNESS = _more(
    next(aspect for aspect in HAIR if aspect.id == "dryness"),
    guard=r"\b(?:blow[- ]?dry\w*|quick[- ]?dry\w*|dry\s+(?:shampoo|conditioner|time)|mabilis\s+matuyo|natuyo\s+agad)\b"
    r"|\b(?:moisturi[sz]\w*|nourish\w*|hydrat\w*|treats?|repairs?|for|ideal\s+for|suitable\s+for|good\s+for)\s+(?:\w+\s+){0,4}dry\b",
)
HAIR = tuple(_DRYNESS if aspect.id == "dryness" else aspect for aspect in HAIR)
HAIR = _patch(
    HAIR,
    {
        "functionality": (
            [
                r"\b(?:good|great|nice|maganda|ganda|effective|ok|okay)\s+(?:sya\s+|siya\s+|po\s+|ito\s+)?(?:for|sa|on)\s+(?:my\s+)?(?:hair|buhok)\b",
                r"\b(?:ganda|gumanda|gumaganda)\s+(?:ng|ang|na)?\s*(?:buhok|hair)\b",
            ],
            [],
        )
    },
)
SKIN = _patch(
    SKIN,
    {
        "texture": ([], [r"\bwhite\s+cast\b"]),
        # "effective for sensitive, dry and oily face": oily is the skin type the product suits, not a complaint.
        "oiliness": ([], [], r"\b(?:for|suitable\s+for|good\s+for|ideal\s+for|para\s+sa)\b[^.!?]{0,40}\b(?:oily|mamantika)\b|\b(?:dry|sensitive|combination|normal)\s*(?:,|and|at|or)\s*(?:oily|mamantika)\b"),
        "functionality": ([r"\b(?:maganda|ganda|good|effective|ok|okay|nice)\s+(?:siya\s+|sya\s+|diya\s+|cya\s+|po\s+|ito\s+|naman\s+)?(?:sa|for|on)\s+(?:face|mukha|balat|skin|lips?|labi)\b"], []),
    },
    extra=(_DRYNESS,),
)
FOOD = _patch(
    FOOD,
    {
        "taste": ([r"\btastes?\s+(?:so\s+|very\s+|really\s+)?(?:great|good|nice|amazing|delicious|yummy|heavenly)\b"], []),
        "expiry": ([], [r"\bexpir\w*\b[^.!?]{0,30}\b(?:too\s+short|masyadong\s+(?:maikli|malapit)|malapit\s+na)\b", r"\b(?:short|maikli)\s+(?:na\s+)?(?:shelf\s+life|expiry|expiration)\b"]),
    },
    extra=(MIXABILITY,),
)
APPLIANCE = _patch(
    APPLIANCE,
    {
        "performance": (
            [
                r"\b(?:perfect|masarap|malambot)\s+(?:ang\s+)?(?:sinaing|kanin|rice|luto|pagkaluto)\b",
                r"\b(?:rice|kanin)\s+(?:is\s+)?(?:perfect|perfectly\s+cooked|malambot|masarap)\b",
                r"\b(?:crispy|crisp)\s+(?:ang\s+|na\s+)?(?:fries|chicken|food|luto)\b",
            ],
            [r"\bmatagal\s+(?:mag-?cook|magluto|maluto|uminit|mag-?init|kumulo|mag-?saing|magsaing)\b"],
        )
    },
)

# Found on real cheese, shampoo and cleanser reviews: "build quality" and "durability" are the wrong words for something you eat or
# wash with. These profiles say "overall quality" and do not read durability at all ("long-lasting fragrance" is not durability).
_OVERALL_QUALITY = replace(BUILD, label="overall quality")
HAIR, SKIN, FOOD = HAIR + (_OVERALL_QUALITY,), SKIN + (_OVERALL_QUALITY,), FOOD + (_OVERALL_QUALITY,)
EXCLUDE_GENERAL: dict[str, frozenset[str]] = {"hair": frozenset({"durability"}), "skin": frozenset({"durability"}), "food": frozenset({"durability"}), "supplements": frozenset({"durability"})}


# Narrow, experimental profiles: avoid applying apparel, snack and device
# cues to unrelated categories. Test on fresh real reviews before deployment.
BAGS = (
    Aspect(
        "storage",
        "storage capacity",
        pos=_re([
            r"\b(?:spacious|roomy|maluwag\s+(?:ang|yung)\s+(?:bag|loob)|maraming\s+(?:bulsa|pockets?|compartments?))\b",
        ]),
        neg=_re([
            r"\b(?:kulang\s+(?:ang|sa)\s+(?:space|storage|compartments?)|maliit\s+(?:ang\s+)?(?:bag|loob|capacity)|too\s+(?:small|little)\s+(?:for\s+)?(?:my\s+)?(?:things|stuff|items))\b",
        ]),
    ),
    Aspect(
        "zipper",
        "zipper and closures",
        pos=_re([
            r"\b(?:smooth|good|great|matibay|maayos|maganda)\s+(?:ang\s+|na\s+)?(?:zipper|zip|zippers)\b",
        ]),
        neg=_re([
            r"\b(?:broken|stuck|jammed|sira|nasira|sirang|natanggal)\s+(?:ang\s+|na\s+)?(?:zipper|zip|zippers)\b",
            r"\b(?:zipper|zip)\s+(?:is\s+|was\s+)?(?:broken|stuck|jammed|sira)\b",
        ]),
    ),
)
# A bedsheet has fabric characteristics, not clothing fit-and-sizing.
HOME_TEXTILE = (APPAREL[0],)
# Supplements are not snacks: expiry and taste are relevant; food spoilage
# terms and build durability should not be imported.
SUPPLEMENTS = tuple(aspect for aspect in FOOD if aspect.id in {"taste", "expiry"}) + (
    replace(BUILD, label="overall quality"),
)

# Which profile reads which product category (product_category.py names). Anything not listed uses its group's
# profile when there is one, otherwise only the GENERAL aspects.
PROFILES: dict[str, tuple[Aspect, ...]] = {
    "hair": HAIR,
    "skin": SKIN,
    "phone": PHONE,
    "earbuds": EARBUDS,
    "powerbank": POWERBANK,
    "apparel": APPAREL,
    "bags": BAGS,
    "home_textile": HOME_TEXTILE,
    "supplements": SUPPLEMENTS,
    "footwear": FOOTWEAR,
    "food": FOOD,
    "appliance": APPLIANCE,
    "motorcycle": MOTORCYCLE,
    "general": (),
}
CATEGORY_PROFILE = {
    "haircare": "hair",
    "skincare": "skin",
    "makeup": "skin",
    "personal_care": "skin",
    "phone": "phone",
    "tablet": "phone",
    "audio": "earbuds",
    "powerbank": "powerbank",
    "charger_cable": "general",
    "battery_solar": "general",
    "apparel": "apparel",
    "bags": "bags",
    "eyewear": "general",
    "home_textile": "home_textile",
    "footwear": "footwear",
    "food_beverage": "food",
    "health_supplements": "supplements",
    "small_appliance": "appliance",
    "kitchen_dining": "general",
    "tv_display": "general",
    "household_cleaning": "general",
    "motorcycle": "motorcycle",
    "automotive": "general",
}
# What to call the product in a sentence. A category name never tells us the exact product ("haircare" is a
# shampoo, a conditioner or a mask), so the noun is deliberately the category's plain word, and plural where English is.
NOUNS: dict[str, tuple[str, bool]] = {
    "hair": ("hair product", False),
    "skin": ("skin or beauty product", False),
    "phone": ("phone", False),
    "earbuds": ("audio product", False),
    "powerbank": ("power product", False),
    "apparel": ("item", False),
    "bags": ("bag", False),
    "home_textile": ("home textile", False),
    "supplements": ("supplement", False),
    "footwear": ("pair of shoes", False),
    "food": ("food product", False),
    "appliance": ("appliance", False),
    "motorcycle": ("part", False),
    "general": ("product", False),
}
CATEGORY_NOUN = {
    "haircare": ("hair product", False),
    "skincare": ("skin care product", False),
    "makeup": ("makeup product", False),
    "phone": ("phone", False),
    "tablet": ("tablet", False),
    "audio": ("audio device", False),
    "powerbank": ("power bank", False),
    "charger_cable": ("charger or cable", False),
    "apparel": ("clothing item", False),
    "bags": ("bag", False),
    "home_textile": ("home textile", False),
    "health_supplements": ("supplement", False),
    "footwear": ("pair of shoes", False),
    "food_beverage": ("food product", False),
    "small_appliance": ("appliance", False),
    "kitchen_dining": ("kitchen item", False),
    "tv_display": ("display", False),
    "motorcycle": ("motorcycle part", False),
    "automotive": ("auto part", False),
}

GROUP_PROFILE = {
    "food_grocery": "food",
}


def profile_key(category: str | None, group: str | None) -> str:
    if category and category in CATEGORY_PROFILE:
        return CATEGORY_PROFILE[category]
    if group and group in GROUP_PROFILE:
        return GROUP_PROFILE[group]
    return "general"


_CACHE: dict[str, tuple[Aspect, ...]] = {}


def aspects_for(category: str | None, group: str | None) -> tuple[Aspect, ...]:
    """The aspects read for this kind of product: the profile's own first, then the general ones it does not replace."""
    key = profile_key(category, group)
    if key not in _CACHE:
        own = PROFILES[key]
        taken = {aspect.id for aspect in own}
        _CACHE[key] = own + tuple(aspect for aspect in GENERAL if aspect.id not in taken and aspect.id not in EXCLUDE_GENERAL.get(key, ()))
    return _CACHE[key]


def noun_for(category: str | None, group: str | None) -> str:
    if category and category in CATEGORY_NOUN:
        return CATEGORY_NOUN[category][0]
    return NOUNS[profile_key(category, group)][0]


# --- reading rules shared by every aspect ---------------------------------------------------------------------------
NEGATORS = frozenset(
    "hindi di d hnd hnde ndi wala walang walay wla hinde no not never without isnt isn't wasnt wasn't doesnt doesn't "
    "didnt didn't dont don't cant can't cannot wont won't aint ain't nor neither".split()
)
# A clause that only wonders, hopes or recalls what the reviewer feared is not a report of what happened.
HYPOTHETICAL = re.compile(
    r"\b(?:akala\s+ko|kala\s+ko|i\s+thought|i\s+was\s+(?:afraid|worried|scared|expecting)|baka|nag-?alala|worried|afraid|"
    r"expect\w*|sana|kung|if|hopefully|hoping|hope|maybe|perhaps|(?:not|haven't|hasn't|havent|hasnt)\s+(?:been\s+|yet\s+)?tested|(?:di|hindi)\s+pa\s+(?:na-?)?(?:test|try)\w*|in\s+case|just\s+in\s+case|paano\s+kung|what\s+if|nakakatakot\s+baka"
    # "some people MAY experience skin irritation": a warning about what could happen, not what happened to this reviewer.
    r"|(?:some\s+people|some\s+users?|others|people|users?|anyone)\s+(?:may|might|can|could)|(?:may|might|could)\s+(?:experience|cause|irritate|trigger|have)|\bmight\b)\b",
    re.I,
)
# What the reviewer usually does is not what this product did ("i only ever buy affordable smartwatches").
HABIT = re.compile(r"\b(?:i\s+(?:only\s+)?(?:ever\s+|always\s+|usually\s+|normally\s+)?(?:buy|buys|bought|prefer|use)|palagi\s+akong|lagi\s+akong|madalas\s+akong)\b", re.I)
# Advertising left as a review. It praises a loan, not the product.
PROMOTION = re.compile(r"\b(?:gloan|installments?|loan|promo\s+code|voucher\s+code|follow\s+(?:us|me)|whatsapp|telegram|add\s+me|dm\s+me|click\s+(?:the\s+)?link|bit\.ly)\b", re.I)
# A prompt the marketplace puts in front of a review field ("Sound Quality:", "Value for money:"). The label is not the buyer's claim.
PROMPT_LABEL = re.compile(r"\b[A-Z][A-Za-z/&]*(?:\s+[A-Za-z/&]+){0,3}:(?=\s*\S)")
COMPARISON = re.compile(
    r"\bas\s+\w+\s+as\s+(?:this|that|the|my|other|others|before|dati)\b|\b(?:than|compared\s+(?:to|with)|kumpara|kesa|kaysa|better\s+than|worse\s+than|same\s+as\s+(?!(?:in\s+)?(?:the\s+)?(?:picture|pictures|photo|photos|pic|pics|advertised|described|listed|description|listing|ad)\b)|kasing|mas\s+(?:maganda|ok|okay|mabuti|mahina|pangit|malakas|mabilis|mabango|malambot))\b",
    re.I,
)
SARCASM = re.compile(r"\b(?:yeah\s+right|as\s+if|sure\s+ka|talaga\s+lang|sana\s+all|/s)\b|\bwow\b[^.!?]{0,25}\b(?:sira|sayang|nasira|broken|fake)\b", re.I)
# The reviewer has not used it, so they cannot have a product opinion yet. (A damaged parcel can still be reported.)
NO_EXPERIENCE = re.compile(
    r"\b(?:hindi|di|d|hnd|not|haven'?t|havent|wala)\s+(?:ko\s+)?(?:pa\s+)?(?:natry|natri|nasubukan|nagamit|nagagamit|nasusubukan|nata-?try|try|tried|used|use|tested|na-?test)\b"
    r"|\b(?:yet\s+to|will|try\s+ko|subukan\s+ko|gamitin\s+ko)\s+(?:pa\s+)?(?:try|use|test|gamitin|subukan)?\b"
    r"|\b(?:try\s+ko\s+pa|subukan\s+ko\s+pa|gamitin\s+ko\s+pa|review\s+(?:ko\s+)?muna|stars?\s+muna|rate\s+muna|just\s+received|just\s+arrived|kakadating|kararating|kakarating|pa\s+lang\s+(?:natanggap|dumating))\b",
    re.I,
)
# "Nawala ang rashes" names a problem to say it is gone. Found by a manual audit of an anti-hair-fall shampoo: "less hairfall", "effective for hair
# fall", "helping with hair fall", "anti-hair loss" were all counted as complaints. A product whose purpose is the problem (anti-hair-fall,
# anti-dandruff, anti-acne) names it constantly in praise, so words that say it is lessened, stopped, fought or treated count as relief.
RELIEF = re.compile(
    r"\b(?:nawala|nawawala|nabawasan|bumaba|gumaling|nagamot|clear\w*|reduc\w*|remov\w*|cure\w*|heal\w*|fights?|prevent\w*|control\w*|bawas\w*|goodbye|walang\s+na|stopped?|stops?"
    r"|less|fewer|anti|helps?|helping|helped|improv\w*|solution|tinanggal|natanggal|wala\s+nang|no\s+more|hindi\s+na|effective\s+(?:for|against|in)|good\s+for|works?\s+(?:for|on|against)|mas\s+less)\b",
    re.I,
)
POSITIVE_EMOJI = re.compile("[\U0001F60D\U0001F44D\U0001F4AF❤\U0001F970\U0001F60A\U0001F929\U0001F44F\U0001F44C✨\U0001F496\U0001F495]")
NEGATIVE_EMOJI = re.compile("[\U0001F44E\U0001F621\U0001F620\U0001F92E\U0001F624\U0001F61E\U0001F622\U0001F494\U0001F62D\U0001F92C\U0001F974]")
