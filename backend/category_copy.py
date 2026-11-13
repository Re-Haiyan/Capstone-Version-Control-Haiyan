"""The words of a report, by kind of product (rules pc3).

The same five labels mean different things on different products: a "safety problem" is a battery fire on a power
bank, a rash on a face cream, spoiled food on a snack and a sharp edge on a toy. Every line a shopper reads under a
label (what it covers, what "none found" says, what the paragraph names) comes from the profile of the product's
group, so a report on a lipstick never talks about chargers.

The profile of a group only needs the lines that differ from DEFAULT, which is written for any product and names no
device. The words say what reviewers REPORT; none of them says a product is safe.
"""

from __future__ import annotations

from typing import Any

# One name for each decision, used on the card and in the filters. They describe the reviews, not the product.
ASSESSMENT = {
    "recommended": "Well reviewed",
    "mixed": "Mixed reviews",
    "caution": "Some concerns",
    "not_recommended": "Not recommended",
    "not_enough": "Too few reviews",
}
ASSESSMENT_NOTE = {
    "recommended": "Mostly positive, no red flags found.",
    "mixed": "Mixed opinions.",
    "not_recommended": "Most reviewers were unhappy or reported serious problems.",
    "not_enough": "Too few reviews to judge.",
    "caution_happy": "Mostly positive, with reported concerns.",
    "caution_unhappy": "Reported concerns.",
}
NO_RED_FLAGS = "No red flags found"

DEFAULT: dict[str, Any] = {
    # After "reviewers report safety problems such as ..."
    "hazards": "fire, burns, injury or a harmful reaction",
    # In "no ... problem stood out"
    "watch": "safety, fake or defect problem",
    "fake_defect": "Reviewers report fakes or defects",
    "badges": {
        "safety": {
            "helper": "Fire, burns, injury or a harmful reaction",
            "none": "No reviews mention fire, burns, injury or a harmful reaction",
        },
        "defect": {
            "helper": "Doesn't work, stops working or arrives broken",
            "claim": "it is faulty or stopped working",
            "none": "No reviews say it is faulty or broken",
        },
        "quality": {
            "helper": "Works, but weak, flimsy or poorly made",
            "claim": "it works but is weak, flimsy or poorly made",
            "none": "No reviews call it weak, flimsy or poorly made",
        },
        "counterfeit": {
            "helper": "Reviewers say it is a copy, not the original brand",
            "claim": "it may not be genuine",
            "none": "No reviews say it is fake",
        },
        "not_as_described": {
            "helper": "Size, features, color or looks differ from the listing",
            "claim": "it differs from the listing",
            "none": "No reviews say it differs from the listing",
        },
    },
    # In "some reviewers reported issues such as ..."
    "issues": {
        "defect": "product defects",
        "quality": "weak or poor build quality",
        "not_as_described": "differences from the product description",
        "counterfeit": "possible authenticity concerns",
    },
}

