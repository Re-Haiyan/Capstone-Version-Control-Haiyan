"""Data helpers shared by the web app and its tests."""

from __future__ import annotations

import copy
import csv
import io
import json
import math
import os
import re
import sys
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

import aspects as aspect_evidence
import category_copy
import conclusion_text


ROOT = Path(__file__).resolve().parent


def search_slug(keyword: str) -> str:
    slug = re.sub(r"[^a-z0-9_]+", "_", keyword.lower()).strip("_")
    return slug or "search"


PLATFORM_NAMES = {"shopee": "Shopee PH", "lazada": "Lazada PH", "temu": "Temu PH"}

RECOMMENDATION_STOP_WORDS = {
    "a", "an", "and", "for", "from", "in", "more", "new", "of", "on",
    "original", "series", "the", "to", "with",
    # Words every gadget name uses. Two names sharing "smart", "wifi" and
    # "home" are not two of the same thing: a door lock was offered a WiFi
    # router on those three words (13 Oct 2026).
    "adjustable", "bluetooth", "fast", "hd", "high", "home", "led", "max",
    "mini", "plus", "portable", "pro", "professional", "quality",
    "rechargeable", "smart", "super", "ultra", "universal", "waterproof",
    "wifi", "wireless",
    # What a product works with, which half the catalogue lists: a stylus was
    # offered a mouse on "iPad", "tablet" and "phone" (13 Oct 2026).
    "android", "cellphone", "computer", "desktop", "device", "devices", "ios",
    "ipad", "iphone", "mobile", "pc", "phone", "phones", "smartphone", "tablet",
}

RECOMMENDATION_PART = "part"
RECOMMENDATION_CASE = "case"
RECOMMENDATION_PHONE = "phone"
# Devices where the brand matters as much as the kind: an iPad suits an iPad buyer.
RECOMMENDATION_BRANDED_DEVICES = ("phone", "tablet", "laptop", "smartwatch", "console", "tv", "earbuds")
# Kinds that fit one device. Two of them are alike only when they are for the
# same model: a case for a Galaxy A07 is no alternative to one for a Realme
# C21Y, however alike the two names read.
RECOMMENDATION_FITS_ONE_DEVICE = (RECOMMENDATION_PART, RECOMMENDATION_CASE)

# The kinds of product a name is read for: (words, label, kind). A name often
# holds several ("Laptop Stand ... Monitor Lifter", "Speaker with Microphone");
# _recommendation_type says which one the product is.
RECOMMENDATION_PRODUCT_TYPES = (
    (("power bank", "powerbank", "portable charger"), "power bank", "powerbank"),
    (("helmet intercom", "motorcycle intercom", "intercom headset"), "helmet intercom", "intercom"),
    (("doorbell",), "doorbell", "doorbell"),
    (("vr box", "vr glasses", "vr headset", "virtual reality"), "VR headset", "vr"),
    (("usb hub", "usb c hub", "usb-c hub", "port hub"), "USB hub", "hub"),
    (
        ("ethernet cable", "lan cable", "network cable", "rj45", "cat6", "cat 6", "cat5e"),
        "network cable",
        "network cable",
    ),
    (("wireless charger", "watch charger", "charging pad", "charging dock"), "wireless charger", "wireless charger"),
    (("smart lock", "door lock"), "door lock", "lock"),
    (("router", "home wifi", "pocket wifi", "modem"), "router", "router"),
    (
        ("phone case", "case for", "shockproof case", "back cover", "tempered glass", "screen protector"),
        "phone case",
        RECOMMENDATION_CASE,
    ),
    (
        (
            "laptop stand", "notebook stand", "monitor stand", "tablet stand", "phone stand", "universal stand",
            "headphone stand", "headset stand", "microphone stand", "mic stand", "speaker stand",
        ),
        "stand",
        "stand",
    ),
    (("wireless earbuds", "earbud", "earphone", "tws"), "wireless earbuds", "earbuds"),
    (("headphones", "headphone", "headset"), "headphones", "headphones"),
    (("microphone",), "microphone", "microphone"),
    (
        # Apple and Samsung sell theirs as a "USB-C Power Adapter", with no "charger" in the name.
        ("wall charger", "charger", "charging adapter", "usb-c power adapter", "usb c power adapter", "usb power adapter"),
        "charger",
        "charger",
    ),
    (("usb cable", "charging cable", "cable"), "cable", "cable"),
    (("mechanical keyboard", "keyboard"), "keyboard", "keyboard"),
    (("gaming mouse", "wireless mouse", "mouse"), "mouse", "mouse"),
    (
        ("smart watch", "smartwatch", "sport watch", "sports watch", "fitness watch", "digital watch"),
        "smart watch",
        "smartwatch",
    ),
    (("bluetooth speaker", "speaker"), "speaker", "speaker"),
    (("monitor",), "monitor", "monitor"),
    (("laptop",), "laptop", "laptop"),
    (("camera",), "camera", "camera"),
    (
        ("lcd for", "lcd replacement", "replacement lcd", "screen replacement", "touch screen", "digitizer"),
        "replacement part",
        RECOMMENDATION_PART,
    ),
)
# Kinds that are named after another product and are never that product: a
# "laptop power bank", a "helmet intercom headset", a "doorbell with camera",
# a "VR headset", a "USB hub for laptop", an "ethernet cable", a "wireless
# charger", a "laptop stand". One of these wins over the ordinary kinds that
# follow it in the name. An ordinary kind named before it wins instead: a
# "Speaker Power Bank with Phone Stand" is sold as a speaker.
RECOMMENDATION_COMPOUND_KINDS = (
    "powerbank", "intercom", "doorbell", "vr", "hub", "network cable", "wireless charger", "lock", "router",
    RECOMMENDATION_CASE, "stand",
)
# Kinds whose words mostly describe something else ("laptop mouse", "monitor
# lifter", "touch screen"): the product is one of these only when its name
# holds no other kind.
RECOMMENDATION_LAST_RESORT_KINDS = ("monitor", "laptop", RECOMMENDATION_PART)
# "Speaker with Microphone", "Doorbell with 1 Camera": what follows "with" is
# something the product has, not what it is.
_COMES_WITH = re.compile(r"(?:\bwith|\bw/)\s+(?:\S+\s+){0,2}$")
# "... for Laptop", "... compatible with Monitors": what a product is for.
_MADE_FOR = re.compile(r"\s(?:for|with|compatible)\s")
# Devices that are known by a brand and model: (kind, pattern). Only the START of a
# name counts, so "USB C cable for iPhone 15" is a cable and "iPad Pro Keyboard
# Case" is not a tablet. The words "iphone", "ipad" and "tablet" are stop words
# (half the catalogue lists what it works with), so without this a phone or a
# tablet had no kind and matched nothing but its brand. Tablets come before
# phones because "Galaxy Tab" and "Redmi Pad" would otherwise read as phones.
_NAME_START = r"^[\W_]*(?:(?:brand\s+new|new|apple|authentic|original|official|sealed)\s+)*"
RECOMMENDATION_DEVICE_NAMES = tuple(
    (kind, re.compile(_NAME_START + pattern))
    for kind, pattern in (
        ("tablet", r"(?:ipad|samsung\s+galaxy\s+tab|galaxy\s+tab|redmi\s+pad|xiaomi\s+(?:redmi\s+)?pad|"
                   r"lenovo\s+(?:tab|idea\s?tab|yoga\s+tab)|huawei\s+(?:matepad|mediapad)|matepad|"
                   r"oppo\s+pad|realme\s+pad|honor\s+pad|amazon\s+fire\s+(?:hd|tablet)|microsoft\s+surface\s+(?:go|pro)|"
                   r"android\s+tablet|kids\s+tablet|\d{1,2}(?:\.\d)?\s?(?:inch|in|\")\s+(?:android\s+)?tablet)"),
        ("phone", r"(?:iphone\s?\d|iphone\s?(?:se|x[rs]?)\b|samsung\s+galaxy\s+[a-z]{0,2}\d|galaxy\s+[a-z]{0,2}\d|"
                  r"galaxy\s+z\s|(?:xiaomi\s+)?redmi\s+(?:note\s+)?\d|(?:xiaomi\s+)?redmi\s|xiaomi\s+(?:mi\s+)?\d|poco\s+[a-z]\d|"
                  r"realme\s+(?:gt\s+|narzo\s+|c|\d)|oppo\s+(?:reno|find|[a-z]\d)|vivo\s+(?:[a-z]\s?\d|v\d|y\d)|"
                  r"infinix\s|tecno\s|itel\s|honor\s+(?:magic|x\d|\d)|google\s+pixel\s?\d|"
                  r"huawei\s+(?:nova|p\d|mate\s?\d)|oneplus\s|nothing\s+phone|motorola\s+(?:moto|edge)|moto\s+[a-z]\d|"
                  r"sony\s+xperia|asus\s+(?:rog\s+phone|zenfone)|zte\s+(?:blade|nubia)|cherry\s+mobile|myphone|symphony)"),
        ("laptop", r"(?:macbook|lenovo\s+(?:thinkpad|ideapad|legion|loq|yoga)|thinkpad|ideapad|asus\s+(?:vivobook|zenbook|tuf|rog)|"
                   r"vivobook|zenbook|acer\s+(?:aspire|nitro|swift|predator)|hp\s+(?:pavilion|envy|spectre|omen|victus)|"
                   r"dell\s+(?:inspiron|latitude|xps|vostro|alienware)|msi\s+(?:katana|cyborg|thin|modern)|"
                   r"huawei\s+matebook|matebook|chromebook|surface\s+laptop|gaming\s+laptop)"),
        ("smartwatch", r"(?:apple\s+watch|galaxy\s+watch|samsung\s+watch|huawei\s+(?:watch|band)|amazfit|garmin|"
                       r"redmi\s+watch|xiaomi\s+(?:watch|smart\s+band|mi\s+band)|mi\s+band|smart\s?band|fitbit|"
                       r"realme\s+watch|oppo\s+watch|imilab|haylou|colmi|kieslect)"),
        ("earbuds", r"(?:airpods|galaxy\s+buds|samsung\s+buds|redmi\s+buds|xiaomi\s+buds|huawei\s+freebuds|freebuds|"
                    r"oppo\s+enco|realme\s+buds|jbl\s+(?:tune|wave|live)\s+(?:buds|flex)|sony\s+wf|anker\s+soundcore)"),
        ("console", r"(?:playstation|ps[45]\b|nintendo\s+switch|switch\s+oled|xbox|steam\s+deck|rog\s+ally|"
                    r"gameboy|game\s?boy|retro\s+game\s+console)"),
        ("tv", r"(?:(?:samsung|lg|tcl|sony|hisense|xiaomi|philips|panasonic|skyworth|devant|haier|aiwa|coocaa)\s+)?(?:(?:smart\s+)?(?:android\s+)?(?:led\s+|4k\s+|uhd\s+)*tv\s+\d|\d{2}(?:\s?inch|\s?\")\s+(?:smart\s+|android\s+|led\s+|4k\s+|uhd\s+)*tv\b|"
                "samsung\s+(?:crystal|qled|the\s+frame)|lg\s+(?:oled|nanocell|uhd)|tcl\s+(?:\d|android|google))"),
        ("camera", r"(?:gopro|go\s?pro|canon\s+(?:eos|powershot)|nikon\s+(?:d\d|z\s?\d)|sony\s+(?:alpha|a\d|zv)|"
                   r"fujifilm|instax|dji\s+(?:osmo|pocket|action)|insta360)"),
    )
)
# Words that make a name an accessory for one of those devices, not the device.
_DEVICE_ACCESSORY = re.compile(
    r"\b(?:case|cases|cover|protector|tempered|glass|cable|charger|adapter|holder|stand|lcd|screen|strap|"
    r"earphones?|earbuds?|headset|power\s?bank|film|lens|pencil|stylus|pen|keyboard|sleeve|bag|pouch|skin|sticker|"
    r"mount|tripod|replacement|dock|hub|band\s+for|bands?|straps?|controller|gamepad|remote|bracket|"
    r"cleaner|cleaning|wipes?|stand|folio|compatible|fits)\b"
)
# "8+256", "8GB+256GB": memory and storage, which only a phone or tablet lists.
_MEMORY_AND_STORAGE = re.compile(r"\b\d{1,2}\s?(?:gb)?\s?\+\s?\d{2,4}\s?(?:gb)?\b")


