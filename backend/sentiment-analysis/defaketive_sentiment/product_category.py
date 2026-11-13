"""Rules pc2: read the product's category from its title, so a word that is a complaint for one kind of product is not one for another.

pc1 had ten categories, mostly electronics. pc2 covers the marketplace: 49 categories in 11 groups (electronics, home
and living, fashion, beauty and health, baby and toys, sports and outdoor, pets, food and grocery, automotive and tools,
office and media, digital services), in the order the rules are checked. A category changes what the checker does only when it has a file
in lexicons/categories/; the rest only label the product, and `group_of` says which group it is in.

WHY THIS EXISTS
"manipis" (thin) is a selling point on a phone or laptop and a complaint on a shirt
or a cable. The quality label read it the same way everywhere. The review panel
asked that each scanned product be placed in a category first, with its own list
of exceptions kept in its own file.

HOW IT WORKS
classify_listing(name) reads the listing's title and returns a category slug
(CATEGORIES). Each category may have a file lexicons/categories/<slug>.tsv with
the matches that are NOT a complaint for that kind of product:

    term     a regular expression; it must match the whole flagged phrase
    label    the label it applies to (quality)
    unless   optional regular expression, matched as whole words; when one of the
             3 words either side of the phrase matches it, the exception does not apply
    reason   why, for the audit trail

A file is named for a category (phone.tsv) or for a whole group (group_fashion.tsv, read for every category of
the group). Exceptions apply to any label (quality, defect, counterfeit, safety, not_as_described): "init" is a
heat hazard on a power bank and the weather on a shirt. A second kind of file, <name>.add.tsv, goes the other way
and lists what reviewers of THAT kind of product report that the general lists do not know: a rash on a face
cream, a spoiled seal on food, a sharp edge on a toy. Its columns are: term | label | severity | reason, where the
term is a regular expression read against the normalized sentence and severity is 1 (minor) to 3. Added safety
terms are read as an unspecified safety concern, which the taxonomy caps at severity 2, so they are counted and
quoted but cannot raise an alert by themselves.

Every doubt falls back to the old behaviour: a title no rule recognizes is "other",
a category with no file has no exceptions, and an `unless` word cancels the
exception ("manipis na plastic" is still a complaint on a phone). So an
exception can only REMOVE a flag the old rules would have raised, and only for a phrase listed in a category
file; an addition can only ADD a flag, and only for a category whose own add file lists the phrase. A product
in "other" or in a category with no file is read exactly as before.

The title is read, not the description: descriptions list compatible devices and
accessories, which would put a phone case in the phone category. Within the title only
the head is read, the words before the first "for", "with", "+", "," or "(": a laptop
sold "with bag and mic" is a laptop, and "case for iPhone" is a case.
"""

from __future__ import annotations

import csv
import re
from functools import lru_cache
from pathlib import Path
from typing import Any

PRODUCT_CATEGORY_REVISION = "pc3"
PRODUCT_CATEGORY_OFF = False
CATEGORY_DIR = Path(__file__).with_name("lexicons") / "categories"