# Only what differs from DEFAULT.
PROFILES: dict[str, dict[str, Any]] = {
    "electronics": {
        "hazards": "fire, smoke, burning smells or overheating",
        "badges": {
            "safety": {
                "helper": "Overheating, smoke, sparks or shocks",
                "none": "No reviews mention fire, smoke, shocks or overheating",
            },
            "defect": {"helper": "Doesn't work, stops working, drains fast or charges slowly"},
            "quality": {
                "helper": "Works, but weak, flimsy or scratched",
                "claim": "it works but is weak, flimsy or marked",
                "none": "No reviews call it weak, flimsy or scratched",
            },
            "not_as_described": {"helper": "Size, capacity, features or looks differ from the listing"},
        },
    },
    "home_living": {
        "hazards": "electric shocks, burns, overheating, sharp edges or collapse",
        "badges": {
            "safety": {
                "helper": "Shocks, overheating, sharp edges, gas leaks or collapse",
                "none": "No reviews mention shocks, overheating, sharp edges or collapse",
            },
            "defect": {"helper": "Doesn't work, stops working, leaks or arrives broken"},
            "quality": {
                "helper": "Works, but flimsy, wobbly or poorly finished",
                "claim": "it works but is flimsy, wobbly or poorly finished",
                "none": "No reviews call it flimsy, wobbly or poorly finished",
            },
            "not_as_described": {"helper": "Size, material, color or features differ from the listing"},
        },
        "issues": {"quality": "flimsy or poorly finished build"},
    },
    "fashion": {
        "hazards": "skin rashes, burns or allergic reactions",
        "fake_defect": "Reviewers report fakes or damaged items",
        "badges": {
            "safety": {
                "helper": "Skin rash, itching or an allergic reaction",
                "none": "No reviews mention a rash, itching or an allergic reaction",
            },
            "defect": {
                "helper": "Torn, loose stitching, broken zipper or a sole that comes apart",
                "claim": "it is torn, badly stitched or came apart",
                "none": "No reviews say it is torn or came apart",
            },
            "quality": {
                "helper": "Thin or rough fabric, fading, shrinking or a poor finish",
                "claim": "its fabric or finish is poor",
                "none": "No reviews call the fabric or finish poor",
            },
            "not_as_described": {"helper": "Size, fit, color or material differs from the listing"},
        },
        "issues": {
            "defect": "tears or loose stitching",
            "quality": "poor fabric or finish",
            "not_as_described": "differences in size, fit or color",
        },
    },
    "beauty_health": {
        "hazards": "skin reactions, burns, rashes or other harm",
        "fake_defect": "Reviewers report fakes or damaged items",
        "badges": {
            "safety": {
                "helper": "Rash, burning, an allergic reaction or other harm",
                "none": "No reviews mention a rash, burning or an allergic reaction",
            },
            "defect": {
                "helper": "Leaks, broken pump or cap, spoiled or doesn't work",
                "claim": "it is damaged, spoiled or doesn't work",
                "none": "No reviews say it is damaged or spoiled",
            },
            "quality": {
                "helper": "Weak or no effect, poor texture, smell or finish",
                "claim": "it has weak results or a poor texture",
                "none": "No reviews call the results weak or the texture poor",
            },
            "counterfeit": {
                "helper": "Reviewers say it is fake, diluted or not the original",
                "claim": "it may be fake or not original",
            },
            "not_as_described": {"helper": "Shade, size, amount or ingredients differ from the listing"},
        },
        "issues": {
            "defect": "damaged or spoiled items",
            "quality": "weak results or poor texture",
            "not_as_described": "differences in shade, size or amount",
        },
    },
    "food_grocery": {
        "hazards": "spoiled or contaminated food, or sickness after eating",
        "watch": "spoilage, fake or safety problem",
        "fake_defect": "Reviewers report fakes or damaged items",
        "badges": {
            "safety": {
                "helper": "Spoiled, expired, contaminated or made someone sick",
                "none": "No reviews mention spoilage, expiry or sickness",
            },
            "defect": {
                "helper": "Broken seal, leaking, crushed or the wrong item",
                "claim": "it arrived damaged, leaking or unsealed",
                "none": "No reviews say it arrived damaged or unsealed",
            },
            "quality": {
                "helper": "Stale, bland, too sweet or poor taste",
                "claim": "it tastes stale or poor",
                "none": "No reviews call the taste stale or poor",
            },
            "counterfeit": {"helper": "Reviewers say it is fake or not the original brand"},
            "not_as_described": {"helper": "Amount, flavor, size or packaging differs from the listing"},
        },
        "issues": {
            "defect": "damaged or leaking packs",
            "quality": "stale or poor taste",
            "not_as_described": "differences in amount or flavor",
        },
    },
    "baby_kids_toys": {
        "hazards": "choking, sharp edges, harmful materials or breakage",
        "badges": {
            "safety": {
                "helper": "Choking, sharp edges, harmful materials or a rash",
                "none": "No reviews mention choking, sharp edges or harmful materials",
            },
            "defect": {"helper": "Breaks, parts fall off or doesn't work"},
            "quality": {
                "helper": "Flimsy, cheap-feeling or poorly finished",
                "claim": "it feels cheap, flimsy or poorly finished",
                "none": "No reviews call it cheap, flimsy or poorly finished",
            },
            "not_as_described": {"helper": "Size, age fit, features or color differ from the listing"},
        },
        "issues": {"quality": "cheap or flimsy build"},
    },
    "sports_outdoor": {
        "hazards": "injury or gear that gives way",
        "badges": {
            "safety": {
                "helper": "Injury, or gear that gives way",
                "none": "No reviews mention injury or gear that gives way",
            },
            "defect": {"helper": "Breaks, tears or stops working"},
            "quality": {
                "helper": "Flimsy, wears out quickly or poorly stitched",
                "claim": "it is flimsy or wears out quickly",
                "none": "No reviews call it flimsy or quick to wear out",
            },
            "not_as_described": {"helper": "Size, weight, material or features differ from the listing"},
        },
        "issues": {"quality": "flimsy or quick-wearing build"},
    },
    "pets": {
        "hazards": "pets getting sick, hurt or reacting badly",
        "badges": {
            "safety": {
                "helper": "A pet sick, hurt or reacting badly",
                "none": "No reviews mention a pet getting sick or hurt",
            },
            "defect": {"helper": "Breaks, leaks or doesn't work"},
            "quality": {
                "helper": "Flimsy, chewed through or poorly made",
                "claim": "it is flimsy or poorly made",
                "none": "No reviews call it flimsy or poorly made",
            },
            "not_as_described": {"helper": "Size, amount, flavor or features differ from the listing"},
        },
    },
    "automotive_tools": {
        "hazards": "parts that fail or break loose while riding, driving or working",
        "badges": {
            "safety": {
                "helper": "Parts that fail, break loose or injure",
                "none": "No reviews mention parts failing or causing injury",
            },
            "defect": {"helper": "Doesn't fit, doesn't work or breaks"},
            "quality": {
                "helper": "Weak, rusts quickly or poorly finished",
                "claim": "it is weak, rusts or is poorly finished",
                "none": "No reviews call it weak, rusty or poorly finished",
            },
            "not_as_described": {"helper": "Fit, size, model or features differ from the listing"},
        },
        "issues": {"not_as_described": "differences in fit, size or model"},
    },
    "office_media": {
        "badges": {
            "defect": {"helper": "Doesn't work, dried out, torn or arrives broken"},
            "quality": {
                "helper": "Poor print, weak material or a poor finish",
                "claim": "its material or finish is poor",
                "none": "No reviews call the material or finish poor",
            },
            "not_as_described": {"helper": "Size, amount, edition or color differs from the listing"},
        },
    },
    "digital_services": {
        "hazards": "harm to a user or an account",
        "watch": "account, scam or delivery problem",
        "fake_defect": "Reviewers report scams or codes that fail",
        "badges": {
            "safety": {
                "helper": "Harm to a user or an account",
                "none": "No reviews mention harm or a problem with an account",
            },
            "defect": {
                "helper": "A code or load that doesn't work or never arrives",
                "claim": "the code or load failed or never arrived",
                "none": "No reviews say a code or load failed",
            },
            "quality": {
                "helper": "Slow, limited or poor service",
                "claim": "the service is slow or limited",
                "none": "No reviews call the service slow or limited",
            },
            "counterfeit": {"helper": "Reviewers say it is a scam or not genuine", "claim": "it may be a scam"},
            "not_as_described": {"helper": "Amount, duration or plan differs from the listing"},
        },
        "issues": {"defect": "codes or loads that failed", "quality": "slow or limited service"},
    },
}


def _merge(base: dict[str, Any], extra: dict[str, Any]) -> dict[str, Any]:
    merged = dict(base)
    for key, value in extra.items():
        merged[key] = _merge(base[key], value) if isinstance(value, dict) and isinstance(base.get(key), dict) else value
    return merged


_CACHE: dict[str, dict[str, Any]] = {}


def profile(group: str | None) -> dict[str, Any]:
    """The words for a group of products; DEFAULT for an unknown group or a product that is not recognised."""
    key = group if group in PROFILES else "default"
    if key not in _CACHE:
        _CACHE[key] = _merge(DEFAULT, PROFILES.get(key, {}))
    return _CACHE[key]