def detect_marketplace(value: str, default: str = "shopee") -> str:
    """Detect a supported marketplace from a URL, otherwise use the chosen default."""
    parsed = urlsplit(str(value).strip())
    host = parsed.netloc.casefold().split(":", 1)[0]
    if host == "shopee.ph" or host.endswith(".shopee.ph"):
        return "shopee"
    if host == "lazada.com.ph" or host.endswith(".lazada.com.ph"):
        return "lazada"
    if host == "temu.com" or host.endswith(".temu.com"):
        return "temu"
    if parsed.scheme in {"http", "https"} and host:
        raise ValueError("Only Shopee PH, Lazada PH, and Temu product links are supported.")
    return default if default in PLATFORM_NAMES else "shopee"


def product_platform(product: dict[str, Any]) -> str:
    platform = str(product.get("platform") or "").strip().casefold()
    if platform not in PLATFORM_NAMES:
        try:
            platform = detect_marketplace(str(product.get("link") or ""))
        except ValueError:
            # Backward-compatible fallback for imported research fixtures whose
            # source predates platform metadata.
            platform = "shopee"
    return platform


def platform_name(product: dict[str, Any]) -> str:
    return PLATFORM_NAMES[product_platform(product)]


def output_path(keyword: str, platform: str = "shopee") -> Path:
    platform = platform if platform in PLATFORM_NAMES else "shopee"
    return ROOT / f"{platform}_ph_{search_slug(keyword)}.json"


def result_files() -> list[Path]:
    return sorted(
        (
            path
            for pattern in ("shopee_ph_*.json", "lazada_ph_*.json", "temu_ph_*.json")
            for path in ROOT.glob(pattern)
            if not path.stem.endswith("_analyzed")
        ),
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    )


def load_products(source: str | Path | bytes) -> list[dict[str, Any]]:
    if isinstance(source, bytes):
        data = json.loads(source.decode("utf-8-sig"))
    else:
        with Path(source).open("r", encoding="utf-8-sig") as file:
            data = json.load(file)
    if isinstance(data, dict):
        data = data.get("products", [])
    if not isinstance(data, list):
        raise ValueError("The JSON must be a product list or contain a 'products' list.")
    return [item for item in data if isinstance(item, dict)]


def has_usable_products(products: list[dict[str, Any]]) -> bool:
    """Return whether a scraper result contains real listing or review data."""
    return any(
        str(product.get("name") or "").strip()
        or bool(product.get("comments"))
        or product.get("review_status") in {"complete", "no_reviews"}
        for product in products
    )


def cached_product_matches(
    products: list[dict[str, Any]], query: str, limit: int = 6
) -> list[dict[str, Any]]:
    """Find analyzed products without making a marketplace request."""
    value = str(query or "").strip()
    if not value or limit <= 0:
        return []
    parsed = urlsplit(value)
    if parsed.scheme in {"http", "https"} and parsed.netloc:
        target = (parsed.netloc.casefold().removeprefix("www."), parsed.path.rstrip("/").casefold())
        matches = []
        for product in products:
            product_url = urlsplit(str(product.get("link") or ""))
            identity = (
                product_url.netloc.casefold().removeprefix("www."),
                product_url.path.rstrip("/").casefold(),
            )
            if identity == target:
                matches.append(product)
        return matches[:limit]

    terms = re.findall(r"[a-z0-9]+", value.casefold())
    if not terms:
        return []
    ranked = []
    for index, product in enumerate(products):
        name = str(product.get("name") or "").casefold()
        overlap = sum(term in name for term in terms)
        if overlap:
            exact_phrase = int(value.casefold() in name)
            ranked.append((exact_phrase, overlap / len(terms), product_reliability(product), -index, product))
    ranked.sort(key=lambda item: item[:4], reverse=True)
    return [item[-1] for item in ranked[:limit]]