OTHER = "other"
# (category, group, pattern). The first category whose pattern is found in the title wins, so the order is the
# design: "phone case" is an accessory before it is a phone, "power bank for iPhone" a power bank before a phone,
# "Samsung refrigerator" an appliance before a brand-only phone match, and a phone titled with its camera
# spec ("108MP camera") a phone before a camera. A title no rule recognizes is OTHER, which behaves as before.
_RULES: tuple[tuple[str, str, str], ...] = (
    # --- not a physical product at all ---
    ("digital_goods", "digital_services",
     r"\b(?:e-?load|gift cards?|vouchers?|top-?up|game credits?|prepaid|subscriptions?|netflix (?:premium|subscription|account)|spotify premium|e-?books?|"
     r"online course|event tickets?|concert tickets?|load promo|gcash)\b"),
    # --- things that are not the device they name ---
    ("stationery_books", "office_media",
     r"^(?!.*\b(?:stylus|touch ?screen)\b).*?\b(?:pencil cases?|pens?(?! ?drive)|pencils?|markers?|highlighters?|erasers?|staplers?|sticky notes|crayons?|"
     r"sketch ?books?|journals?|planners?|notebooks? (?:paper|journal)|spiral notebooks?|books?|novels?|textbooks?|"
     r"workbooks?|manga|magazines?|bible|art supplies|folders?|scissors)\b"),
    ("home_textile", "home_living",
     r"\b(?:bed ?sheets?|bed ?covers?|bedding|comforters?|duvets?|pillows?|pillow ?cases?|blankets?|curtains?|towels?|"
     r"rugs?|carpets?|mattress(?:es)?|doormats?|table ?cloth|bath ?mats?)\b"),
    ("accessory", "electronics",
     r"\b(?:cases?|casing|covers?|sleeves?|protectors?|tempered|screen film|film|stands?(?! (?:fans?|mixers?))|holders?|"
     r"mounts?|brackets?|tripods?|ring light|lanyards?|cleaner|organizers?|mouse ?pads?|cooling pads?|"
     r"watch (?:bands?|straps?)|(?:phone|laptop|camera|tablet|ipad) (?:bags?|pouch|backpack))\b"),
    # --- electronics ---
    ("powerbank", "electronics", r"\bpower ?banks?\b"),
    ("charger_cable", "electronics",
     r"\b(?:chargers?|charging (?:cables?|cords?|stations?|docks?|pads?)|cables?|cords?|adapters?|adaptors?|usb hub|"
     r"extension cords?|power strips?|surge protectors?)\b"),
    ("health_supplements", "beauty_health",
     r"\b(?:vitamins?|supplements?|collagen|probiotics?|capsules?|\d+ ?mg|gluta(?:thione)?|multivitamins?|fish oil|"
     r"protein powder|herbal)\b"),
    ("audio", "electronics",
     r"\b(?:earbuds?|earphones?|headphones?|headsets?|airpods?|buds|tws|speakers?|soundbar|microphones?|mic|neckband|"
     r"karaoke|amplifier|dj mixer)\b"),
    ("wearable", "electronics", r"\b(?:smart ?watch|smart ?band|fitness (?:band|tracker)|mi band|watch(?:es)?)\b"),
    ("phone", "electronics",
     r"\b(?:smart ?phones?|cell ?phones?|mobile phones?|android phones?|keypad phones?|cp|iphone|galaxy [asmz]\d+|"
     r"pixel \d+|(?:redmi|realme|infinix|tecno|poco|oppo|vivo|xiaomi|huawei|honor|nokia|oneplus|samsung galaxy|galaxy)\s+"
     r"(?:note|narzo|hot|spark|camon|pova|reno|find|nord|play|[a-z]\d{1,3}))\b"),
    ("phone", "electronics",
     r"^(?!.*\b(?:tablets?|ipad|laptops?|notebook|pad|tv|watch|projector|box|router|dash ?cam)\b).*?"
     r"\b(?:\d+ ?gb ?(?:ram|rom)|\d+ ?\+ ?\d+ ?gb|helio|dimensity|snapdragon|exynos|unisoc|mediatek|dual sim|"
     r"5g (?:smart)?phone)\b"),
    ("gaming", "electronics",
     r"\b(?:game ?pads?|controllers?|joysticks?|consoles?|ps[2-5]|playstation|xbox|nintendo|switch lite|steam deck|"
     r"dual ?shock|double ?shock|dual ?sense|gaming chairs?)\b"),
    ("eyewear", "fashion",
     r"\b(?:sunglasses|eye ?glasses|reading glasses|contact lens(?:es)?|eyewear|spectacles|blue ?light glasses|"
     r"anti-?radiation glasses|prescription glasses|eyeglass(?:es)? frames?)\b"),
    ("camera", "electronics",
     r"\b(?:cameras?|dash ?cams?|cctv|gopro|action cam|web ?cams?|camcorders?|drones?|binoculars?|lens(?:es)?)\b"),
    ("tv_display", "electronics",
     r"\b(?:tvs?|televisions?|smart tv|projectors?|(?<!baby )(?<!heart rate )(?<!blood pressure )(?<!bp )monitors?|tv box|android box|tv stick|digital antenna)\b"),
    # --- home appliances (before the brand-only phone rule) ---
    ("small_appliance", "home_living",
     r"\b(?:rice cookers?|air ?fryers?|blenders?|kettles?|toasters?|microwaves?|ovens?|mixers?|juicers?|coffee makers?|"
     r"espresso machines?|(?:electric |stand |ceiling |rechargeable |usb |desk |mini )?(?<!cooling )(?<!cpu )(?<!case )(?<!pc )fans?|air ?con(?:ditioners?)?|"
     r"humidifiers?|dehumidifiers?|air purifiers?|vacuums?|(?:steam |electric |clothes )irons?|garment steamers?|"
     r"washing machines?|refrigerators?|freezers?|heaters?|water dispensers?|induction cookers?|electric stoves?|"
     r"hot ?plates?|pressure cookers?|slow cookers?|food processors?|grills?|sandwich makers?|waffle makers?|"
     r"rice maker|water heaters?|electric (?:pots?|shavers?)|sewing machines?)\b"),
    ("smart_home", "electronics",
     r"\b(?:smart (?:plugs?|bulbs?|locks?|switch(?:es)?|doorbells?|sockets?)|door ?bells?|motion sensors?|alarm systems?|"
     r"wifi (?:plugs?|bulbs?)|tuya|door lock|fingerprint)\b"),
    ("laptop", "electronics",
     r"\b(?:laptops?|macbook|chromebook|ultrabook|thinkpad|ideapad|vivobook|zenbook|notebook pc|desktop pc|"
     r"all-in-one pc)\b"),
    ("tablet", "electronics", r"\b(?:tablets?|ipad|galaxy tab|redmi pad|mi pad)\b"),
    ("computer_peripheral", "electronics",
     r"\b(?:keyboards?|mouse|mice|printers?|scanners?|routers?|modems?|flash ?drives?|pen ?drives?|usb drives?|"
     r"memory cards?|sd cards?|micro ?sd|hard (?:disk|drive)s?|hdd|ssd|webcam|graphics cards?|gpu|motherboards?|"
     r"power supply|psu|pc (?:case|fan)|cooling pads?|capture cards?|docking stations?|kvm|ink|toner|"
     r"stylus|drawing tablets?|card readers?|processors?|cpu|ryzen|intel core|core i[3579]|ddr[345]|so-?dimm|"
     r"wi-?fi (?:extenders?|repeaters?|boosters?|dongles?|adapters?)|mesh wi-?fi|pocket wi-?fi|home wi-?fi|"
     r"wi-?fi router|lte router|access points?|network switch|ethernet)\b"),
    ("battery_solar", "electronics",
     r"\b(?:lifepo4|lithium (?:ion )?batter(?:y|ies)|batter(?:y|ies) (?:packs?|cells?)|(?:car|motorcycle|solar|deep cycle|"
     r"rechargeable|aa|aaa|9v) batter(?:y|ies)|\d+ ?v ?\d+ ?ah|18650|solar (?:inverters?|chargers?|generators?|"
     r"power|batter(?:y|ies)|panel (?:kits?|sets?|systems?))|inverters?|generators?|power stations?|battery chargers?)\b"),
    ("motorcycle", "automotive_tools",
     r"\b(?:mufflers?|exhaust|handlebars?|bar ?ends?|side mirrors?|tail ?lights?|sprockets?|"
     r"drive chain|clutch (?:lever|cable|plate|cover)|brake pads?|scooter parts?|mio (?:sporty|soul|i)|nmax|aerox|click ?125|xrm|power ?pipe|"
     r"e-?bikes?|electric (?:bike|scooter)s?|riding gloves|fairings?|top ?box|crash guards?)\b"),
    # --- the home and the family ---
    ("baby", "baby_kids_toys",
     r"\b(?:baby|babies|infants?|newborns?|toddlers?|diapers?|strollers?|cribs?|pacifiers?|feeding bottles?|nursing|"
     r"breast pumps?|bibs?|teethers?|baby (?:wipes|powder|lotion)|onesies?)\b"),
    ("garden_plants", "home_living",
     r"\b(?:flower pots?|plant pots?|garden(?:ing)?|seeds?|fertili[sz]ers?|potting soil|soil|watering cans?|hoses?|lawn|"
     r"planters?|plants?|seedlings?|grow lights?|pruning|sprinklers?)\b"),
    ("home_decor_lighting", "home_living",
     r"\b(?:lamps?|led (?:strips?|lights?|bulbs?)|bulbs?|chandeliers?|string lights|fairy lights|night lights?|"
     r"ceiling lights?|flood ?lights?|flash ?lights?|headlamps?|torch(?:es)?|decor|wall art|picture frames?|photo frames?|"
     r"vases?|candles?|mirrors?|wall stickers?|wallpapers?|clocks?|figurines?|artificial (?:plants?|flowers?))\b"),
    ("kitchen_dining", "home_living",
     r"\b(?:cookware|frying pans?|pans?|pots?|woks?|kitchen|knives|knife|utensils?|plates?|bowls?|cups?|mugs?|tumblers?|"
     r"water bottles?|bottles?|containers?|lunch ?box(?:es)?|chopping boards?|spatulas?|cutlery|spoons?|forks?|"
     r"chopsticks|glassware|thermos|flasks?|colanders?|strainers?|baking|cake molds?|food storage|dish racks?|"
     r"spice racks?|jugs?|pitchers?)\b"),
    ("furniture", "home_living",
     r"\b(?:sofas?|couch(?:es)?|chairs?|tables?|desks?|shelf|shelves|shelving|cabinets?|wardrobes?|bed frames?|beds?|"
     r"stools?|bookshelf|bookcases?|drawers?|storage racks?|racks?|shoe racks?|dressers?|benches|ottomans?|"
     r"hanging rack|clothes rack|nightstands?)\b"),
    ("household_cleaning", "home_living",
     r"\b(?:detergents?|fabric softeners?|dish ?soap|disinfectants?|mops?|brooms?|dust ?pans?|trash (?:bins?|bags?)|"
     r"garbage|tissues?|toilet (?:paper|brush)|laundry|baskets?|hangers?|sponges?|bleach|air fresheners?|"
     r"insecticides?|cleaning)\b"),
    ("tools_hardware", "automotive_tools",
     r"\b(?:drills?|screwdrivers?|wrenches?|tool ?(?:sets?|box|kits?)|hammers?|pliers?|saws?|tape measures?|ladders?|"
     r"screws?|bolts?|nail guns?|power tools?|soldering|multimeters?|glue guns?|paint (?:brush|roller|sprayer)|"
     r"padlocks?|hinges?|sandpaper|welding)\b"),
    ("automotive", "automotive_tools",
     r"\b(?:car|cars|motorcycles?|motorbikes?|helmets?|tires?|tyres?|engine oil|car (?:seat|wash|wax|polish)|"
     r"dash ?board|windshield|wiper|brake|spark plugs?|motor oil|mags?|rims?|bike (?:lights?|accessories))\b"),
    # --- people ---
    ("toys", "baby_kids_toys",
     r"\b(?:toys?|lego|dolls?|action figures?|puzzles?|board games?|plush|stuffed|rc cars?|remote control cars?|"
     r"building blocks|playsets?|slime|fidget|nerf|toy cars?|diecast|model kits?|blocks|kids? (?:toy|game))\b"),
    ("footwear", "fashion",
     r"\b(?:shoes?|sneakers?|sandals?|slippers?|flip ?flops?|boots?|heels|loafers|crocs|insoles?|slides|clogs|"
     r"stilettos?|wedges|rubber shoes|cleats|oxfords?)\b"),
    ("bags", "fashion",
     r"\b(?:bags?|handbags?|backpacks?|wallets?|luggage|totes?|sling bags?|purses?|clutch|fanny packs?|belt bags?|"
     r"shoulder bags?|duffel|briefcases?|trolley)\b"),
    ("jewelry_accessories", "fashion",
     r"\b(?:necklaces?|bracelets?|rings?|earrings?|pendants?|anklets?|brooch(?:es)?|hair clips?|headbands?|scrunchies?|"
     r"sunglasses|eyeglasses|belts?|caps?|hats?|scarf|scarves|gloves|bandanas?|jewel(?:ry|lery)|chains?|bangles?|"
     r"hair accessories|ties|cufflinks|beanies?|visors?)\b"),
    ("apparel", "fashion",
     r"\b(?:t-?shirts?|shirts?|tees?|dress(?:es)?|pants|shorts|jeans|jackets?|hoodies?|blouses?|skirts?|leggings|"
     r"underwear|socks?|pajamas?|uniforms?|cardigans?|sweaters?|polo|bras?|panty|panties|fabric|tela|coats?|blazers?|"
     r"trousers|joggers?|jumpsuits?|rompers?|tank tops?|crop tops?|sando|swimwear|bikinis?|lingerie|boxers?|briefs|"
     r"sweatshirts?|vests?|gowns?|abayas?|hijabs?|sleepwear|robes?|tops|outfits?|clothes|clothing|costume)\b"),
    # --- beauty, health, personal care ---
    ("medical_devices", "beauty_health",
     r"\b(?:thermometers?|blood pressure|oximeters?|glucometers?|(?:surgical|kn95|n95|disposable|3-?ply|4-?ply|ffp2) (?:face )?masks?|first aid|"
     r"massagers?|massage guns?|nebulizers?|heating pads?|knee (?:braces?|supports?)|wheelchairs?|crutches|hearing aids?|"
     r"bp monitors?|orthopedic|posture corrector|compression (?:socks|stockings))\b"),
    ("makeup", "beauty_health",
     r"\b(?:lipsticks?|lip (?:tint|gloss|balm|stain|liner)|foundation|mascara|eyeliner|blush|eyeshadow|concealer|makeup|"
     r"make-up|cosmetics?|nail (?:polish|art|stickers?)|press-?on nails|false (?:eyelashes|lashes)|fake (?:nails|lashes|eyelashes)|"
     r"eyelashes|eyebrow|highlighter|compact powder|setting spray|makeup brush(?:es)?|primer|bb cream|cc cream|contour)\b"),
    ("skincare", "beauty_health",
     r"\b(?:serum|moisturi[sz]er|sunscreen|sunblock|cleanser|toner|face (?:cream|wash|mask|oil)|facial|lotion|"
     r"body (?:lotion|butter|scrub)|skin ?care|whitening|anti-?aging|acne|pimple|exfoliat\w*|sheet masks?|eye cream|"
     r"night cream|day cream|retinol|niacinamide|hyaluronic|soap)\b"),
    ("haircare", "beauty_health",
     r"\b(?:shampoo|conditioner|hair (?:dryers?|straighteners?|curlers?|oil|color|dye|treatment|mask|serum|spray|wax|gel|"
     r"iron|brush|comb|removal)|blow ?dryers?|wigs?|hair|flat iron|curling iron|keratin|hairbrush)\b"),
    ("personal_care", "beauty_health",
     r"\b(?:razors?|shavers?|trimmers?|epilators?|toothbrush(?:es)?|toothpaste|deodorants?|perfumes?|colognes?|"
     r"body (?:wash|spray|mist)|sanitary|napkins?|menstrual|feminine|condoms?|mouthwash|floss|cotton buds|cotton swabs|"
     r"hand sanitizers?|alcohol|nail clippers?|tweezers?|bath|loofah|lip care)\b"),
    # --- everything else ---
    ("sports_fitness", "sports_outdoor",
     r"\b(?:dumbbells?|barbells?|kettlebells?|yoga|gym|fitness|exercise|treadmills?|resistance bands?|jump ropes?|"
     r"basketball|football|volleyball|badminton|rackets?|swim(?:ming)? goggles|bicycles?|bikes?|fishing|camping|tents?|"
     r"hiking|sleeping bags?|push[- ]?up|ab roller|boxing|skateboards?|scooters?|sports?|golf|tennis|table tennis|"
     r"trekking|climbing|swimming|water bottles? sports|hydration)\b"),
    ("pet", "pets",
     r"\b(?:dogs?|cats?|pets?|puppy|puppies|kittens?|aquariums?|fish tanks?|bird cages?|litter|cat (?:food|litter)|"
     r"dog (?:food|leash|collar|bed|treats?)|leash|collars?|hamsters?|rabbits?|pet (?:bowl|carrier)|fish food)\b"),
    ("musical_instruments", "office_media",
     r"\b(?:guitars?|ukuleles?|pianos?|violins?|drums?|harmonicas?|flutes?|saxophones?|keyboard pianos?|midi|"
     r"synthesizers?|bass guitar|amp(?:lifier)? guitar|tambourines?|trumpets?)\b"),
    ("phone", "electronics",
     r"\b(?:redmi|realme|infinix|tecno|poco|oppo|vivo|xiaomi|samsung|huawei|honor|nokia|oneplus)\b"),
    ("food_beverage", "food_grocery",
     r"\b(?:coffee|tea|snacks?|noodles?|chocolates?|biscuits?|cookies?|candy|candies|sauce|spices?|milk|juice|cereals?|"
     r"instant|canned|crackers?|chips|dried (?:mango|fruit)|honey|jam|pasta|flour|sugar|salt|seasoning|syrup|"
     r"condiments?|rice|oil|vinegar|nuts|oats|granola|cheese|butter|bread|cake|dessert|beverage|drink mix|pancit|"
     r"frozen|meat|dried fish|eggs?|vegetables?|fruits?|bagoong|longganisa|tocino|dried squid|tuyo)\b"),
    # --- the long tail: only titles nothing above recognizes ---
    ("collectibles_hobbies", "baby_kids_toys",
     r"\b(?:trading cards?|pok[eé]mon|yu-?gi-?oh|funko|collectibles?|blind box(?:es)?|pop ?mart|labubu|gundam|"
     r"anime|k-?pop|photo ?cards?|light ?sticks?|comic|coins?|stamps?|hot wheels|figures?|merch)\b"),
    ("crafts_diy", "office_media",
     r"\b(?:crochet|yarn|knitting|cross ?stitch|embroidery|beads?|sewing|craft(?:s| supplies| kit)?|resin|clay|canvas|"
     r"paint(?:ing)? (?:set|kit|brush)|watercolou?rs?|acrylic paint|glitter|diy|origami|scrapbook|washi|wool)\b"),
    ("party_gifts", "office_media",
     r"\b(?:balloons?|party|gift (?:wrap|box|bags?|sets?)|souvenirs?|greeting cards?|birthday|wedding|christmas|"
     r"giveaways?|confetti|banners?|lootbags?|loot bags?|pasko|costumes? party)\b"),
    ("office_equipment", "office_media",
     r"\b(?:calculators?|bond paper|printer paper|whiteboards?|shredders?|laminators?|label makers?|"
     r"barcode scanners?|cash registers?|binders?|envelopes?|id (?:lace|holders?)|badge holders?|thermal paper|receipt paper)\b"),
    ("bath_plumbing", "home_living",
     r"\b(?:shower ?heads?|faucets?|bidets?|toilets?|sinks?|water filters?|pipes?|drains?|bathroom|towel racks?|"
     r"soap dispensers?|water pumps?|plumbing)\b"),
    ("electrical_supplies", "automotive_tools",
     r"\b(?:electrical wires?|wires?|circuit breakers?|outlets?|wall switch(?:es)?|junction box|conduit|terminal blocks?|"
     r"fuses?|electrical tape|cable ties|wire connectors?|sockets?|lighting fixtures?)\b"),
)
_COMPILED = tuple((name, re.compile(pattern, re.I)) for name, _group, pattern in _RULES)
# The head of a title ends at the first of these: what follows is what the product comes with or fits.
_HEAD_END = re.compile(r"\s(?:for|with|w/|free|plus)\s|\s[+&|-]\s|[,(|]", re.I)
# Shop names, slogans and bracketed promotions that say nothing about what the product is.
_PROMO = re.compile(
    r"[【\[][^】\]]{0,80}[】\]]|\b(?:official store|flagship store|local (?:seller|stock)|free shipping|"
    r"buy 1 take 1|hot sale|new arrival|on sale)\b",
    re.I,
)
CATEGORIES = tuple(dict.fromkeys(name for name, _group, _pattern in _RULES)) + (OTHER,)
# Groups, for saying what a scan covers ("best used for electronics"). OTHER is its own group.
GROUPS: dict[str, str] = {name: group for name, group, _pattern in _RULES} | {OTHER: OTHER}


def group_of(category: str | None) -> str:
    """The broad group a category belongs to (electronics, home_living, fashion ...); OTHER when unknown."""
    return GROUPS.get(category or OTHER, OTHER)


def classify_listing(listing: Any) -> str:
    """The category of a product from its title; OTHER when none is recognized.

    `listing` is the product's {"name": ..., "description": ...}; a plain title
    string is also accepted. Returns OTHER when category reading is switched off.
    """
    if PRODUCT_CATEGORY_OFF:
        return OTHER
    title = listing.get("name") if isinstance(listing, dict) else listing
    title = _PROMO.sub(" ", str(title or ""))
    # The head first, then each later part, then the whole title: a title that opens with a shop name or a slogan
    # ("Official Store | Tapo C200C WiFi IP Camera") is read from the first part that names a product.
    segments = [part for part in _HEAD_END.split(title) if part.strip()]
    for text in (*segments, title):
        for name, pattern in _COMPILED:
            if pattern.search(text):
                return name
    return OTHER


def _files(category: str, suffix: str) -> tuple[Path, ...]:
    """The files that apply to a category: its own, then its group's."""
    names = (category, f"group_{group_of(category)}")
    return tuple(path for path in (CATEGORY_DIR / f"{name}{suffix}" for name in names) if path.is_file())