def merge_product_catalogs(*catalogs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Merge analyzed catalogs while preserving the first version of each listing."""
    merged: list[dict[str, Any]] = []
    seen: set[tuple[str, str] | tuple[str, str, str]] = set()
    for catalog in catalogs:
        for product in catalog or []:
            if not isinstance(product, dict):
                continue
            parsed = urlsplit(str(product.get("link") or ""))
            if parsed.netloc and parsed.path:
                identity: tuple[str, str] | tuple[str, str, str] = (
                    parsed.netloc.casefold().removeprefix("www."),
                    parsed.path.rstrip("/").casefold(),
                )
            else:
                identity = (
                    "name",
                    str(product.get("platform") or "").casefold(),
                    str(product.get("name") or "").strip().casefold(),
                )
            if identity in seen:
                continue
            seen.add(identity)
            merged.append(product)
    return merged


def _recommendation_brand(product: dict[str, Any]) -> str:
    brand = str(product.get("brand") or "").strip()
    if brand:
        return brand
    name_terms = [
        term for term in re.findall(r"[A-Za-z0-9]+", str(product.get("name") or ""))
        if term.casefold() not in RECOMMENDATION_STOP_WORDS
    ]
    return name_terms[0] if name_terms else ""


def _recommendation_terms(product: dict[str, Any]) -> set[str]:
    text = " ".join(
        str(product.get(field) or "").casefold()
        for field in ("name", "category", "brand")
    )
    terms = {
        term for term in re.findall(r"[a-z0-9]+", text)
        if term not in RECOMMENDATION_STOP_WORDS
    }
    if "powerbank" in terms or {"power", "bank"}.issubset(terms):
        terms.add("powerbank")
    product_type = _recommendation_type(product)
    if product_type:
        terms.add(product_type)
    return terms


def _recommendation_type(product: dict[str, Any]) -> str:
    """The kind of product a listing is, read from its name and category.

    A name leads with what the thing is and goes on to what it has or fits, so
    of the ordinary kinds the one named first wins, and a kind that only comes
    "with" the product is passed over while the name holds another:
    "Microphone ... Speaker" is a microphone, "Speaker with Microphone" a
    speaker. Two groups are exceptions (see the two tuples above). Before
    13 Oct 2026 the first kind in the list won, which read a laptop stand with
    a "monitor lifter" as a monitor and a helmet intercom headset as
    headphones.
    """
    text = " ".join(
        str(product.get(field) or "").casefold()
        for field in ("name", "category")
    )
    # What a device comes with ("... with Case and Charger", "+ free earphones") is not
    # what it is, so only the words before that are read for an accessory.
    head = re.split(r"\bwith\b|\bw/|\bfree\b|\bincludes?\b|\bbundle\b|\+", text)[0]
    if not _DEVICE_ACCESSORY.search(head):
        # "Apple iPhone 16", "iPad Air 5", "Galaxy Tab A9": known by name alone.
        for device_kind, pattern in RECOMMENDATION_DEVICE_NAMES:
            if pattern.search(text):
                return device_kind
    if _MEMORY_AND_STORAGE.search(text):
        # A phone sold with a charger and earphones is still a phone; with
        # "tablet" or "pad" in the name it is a tablet.
        return "tablet" if re.search(r"\b(?:tablet|pad|tab)\b", text) and "phone" not in text else RECOMMENDATION_PHONE

    def first_seen(skip_what_it_comes_with: bool) -> dict[str, int]:
        found: dict[str, int] = {}
        for variants, _label, canonical in RECOMMENDATION_PRODUCT_TYPES:
            positions = [
                match.start()
                for variant in variants
                for match in re.finditer(re.escape(variant), text)
                if not (skip_what_it_comes_with and _COMES_WITH.search(text[: match.start()]))
            ]
            if positions:
                found[canonical] = min(positions)
        return found

    # A name that holds nothing but what the product comes with is read by that.
    seen = first_seen(True) or first_seen(False)
    ordinary = [
        kind for kind in seen
        if kind not in RECOMMENDATION_COMPOUND_KINDS and kind not in RECOMMENDATION_LAST_RESORT_KINDS
    ]
    leading = min((seen[kind] for kind in ordinary), default=len(text))
    for canonical in RECOMMENDATION_COMPOUND_KINDS:
        if canonical in seen and seen[canonical] <= leading:
            return canonical
    if ordinary:
        # The dict keeps the list's order, which settles a tie.
        return min(ordinary, key=lambda kind: seen[kind])
    made_for = _MADE_FOR.search(text)
    for canonical in RECOMMENDATION_LAST_RESORT_KINDS:
        # "USB adapter for laptop" is not a laptop: the word must lead the name.
        leads = canonical == RECOMMENDATION_PART or not made_for or seen.get(canonical, 0) < made_for.start()
        if canonical in seen and leads:
            return canonical
    return ""


def _model_codes(product: dict[str, Any]) -> set[str]:
    """Model numbers in a name: words that start with a letter and hold a digit.

    "rmx3834", "a07", "c21y". A word that starts with a digit is a quantity
    far more often than a model ("4in1", "30w", "5g", "20000mah"), and two
    listings sharing "4in1" are not for the same phone.
    """
    return {
        term for term in re.findall(r"[a-z0-9]+", str(product.get("name") or "").casefold())
        if term[0].isalpha() and any(character.isdigit() for character in term)
    }


def rank_recommendations(
    product: dict[str, Any],
    products: list[dict[str, Any]],
    limit: int = 3,
    min_positive_ratio: float = 0.5,
    min_review_count: int = 5,
) -> list[dict[str, Any]]:
    """Up to `limit` similar products with no warning signs.

    The strict pass comes first. When it finds fewer than `limit`, a looser
    pass fills the rest (a product whose kind the name list cannot read, a
    slightly lower rating), so a product is not left with nothing while
    similar safe ones exist. The loose pass never relaxes the safety rule: a
    candidate still needs the "no warning signs" verdict and zero safety
    reports.
    """
    if limit <= 0:
        return []
    picked = _rank_recommendations(product, products, limit, min_positive_ratio, min_review_count, loose=False)
    if len(picked) < limit:
        have = {str(item.get("link") or "") for item in picked}
        loose = _rank_recommendations(
            product, products, limit, min(min_positive_ratio, 0.4), min(min_review_count, 3), loose=True
        )
        picked += [item for item in loose if str(item.get("link") or "") not in have]
    return picked[:limit]


def _rank_recommendations(
    product: dict[str, Any],
    products: list[dict[str, Any]],
    limit: int,
    min_positive_ratio: float,
    min_review_count: int,
    loose: bool,
) -> list[dict[str, Any]]:
    """Rank similar products whose reviews show no warning signs.

    Only products analysed with the badge model qualify: a legacy risk score
    cannot vouch for a product under the current checks. A candidate needs the
    "no warning signs" verdict -- which already requires enough reviews -- and
    not a single safety report, because suggesting a product with a fire report
    as the safer choice would be worse than suggesting nothing. Candidates rank
    by similarity, then by the lower bound of their positive-review ratio,
    which discounts products whose praise rests on a small sample.
    """
    if limit <= 0:
        return []
    target_terms = _recommendation_terms(product)
    target_type = _recommendation_type(product)
    target_codes = _model_codes(product)
    target_category = str(product.get("category") or "").strip().casefold()
    target_brand = _recommendation_brand(product).casefold()
    ranked: list[tuple[float, float, int, int, dict[str, Any]]] = []
    for index, candidate in enumerate(products):
        if candidate.get("link") == product.get("link"):
            continue
        summary = candidate.get("sentiment_summary") or {}
        if not is_badge_summary(summary):
            continue
        view = badge_view(candidate)
        if view["state"] != "no_warning_signs" or view["counts"]["safety"]:
            continue
        positive = float(summary.get("positive_ratio_lower_bound") or 0)
        review_count = view["reviews_analyzed"]
        rating = rating_value(candidate.get("rating"))
        if (
            positive < min_positive_ratio
            or review_count < min_review_count
            or (rating is not None and rating < (3.5 if loose else 4.0))
        ):
            continue

        candidate_terms = _recommendation_terms(candidate)
        candidate_type = _recommendation_type(candidate)
        if target_type != candidate_type:
            # Also when only one of the two has a kind the list knows: a name
            # that says "mouse" and one that does not are not both mice.
            continue
        if (
            target_type in RECOMMENDATION_FITS_ONE_DEVICE
            and candidate_type == target_type
            and not (target_codes & _model_codes(candidate))
        ):
            # A replacement part or a case fits one device. An LCD for another
            # phone is not an alternative, however alike the two names are.
            continue
        overlap = target_terms & candidate_terms
        if loose and not target_type:
            # Two products whose kind the list cannot read (so no kind to
            # compare) are matched on their words: three real shared words,
            # not "men" and "s" from "Men's", and a shared category is not
            # enough by itself. Shared words like "fast" or "charging" alone
            # offered a stylus pen for a power bank.
            overlap = {term for term in overlap if len(term) > 2 and term not in {"men", "women", "pcs", "set"}}
            if len(overlap) < 3:
                continue
        candidate_category = str(candidate.get("category") or "").strip().casefold()
        category_match = bool(target_category and target_category == candidate_category)
        type_match = bool(target_type and target_type == candidate_type)
        lexical_similarity = len(overlap) / max(1, min(len(target_terms), len(candidate_terms)))
        if not category_match and not type_match and (
            len(overlap) < 3 or lexical_similarity < (0.25 if loose else 0.35)
        ):
            continue
        brand_match = bool(
            target_brand and target_brand == _recommendation_brand(candidate).casefold()
        )
        similarity = min(
            1.0,
            lexical_similarity + (0.25 if category_match else 0) + ((0.2 if target_type in RECOMMENDATION_BRANDED_DEVICES else 0.08) if brand_match else 0),
        )
        evidence = min(1.0, math.log10(review_count + 1) / 2)
        recommendation_score = 0.6 * similarity + 0.3 * positive + 0.1 * evidence
        ranked.append((recommendation_score, positive, review_count, -index, candidate))
    ranked.sort(key=lambda item: item[:4], reverse=True)
    return [item[-1] for item in ranked[:limit]]


def price_value(value: Any) -> float | None:
    text = str(value or "").replace("â‚±", "₱")
    numbers = re.findall(r"\d[\d,]*(?:\.\d+)?", text)
    if not numbers:
        return None
    parsed = [float(number.replace(",", "")) for number in numbers[:2]]
    return sum(parsed) / len(parsed)


def rating_value(value: Any) -> float | None:
    try:
        rating = float(value)
    except (TypeError, ValueError):
        return None
    return rating if 0 <= rating <= 5 else None


def product_rows(products: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows = []
    for product in products:
        comments = product.get("comments")
        view = badge_view(product)
        rows.append(
            {
                "Image": product.get("img", ""),
                "Product": product.get("name", ""),
                "Price": str(product.get("price", "")).replace("â‚±", "₱"),
                "Price (PHP)": price_value(product.get("price")),
                "Rating": rating_value(product.get("rating")),
                "Reviews": len(comments) if isinstance(comments, list) else 0,
                "Total ratings": int(product.get("total_rating") or 0),
                "Location": product.get("location", ""),
                "Platform": platform_name(product),
                "Result": view["headline"],
                "Reviews analyzed": view["reviews_analyzed"],
                "Safety reports": view["counts"]["safety"],
                "Faulty or broken reports": view["counts"]["defect"],
                "Poor quality reports": view["counts"].get("quality"),
                "Possible fake reports": view["counts"]["counterfeit"],
                "Not as advertised reports": view["counts"].get("not_as_described"),
                "Link": product.get("link", ""),
            }
        )
    return rows


def normalized_risk_score(value: Any, scale: Any | None = None) -> float:
    """Return a risk score on 0..1 using explicit units when available.

    Older imported datasets did not record a unit, so their values retain the
    historical heuristic: values above 1 are percentages and values up to 1
    are ratios. New analyses always include ``risk_score_scale`` to remove the
    otherwise unavoidable ambiguity around low percentage scores such as 1.0.
    """
    try:
        score = float(value)
    except (TypeError, ValueError):
        return 0.0
    unit = str(scale or "").strip().casefold()
    if unit in {"percent", "percentage", "0-100"}:
        score /= 100
    elif unit not in {"ratio", "proportion", "fraction", "0-1"} and score > 1:
        score /= 100
    return min(1.0, max(0.0, score))


def reliability_score(
    risk: Any,
    positive_ratio: Any | None = None,
    risk_scale: Any | None = None,
) -> float:
    """Return the manuscript reliability score on a bounded 0..100 scale.

    With a positive ratio this implements Positive Ratio - Risk Score. The
    one-argument form is retained for compatibility with older saved results.
    """
    normalized_risk = normalized_risk_score(risk, risk_scale)
    if positive_ratio is None:
        return round(100 * (1 - normalized_risk), 1)
    try:
        positive = float(positive_ratio)
    except (TypeError, ValueError):
        positive = 0.0
    if positive > 1:
        positive /= 100
    return round(100 * max(0.0, min(1.0, positive) - normalized_risk), 1)


def product_reliability(product: dict[str, Any]) -> float:
    summary = product.get("sentiment_summary") or {}
    positive = (summary.get("sentiment_ratios") or {}).get("positive")
    return reliability_score(
        summary.get("risk_score"), positive, summary.get("risk_score_scale")
    )


# ---------------------------------------------------------------------------
# Badge presentation (summary schema 2.0)
#
# The badge model does not produce a score. It records which reviews mention a
# safety hazard, a counterfeit or a defect, and quotes them. The check is
# imperfect -- on round 1 it caught 21 of 27 confirmed safety reports, and 18
# of its 39 safety flags were harmless -- so the screen shows shoppers the
# reviews and says what they report, rather than asserting that a product is
# safe or unsafe. Everything user-facing about badges is worded here, once.
# ---------------------------------------------------------------------------

BADGE_SCHEMA_PREFIX = "defaketive-summary-2"
EVIDENCE_SHOWN_PER_BADGE = 5

# Held-out figures for the shipped safety check (keyword checker 0.3.0 with the
# learned safety model adopted on labelling round 2): 569 sentences whose safety
# label two annotators agreed on, none seen while either was built. Source:
# research/hazard_tagger_measurement_round2.json, configuration "v4_learned".
SAFETY_CHECK_ACCURACY = {
    "sentences_checked": 569,
    "reports_confirmed": 16,
    "reports_caught": 10,
    "flags_raised": 24,
    "flags_confirmed": 10,
}

# Tone drives colour only. It is never shown as a word.
VERDICT_TONES = {
    "safety_warning": "high",
    "possible_safety_issue": "moderate",
    "possible_counterfeit_or_defect": "moderate",
    "no_warning_signs": "low",
    "insufficient_evidence": "unknown",
    "reviews_may_be_unreliable": "unknown",
}

# Headlines say what reviewers report, never that a product IS unsafe.
VERDICT_HEADLINES = {
    "safety_warning": "Reviewers report safety problems",
    "possible_safety_issue": "Some reviewers mention safety concerns",
    "possible_counterfeit_or_defect": "Reviewers report fakes or defects",
    "reviews_may_be_unreliable": "These reviews may not be trustworthy",
    "insufficient_evidence": "Not enough reviews to judge",
    "no_warning_signs": category_copy.NO_RED_FLAGS,
}

HAZARD_LABELS = {
    "fire_explosion_swelling": "fire, explosion or a swollen battery",
    "shock_spark_short": "electric shocks, sparks or short circuits",
    "overheat_burn": "overheating or burns",
    "smoke_smell": "smoke or a burning smell",
    "safety_unspecified": "a safety problem",
}

# The labels a shopper sees, in the order they are shown, worded once here
# (tagging guide 1.4, Rule 10). A label names what reviewers reported, never a
# finding: "Possible fake", not "Fake". "helper" is the line under the label.
# "verb" is (singular, plural): "1 review says", "3 reviews say".
BADGE_COPY = {
    "safety": {
        "label": "Safety problem",
        "helper": "Overheating, smoke, sparks or shocks",
        "verb": ("mentions", "mention"),
        "none": "No reviews mention fire, smoke, shocks or overheating",
    },
    "defect": {
        "label": "Faulty or broken",
        "helper": "Doesn't work, stops working, drains fast or charges slowly",
        "verb": ("says", "say"),
        "claim": "it is faulty or stopped working",
        "none": "No reviews say it is faulty or broken",
    },
    "quality": {
        "label": "Poor quality",
        "helper": "Works, but weak, flimsy or scratched",
        "verb": ("says", "say"),
        "claim": "it works but is weak, flimsy or marked",
        "none": "No reviews call it weak, flimsy or scratched",
    },
    "counterfeit": {
        "label": "Possible fake",
        "helper": "Reviewers say it is a copy, not the original brand",
        "verb": ("says", "say"),
        "claim": "it may not be genuine",
        "none": "No reviews say it is fake",
    },
    "not_as_described": {
        "label": "Not as advertised",
        "helper": "Size, capacity, features or looks differ from the listing",
        "verb": ("says", "say"),
        "claim": "it differs from the listing",
        "none": "No reviews say it differs from the listing",
    },
}
# Counted and quoted for the shopper, but no verdict rule reads them.
INFORMS_ONLY = ("quality", "not_as_described")
# Sent with every report so the screens never word a label themselves.
BADGE_LABELS = [
    {
        "category": category,
        "label": text["label"],
        "helper": text["helper"],
        "informs_only": category in INFORMS_ONLY,
    }
    for category, text in BADGE_COPY.items()
]


def is_badge_summary(summary: Any) -> bool:
    return isinstance(summary, dict) and str(summary.get("schema_version") or "").startswith(
        BADGE_SCHEMA_PREFIX
    )


def _reviews(count: int) -> str:
    return f"{count} review{'' if count == 1 else 's'}"


def _badge_copy(category: str, words: dict[str, Any] | None) -> dict[str, Any]:
    """The label's fixed words, with the helper, claim and "none" lines of the product's group."""
    return {**BADGE_COPY[category], **((words or {}).get("badges") or {}).get(category, {})}


def _labels(words: dict[str, Any] | None) -> list[dict[str, Any]]:
    """BADGE_LABELS, with each helper line worded for the product's group."""
    return [{**item, "helper": _badge_copy(item["category"], words)["helper"]} for item in BADGE_LABELS]


def _report_phrase(category: str, mentions: int, claim: str) -> str:
    """The verb phrase after a count: "mentions fire", "say it broke"."""
    singular, plural = BADGE_COPY[category]["verb"]
    return f"{singular if mentions == 1 else plural} {claim}"


def _usable_reviews(summary: dict[str, Any]) -> int:
    coverage = summary.get("coverage") or {}
    return int(summary.get("usable_review_count") or coverage.get("usable_reviews") or 0)


def _evidence_items(evidence: Any) -> tuple[list[dict[str, Any]], int]:
    """Return the strongest distinct quotes for a badge, and how many were cut.

    Each quote carries the character ranges of the words that triggered it, so
    the screen can highlight them without re-matching the text.
    """
    if not isinstance(evidence, list):
        return [], 0
    ranked = sorted(
        (item for item in evidence if isinstance(item, dict) and str(item.get("text") or "").strip()),
        key=lambda item: (bool(item.get("high_confidence")), float(item.get("score") or 0)),
        reverse=True,
    )
    seen: set[str] = set()
    distinct: list[dict[str, Any]] = []
    for item in ranked:
        text = str(item["text"]).strip()
        key = " ".join(text.casefold().split())
        if key in seen:
            continue
        seen.add(key)
        highlights = sorted(
            [int(term["span"][0]), int(term["span"][1])]
            for term in item.get("terms") or []
            if isinstance(term, dict)
            and not term.get("negated")
            and isinstance(term.get("span"), list)
            and len(term["span"]) == 2
        )
        distinct.append(
            {
                "text": text,
                "rating": item.get("rating"),
                "hazard": HAZARD_LABELS.get(str(item.get("hazard_subtype") or "")),
                "highlights": highlights,
            }
        )
    shown = distinct[:EVIDENCE_SHOWN_PER_BADGE]
    return shown, len(distinct) - len(shown)


def _hazard_phrase(safety: dict[str, Any]) -> str:
    """Name the most serious hazard reported, noting when there are others.

    Each quote also carries its own hazard label, so naming one type here loses
    nothing, and joining two "X or Y" labels reads as "X or Y and A or B".
    """
    subtypes = safety.get("hazard_subtypes") or {}
    ranked = sorted(
        (
            (int(detail.get("severity") or 0), int(detail.get("reviews") or 0), name)
            for name, detail in subtypes.items()
            if isinstance(detail, dict) and name in HAZARD_LABELS
        ),
        reverse=True,
    )
    if not ranked:
        return HAZARD_LABELS["safety_unspecified"]
    phrase = HAZARD_LABELS[ranked[0][2]]
    return f"{phrase}, and other hazards" if len(ranked) > 1 else phrase


def _safety_badge(safety: dict[str, Any], usable: int, words: dict[str, Any] | None = None) -> dict[str, Any]:
    mentions = int(safety.get("flagged_reviews") or 0)
    evidence, more = _evidence_items(safety.get("evidence"))
    copy_text = _badge_copy("safety", words)
    return {
        "category": "safety",
        "label": copy_text["label"],
        "helper": copy_text["helper"],
        "informs_only": False,
        "mentions": mentions,
        "reviews_analyzed": usable,
        "phrase": _report_phrase("safety", mentions, _hazard_phrase(safety)),
        "summary": (
            f"{_reviews(mentions)} {_report_phrase('safety', mentions, _hazard_phrase(safety))}"
            if mentions
            else copy_text["none"]
        ),
        "evidence": evidence,
        "more_evidence": more,
    }


def _flag_badge(category: str, flag: Any, usable: int, words: dict[str, Any] | None = None) -> dict[str, Any]:
    flag = flag if isinstance(flag, dict) else {}
    mentions = int(flag.get("flagged_reviews") or 0)
    evidence, more = _evidence_items(flag.get("evidence"))
    copy_text = _badge_copy(category, words)
    phrase = _report_phrase(category, mentions, copy_text["claim"])
    return {
        "category": category,
        "label": copy_text["label"],
        "helper": copy_text["helper"],
        "informs_only": category in INFORMS_ONLY,
        "mentions": mentions,
        "reviews_analyzed": usable,
        "phrase": phrase,
        "summary": f"{_reviews(mentions)} {phrase}" if mentions else copy_text["none"],
        "evidence": evidence,
        "more_evidence": more,
    }


def _verdict_detail(state: str, verdict: dict[str, Any], badges: list[dict[str, Any]], usable: int) -> str:
    """Explain the verdict in terms of what the reviews say."""
    reported = [badge for badge in badges if badge["mentions"]]
    if reported and state in {
        "safety_warning",
        "possible_safety_issue",
        "possible_counterfeit_or_defect",
    }:
        # One line, for the most serious thing found; every kind of problem has its own card below the result.
        deciding = [badge for badge in reported if badge["category"] in {"safety", "defect", "counterfeit"}]
        lead = (deciding or reported)[0]
        return f"{lead['mentions']} of {_reviews(usable)} {lead['phrase']}."
    detail = str(verdict.get("detail") or "").strip().rstrip(".")
    if state == "insufficient_evidence" and reported:
        # Too few reviews for an overall judgement must not hide what the few
        # reviews say: a single fire report is still worth reading.
        clauses = "; ".join(
            [reported[0]["summary"]]
            + [f"{badge['mentions']} {badge['phrase']}" for badge in reported[1:]]
        )
        pronoun = "it" if sum(badge["mentions"] for badge in reported) == 1 else "them"
        return f"{detail}. Even so, {clauses}. Read {pronoun} below."
    if state == "no_warning_signs" and reported:
        # The aggregator's own detail says "absence of complaints", which is
        # false when an isolated complaint sits just below the warning level.
        clauses = "; ".join(
            [reported[0]["summary"]]
            + [f"{badge['mentions']} {badge['phrase']}" for badge in reported[1:]]
        )
        pronoun = "it" if sum(badge["mentions"] for badge in reported) == 1 else "them"
        return (
            f"No problem reaches a warning level in {_reviews(usable)}, but {clauses}. "
            f"Read {pronoun} below. This is not proof that a product is safe."
        )
    return f"{detail}." if detail else ""


# The buying conclusion (panel recommendation, Nov 2026): "based on the reviews of this product ...".
# It is worked out from the saved summary when the product is served, so it needs no new analysis and
# changes no stored result. The cut-offs are the team's to confirm; they are not validated against
# shoppers' outcomes, which is why the wording says what reviewers report and never promises anything.
CONCLUSION_RECOMMEND_SHARE = 0.75  # at least this share of reviewers positive ...
CONCLUSION_RECOMMEND_BOUND = 0.65  # ... and the lower bound of that share (small samples) at least this
CONCLUSION_MIXED_SHARE = 0.5  # below this share of positive reviews the decision is not_recommended (a threshold on POSITIVE reviews only; the wording uses the real shares)
CONCLUSION_NOTICE = "This is a guide from public reviews, not proof or a guarantee."
# An operator's off-switch for the product-specific reasons (read once at start): DEFAKETIVE_CONCLUSION_REASONS=0 puts every
# product page back on the plain conclusion without a redeploy. The decision and the verdict are the same either way.
REASONS_ENABLED = os.environ.get("DEFAKETIVE_CONCLUSION_REASONS", "1").strip().lower() not in ("0", "off", "false", "no")


def _sentiment_shares(summary: dict[str, Any]) -> dict[str, float] | None:
    """Positive, uncertain and negative shares of the reviews, weighted when the sample was."""
    shares = summary.get("sentiment_shares")
    if isinstance(shares, dict) and shares:
        values = {name: float(shares.get(name) or 0.0) for name in ("positive", "uncertain", "negative")}
    else:
        counts = summary.get("sentiment_counts") or {}
        values = {
            "positive": float(counts.get("positive") or 0),
            "uncertain": float(counts.get("uncertain") or 0) + float(counts.get("neutral") or 0),
            "negative": float(counts.get("negative") or 0),
        }
    total = sum(values.values())
    return {name: value / total for name, value in values.items()} if total > 0 else None


# The words of the conclusion card: a lead sentence, a short paragraph that names how many reviews raised each
# kind of problem, and the label shown beside it. Counts only; nothing here promises that a product is safe.
CONCLUSION_ASSESSMENT = category_copy.ASSESSMENT
# Order of the problems named in the paragraph (safety last, since it is the one to read closely). Each kind of product
# words them its own way (category_copy).
CONCLUSION_ISSUES = ("defect", "quality", "not_as_described", "counterfeit")


def _review_count(count: int) -> str:
    return f"{count} review" if count == 1 else f"{count} reviews"


def _issue_phrases(mentions: dict[str, int], words: dict[str, Any] | None = None) -> list[str]:
    names = (words or category_copy.profile(None))["issues"]
    phrases = [f"{names[key]} ({_review_count(mentions[key])})" for key in CONCLUSION_ISSUES if mentions.get(key)]
    safety = mentions.get("safety", 0)
    if safety:
        phrases.append(
            "one review mentioning a potential safety concern"
            if safety == 1
            else f"{safety} reviews mentioning a potential safety concern"
        )
    return phrases


def _join_phrases(phrases: list[str]) -> str:
    if len(phrases) <= 2:
        return " and ".join(phrases)
    return ", ".join(phrases[:-1]) + ", and " + phrases[-1]


def _conclusion_words(
    decision: str,
    usable: int,
    shares: dict[str, float] | None,
    mentions: dict[str, int],
    closing: str | None,
    words: dict[str, Any] | None = None,
) -> dict[str, str]:
    """The lead sentence, paragraph and side note of the conclusion card when no review text is available to explain it.

    The mood is described from the real positive, neutral and negative shares (conclusion_text.mood_sentence), never
    inferred from one of them: a product that is 25% positive, 65% neutral and 10% negative is not "mostly negative".
    """
    issues = _issue_phrases(mentions, words)
    positive = shares["positive"] if shares else None
    negative = shares["negative"] if shares else None
    happy = positive is not None and positive >= CONCLUSION_RECOMMEND_SHARE
    serious = any(mentions.get(name) for name in ("safety", "counterfeit", "defect"))
    if decision == "not_enough":
        lead = "There are not enough reviews to say whether this product is worth buying."
        note = category_copy.ASSESSMENT_NOTE["not_enough"]
    elif decision == "recommended":
        lead = "Reviews of this product are generally favorable."
        note = category_copy.ASSESSMENT_NOTE["recommended"]
    elif decision == "mixed":
        lead = "Opinions on this product are mixed."
        note = category_copy.ASSESSMENT_NOTE["mixed"]
    elif decision == "not_recommended":
        lead = "Reviews advise against buying this product."
        note = (
            category_copy.ASSESSMENT_NOTE["not_recommended"]
            if negative is not None and negative > 0.5
            else "Serious problems were reported." if serious else "Few reviews were positive."
        )
    else:
        lead = "Reviews are generally favorable, but some concerns were reported." if happy else "Think twice before buying this product."
        note = category_copy.ASSESSMENT_NOTE["caution_happy" if happy else "caution_unhappy"]
    if decision == "not_enough":
        paragraph = f"Only {_review_count(usable)} could be analyzed, which is too few to say whether this product is worth buying."
    else:
        paragraph = conclusion_text.mood_sentence(shares, usable)
    if issues:
        paragraph += (" However, some" if happy else " Some") + f" reviewers reported issues such as {_join_phrases(issues)}."
    default_closing = {
        "recommended": "Individual results may vary.",
        "mixed": "Experiences differ, so read the reported issues before deciding.",
        "caution": "Read the reported issues before purchasing.",
        "not_recommended": "Read the reported issues before deciding.",
        "not_enough": "",
    }[decision]
    closing = default_closing if closing is None else closing
    if closing:
        paragraph += " " + closing
    return {"lead": lead, "summary": paragraph, "assessment": CONCLUSION_ASSESSMENT[decision], "assessment_note": note}


def _conclusion(
    summary: dict[str, Any], state: str, badges: list[dict[str, Any]], usable: int, words: dict[str, Any] | None = None
) -> dict[str, Any] | None:
    """What the reviews add up to, in one decision and a plain sentence beginning "Based on the reviews"."""
    shares = _sentiment_shares(summary)
    mentions = {badge["category"]: int(badge.get("mentions") or 0) for badge in badges}
    reviews = _reviews(usable)
    words = words or category_copy.profile(None)

    def build(decision: str, headline: str, text: str, points: list[str], closing: str | None = None) -> dict[str, Any]:
        return {
            "decision": decision,
            "headline": headline,
            "text": text,
            **_conclusion_words(decision, usable, shares, mentions, closing, words),
            "points": points,
            "basis": {
                "reviews": usable,
                **({name: round(value * 100) for name, value in shares.items()} if shares else {}),
            },
            "notice": CONCLUSION_NOTICE,
        }

    positive = shares["positive"] if shares else None
    negative = shares["negative"] if shares else None
    mood = (
        f"{round(positive * 100)}% of reviewers were positive and {round(negative * 100)}% negative"
        if shares
        else None
    )
    # "most reviewers were not happy" is said only when the negative share is a majority; a low positive share can
    # just as well mean that most reviews were neutral.
    unhappy = "most reviewers were negative" if negative is not None and negative > 0.5 else "few reviewers were positive"
    points = [f"{reviews} analyzed"] + ([mood] if mood else [])
    if state == "insufficient_evidence":
        return build(
            "not_enough",
            "Not enough reviews to advise",
            f"Based on the reviews of this product, there are too few to say whether it is worth buying ({reviews} usable).",
            points,
        )
    if state == "safety_warning":
        return build(
            "not_recommended",
            "Not recommended",
            "Based on the reviews of this product, we advise against buying it: reviewers report safety problems "
            f"such as {words['hazards']}.",
            points + [f"{mentions.get('safety', 0)} review{'s' if mentions.get('safety', 0) != 1 else ''} mention a safety problem"],
        )
    if state == "possible_safety_issue":
        found = points + [f"{mentions.get('safety', 0)} review{'s' if mentions.get('safety', 0) != 1 else ''} mention a safety problem"]
        if positive is not None and positive < CONCLUSION_MIXED_SHARE:
            return build(
                "not_recommended",
                "Not recommended",
                f"Based on the reviews of this product, we advise against buying it: {unhappy} and "
                "some report possible safety problems.",
                found,
            )
        return build(
            "caution",
            "Think twice before buying",
            "Based on the reviews of this product, think carefully before buying it: some reviewers report possible "
            "safety problems. Read them first.",
            points + [f"{mentions.get('safety', 0)} review{'s' if mentions.get('safety', 0) != 1 else ''} mention a safety problem"],
        )
    if state == "possible_counterfeit_or_defect":
        problems = [
            f"{mentions[name]} report{'s' if mentions[name] != 1 else ''} of {label}"
            for name, label in (("counterfeit", "a fake or not-original item"), ("defect", "a defect"))
            if mentions.get(name)
        ]
        if positive is not None and positive < CONCLUSION_MIXED_SHARE:
            return build(
                "not_recommended",
                "Not recommended",
                f"Based on the reviews of this product, we advise against buying it: {unhappy} and "
                "many report a fake item or a defect.",
                points + problems,
            )
        return build(
            "caution",
            "Think twice before buying",
            "Based on the reviews of this product, think carefully before buying it: many reviewers report a fake item "
            "or a defect, even though some are happy with it.",
            points + problems,
        )
    if state == "reviews_may_be_unreliable":
        return build(
            "caution",
            "Reviews may not be a fair guide",
            "Based on the reviews of this product, we cannot give clear advice: many of the reviews look copied or "
            "generic, so they may not reflect real buyers.",
            points,
            closing="Many of the reviews look copied or generic, so treat this summary with care.",
        )
    if state != "no_warning_signs" or positive is None:
        return None
    lower_bound = float(summary.get("positive_ratio_lower_bound") or 0.0)
    if positive >= CONCLUSION_RECOMMEND_SHARE and lower_bound >= CONCLUSION_RECOMMEND_BOUND:
        return build(
            "recommended",
            "Looks okay to buy",
            f"Based on the reviews of this product, it looks okay to buy: {mood}, and no {words['watch']} "
            "stood out.",
            points + ["No warning signs found"],
        )
    if positive >= CONCLUSION_MIXED_SHARE:
        return build(
            "mixed",
            "Mixed reviews",
            f"Based on the reviews of this product, opinions are mixed: {mood}. Nothing alarming stood out, but read "
            "the complaints before you decide.",
            points + ["No warning signs found"],
        )
    return build(
        "not_recommended",
        "Not recommended",
        f"Based on the reviews of this product, we advise against buying it: {mood}.",
        points,
    )


def product_group(product: dict[str, Any]) -> str | None:
    """The group of products this one belongs to (electronics, fashion, food_grocery ...), read from its title.

    A report saved after rules pc3 carries it; an older one is read again from its name, which needs no new analysis.
    """
    group = product.get("product_group")
    if group:
        return str(group)
    try:
        _ensure_sentiment_path()
        from defaketive_sentiment.product_category import classify_listing, group_of

        return group_of(classify_listing({"name": str(product.get("name") or "")}))
    except Exception:  # the wording falls back to the general profile; a report is never lost over it
        return None


def product_category_of(product: dict[str, Any]) -> str | None:
    """The product's category (haircare, phone, audio ...): the saved one, or read again from its title."""
    saved = product.get("product_category")
    if saved:
        return str(saved)
    try:
        _ensure_sentiment_path()
        from defaketive_sentiment.product_category import classify_listing

        return classify_listing({"name": str(product.get("name") or "")})
    except Exception:
        return None


def _ground_conclusion(
    conclusion: dict[str, Any] | None,
    product: dict[str, Any],
    summary: dict[str, Any],
    state: str,
    badges: list[dict[str, Any]],
    usable: int,
    words: dict[str, Any],
) -> dict[str, Any] | None:
    """Explain the decision with what reviewers actually wrote about the product (aspects.py, conclusion_text.py).

    Only the words change: the decision, headline, points, basis and notice stay as _conclusion made them. A product
    saved without its review text keeps the plain wording, and any failure here also does (a report is never lost over
    its explanation).
    """
    comments = product.get("comments")
    if not conclusion or not isinstance(comments, list) or not comments:
        return conclusion
    try:
        category, group = product_category_of(product), product_group(product)
        result = aspect_evidence.cached_extract(str(product.get("link") or ""), comments, category, group)
        mentions = {badge["category"]: int(badge.get("mentions") or 0) for badge in badges}
        from aspect_profiles import noun_for

        composed = conclusion_text.compose(
            decision=conclusion["decision"],
            state=state,
            usable=usable,
            shares=_sentiment_shares(summary),
            mentions=mentions,
            result=result,
            noun=noun_for(category, group),
            hazards=words["hazards"],
            recommend_share=CONCLUSION_RECOMMEND_SHARE,
        )
        if composed is None:
            return conclusion
        grounded = {
            **conclusion,
            "lead": composed["lead"],
            "summary": composed["summary"],
            "body": composed["body"],  # the paragraph without the hazard sentences ...
            "warnings": composed["warnings"],  # ... which come on their own, so the card can set them apart
            "evidence_status": composed["evidence_status"],
        }
        if composed.get("assessment_note"):
            grounded["assessment_note"] = composed["assessment_note"]
        grounded["evidence"] = {
            "status": composed["evidence_status"],
            "reviews_considered": result["reviews_considered"],
            "product_reviews": result["product_reviews"],
            "service_reviews": result["service_reviews"],
            "not_used_yet_reviews": result["not_used_yet_reviews"],
            "skipped_clauses": result["skipped_clauses"],
            "rules_version": result["version"],
            "category": category,
            "why": conclusion_text.why_items(result, usable),
        }
        return grounded
    except Exception:
        return conclusion


def badge_view(product: dict[str, Any], aspects: bool = False) -> dict[str, Any]:
    """Turn a product's badge summary into what the screen shows.

    `aspects=True` also reads the product's review text for what reviewers praise and criticise (product page only:
    list views never pay for it).
    """
    summary = product.get("sentiment_summary") or {}
    if not is_badge_summary(summary):
        return {
            "available": False,
            "state": "not_analyzed",
            "tone": "unknown",
            "headline": "Not analyzed yet",
            "detail": "This product has not been checked with the current review model.",
            "reviews_analyzed": 0,
            "counts": {"safety": 0, "counterfeit": 0, "defect": 0},
            "badges": [],
            "labels": BADGE_LABELS,
            "conclusion": None,
        }

    usable = _usable_reviews(summary)
    verdict = summary.get("verdict") or {}
    state = str(verdict.get("state") or "insufficient_evidence")
    words = category_copy.profile(product_group(product))
    flags = summary.get("flags") or {}
    # "reports" is present only when the checker ran the five-label rules. A
    # label that was not checked gets no badge, so it never reads "0 reviews".
    reports = summary.get("reports")
    found = {
        "counterfeit": flags.get("counterfeit"),
        "defect": flags.get("defect"),
        **(reports if isinstance(reports, dict) else {}),
    }
    badges = [
        _safety_badge(summary.get("safety") or {}, usable, words)
        if category == "safety"
        else _flag_badge(category, found[category], usable, words)
        for category in BADGE_COPY
        if category == "safety" or category in found
    ]
    return {
        "available": True,
        "state": state,
        "tone": VERDICT_TONES.get(state, "unknown"),
        "headline": words["fake_defect"] if state == "possible_counterfeit_or_defect" else VERDICT_HEADLINES.get(state, "Not enough reviews to judge"),
        "detail": _verdict_detail(state, verdict, badges, usable),
        "reviews_analyzed": usable,
        "counts": {badge["category"]: badge["mentions"] for badge in badges},
        "badges": badges,
        "labels": _labels(words),
        "limits_notice": summary.get("limits_notice"),
        "safety_check_accuracy": SAFETY_CHECK_ACCURACY,
        "conclusion": _ground_conclusion(_conclusion(summary, state, badges, usable, words), product, summary, state, badges, usable, words)
        if aspects and REASONS_ENABLED
        else _conclusion(summary, state, badges, usable, words),
    }


def with_badge_view(product: dict[str, Any], aspects: bool = False) -> dict[str, Any]:
    """Return a shallow copy of a product carrying its display view."""
    return {**product, "badge_view": badge_view(product, aspects)}


def review_rows(products: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows = []
    for product in products:
        for review in product.get("comments") or []:
            if not isinstance(review, dict):
                continue
            if review.get("included_in_analysis") is False:
                continue
            analysis = review.get("sentiment_analysis") or {}
            risk = analysis.get("risk") or {}
            scores = analysis.get("scores") or {}
            rows.append(
                {
                    "Product": product.get("name", ""),
                    "Author": review.get("author", ""),
                    "Stars": int(review.get("rating") or 0),
                    "Date": review.get("time", ""),
                    "Review": review.get("content", ""),
                    "Likes": int(review.get("like_count") or 0),
                    "Sentiment": analysis.get("label", "unanalyzed"),
                    "Compound": scores.get("compound"),
                    "Risk": bool(risk.get("detected", False)),
                    "Risk categories": ", ".join(risk.get("categories") or []),
                    "Duplicate": bool(review.get("is_duplicate", False)),
                    "Product link": product.get("link", ""),
                }
            )
    return rows


def _ensure_sentiment_path() -> None:
    sentiment_root = ROOT / "sentiment-analysis"
    if str(sentiment_root) not in sys.path:
        sys.path.insert(0, str(sentiment_root))


def sentiment_model_version() -> str:
    """Return the version of the model the application actually runs.

    Delegates to the registry so this can never name a different model from the
    one `analyze_products` loads. When they disagree, `analysis_is_current`
    either re-analyzes on every request or fails to re-analyze when the model
    really has changed.
    """
    _ensure_sentiment_path()
    from defaketive_sentiment.registry import ModelUnavailableError, model_version

    try:
        return model_version()
    except ModelUnavailableError:
        # Only used to decide whether stored analyses are stale. An unloadable
        # model means nothing can be current, and analyze_products will raise
        # with the real reason when it is called.
        return "unavailable"


def model_unavailable_error() -> type[Exception]:
    """The exception raised when the configured model cannot be loaded."""
    _ensure_sentiment_path()
    from defaketive_sentiment.registry import ModelUnavailableError

    return ModelUnavailableError


def require_model() -> None:
    """Raise ModelUnavailableError now if the model cannot load.

    Called before a live scan, so a missing model is reported before minutes of
    marketplace collection rather than after them.
    """
    _ensure_sentiment_path()
    from defaketive_sentiment.registry import load_model

    load_model()


def _pc4_report_compatible(product: dict[str, Any], expected_version: str) -> bool:
    """Accept an earlier pc4 report ONLY when pc6 chooses the same category.

    The shipped sentiment/learned hazard assets, lexicons and thresholds are
    identical in this candidate. The only authoritative difference is the
    product-title classifier. If it returns the same known category, it takes
    exactly the same category-specific hazard path. Old reports with a missing,
    unknown or newly changed category remain stale until an explicit recheck.

    Never strip version tags or mark other model-version upgrades as current.
    """
    if "+pc6+" not in expected_version:
        return False
    previous = expected_version.replace("+pc6+", "+pc4+", 1)
    if previous == expected_version:
        return False
    category = product.get("product_category")
    if not isinstance(category, str) or not category:
        return False
    try:
        _ensure_sentiment_path()
        from defaketive_sentiment.product_category import classify_listing, group_of

        name = str(product.get("name") or "")
        if not name or classify_listing({"name": name}) != category:
            return False
        stored_group = product.get("product_group")
        if stored_group and str(stored_group) != group_of(category):
            return False
    except (ImportError, AttributeError, TypeError, ValueError):
        return False
    for review in product.get("comments") or []:
        if not isinstance(review, dict) or review.get("included_in_analysis") is False:
            continue
        if (review.get("sentiment_analysis") or {}).get("model_version") != previous:
            return False
    return True


def _category_revision_report_compatible(product: dict[str, Any], expected_version: str) -> bool:
    """Reuse older reports only when their title still takes the same hazard path."""
    revisions = {"pc8": ("pc7", "pc6", "pc4"), "pc7": ("pc6", "pc4")}
    current = next((revision for revision in revisions if f"+{revision}+" in expected_version), None)
    if current is None:
        return False
    category = product.get("product_category")
    if not isinstance(category, str) or not category:
        return False
    name = str(product.get("name") or "")
    if not name:
        return False
    try:
        _ensure_sentiment_path()
        from defaketive_sentiment.product_category import classify_listing, group_of

        if classify_listing({"name": name}) != category:
            return False
        stored_group = product.get("product_group")
        if stored_group and str(stored_group) != group_of(category):
            return False
    except (ImportError, AttributeError, TypeError, ValueError):
        return False

    versions = [
        (review.get("sentiment_analysis") or {}).get("model_version")
        for review in product.get("comments") or []
        if isinstance(review, dict) and review.get("included_in_analysis") is not False
    ]
    if not versions:
        return False
    for earlier in revisions[current]:
        previous = expected_version.replace(f"+{current}+", f"+{earlier}+", 1)
        if previous != expected_version and all(value == previous for value in versions):
            return True
    return False


def analysis_is_current(products: list[dict[str, Any]]) -> bool:
    """Check exact-model matches or narrowly validated category revision equivalence.

    All previously generated outputs remain byte-identical. An unchanged title
    category can safely follow the same hazard path. Changed categories
    remain stale until explicitly rechecked.
    """
    if not products:
        return False
    expected_version = sentiment_model_version()
    for product in products:
        if not isinstance(product, dict):
            return False
        summary = product.get("sentiment_summary") or {}
        if not (is_badge_summary(summary) or summary.get("risk_score_scale")):
            return False
        versions = [
            (review.get("sentiment_analysis") or {}).get("model_version")
            for review in product.get("comments") or []
            if isinstance(review, dict) and review.get("included_in_analysis") is not False
        ]
        if all(value == expected_version for value in versions):
            continue
        if not (
            _pc4_report_compatible(product, expected_version)
            or _category_revision_report_compatible(product, expected_version)
        ):
            return False
    return True


def analyze_products(products: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Analyze products with the configured model.

    Raises ModelUnavailableError if that model cannot be loaded. It deliberately
    does not fall back to a different model: with badges, a substitution would
    change the shape of the output, and the report would render another model's
    verdict with nothing to show that it had happened.
    """
    _ensure_sentiment_path()
    from defaketive_sentiment.analyze_reviews import analyze_product_json
    from defaketive_sentiment.registry import load_model

    analyzed = copy.deepcopy(products)
    return analyze_product_json(analyzed, load_model())


def json_bytes(products: list[dict[str, Any]]) -> bytes:
    return json.dumps(products, ensure_ascii=False, indent=2).encode("utf-8")


def csv_bytes(rows: list[dict[str, Any]]) -> bytes:
    if not rows:
        return b""
    buffer = io.StringIO(newline="")
    writer = csv.DictWriter(buffer, fieldnames=list(rows[0]), extrasaction="ignore")
    writer.writeheader()
    writer.writerows(rows)
    return buffer.getvalue().encode("utf-8-sig")