def _rows(path: Path, width: int) -> list[list[str]]:
    with path.open("r", encoding="utf-8", newline="") as file:
        lines = (line for line in file if line.strip() and not line.startswith("#"))
        return [(values + [""] * width)[:width] for values in csv.reader(lines, delimiter="	")]


@lru_cache(maxsize=None)
def _exceptions(category: str) -> tuple[tuple[re.Pattern[str], str, re.Pattern[str] | None, str], ...]:
    rows = []
    for path in _files(category, ".tsv"):
        for term, label, unless, reason in _rows(path, 4):
            try:
                rows.append(
                    (
                        re.compile(term.strip(), re.I),
                        label.strip(),
                        re.compile(rf"\b(?:{unless.strip()})\b", re.I) if unless.strip() else None,
                        reason.strip(),
                    )
                )
            except re.error as error:
                raise ValueError(f"{path.name}: bad pattern in the row for {term!r}: {error}") from error
    return tuple(rows)


@lru_cache(maxsize=None)
def _additions(category: str) -> tuple[tuple[str, str, int, re.Pattern[str], str], ...]:
    rows = []
    for path in _files(category, ".add.tsv"):
        for term, label, severity, reason in _rows(path, 4):
            try:
                pattern = re.compile(rf"(?<!\w)(?:{term.strip()})(?!\w)")
                rows.append((term.strip(), label.strip(), int(severity or 1), pattern, reason.strip()))
            except (re.error, ValueError) as error:
                raise ValueError(f"{path.name}: bad row for {term!r}: {error}") from error
    return tuple(rows)


def added_terms(category: str | None, label: str) -> tuple[tuple[str, int, re.Pattern[str]], ...]:
    """What reviewers of this kind of product report under `label` that the general lists do not know.

    Returned as (term, severity, pattern), the shape the hazard tagger reads its own terms in.
    """
    if not category or category == OTHER or PRODUCT_CATEGORY_OFF:
        return ()
    return tuple((term, severity, pattern) for term, row_label, severity, pattern, _reason in _additions(category) if row_label == label)


def clear_cache() -> None:
    """Forget the category files, e.g. after one was edited in a test."""
    _exceptions.cache_clear()
    _additions.cache_clear()


def exemption(category: str | None, label: str, normalized: str, span: tuple[int, int], reach: int = 3) -> str | None:
    """The reason a flagged phrase is not a complaint in this category, or None.

    `normalized` is the sentence the span was found in. Words within `reach`
    words of the phrase are checked against the row's `unless` pattern.
    """
    if not category or category == OTHER or PRODUCT_CATEGORY_OFF:
        return None
    start, end = span
    phrase = normalized[start:end].strip()
    nearby = " ".join(normalized[:start].split()[-reach:] + normalized[end:].split()[:reach])
    for term, row_label, unless, reason in _exceptions(category):
        if row_label != label or not term.fullmatch(phrase):
            continue
        if unless is not None and unless.search(nearby):
            continue
        return reason or f"not a complaint on a {category}"
    return None
