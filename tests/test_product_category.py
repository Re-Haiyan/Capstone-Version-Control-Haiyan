"""product_category pc1: the same word is read by the kind of product it describes."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend" / "sentiment-analysis"))

from defaketive_sentiment import product_category  # noqa: E402
from defaketive_sentiment.hazard_model import QUALITY, LexiconHazardTagger  # noqa: E402

TITLES = {
    "Samsung Galaxy A15 Smartphone 128GB": "phone",
    "iPhone 13 Pro Max": "phone",
    "Realme C55 6GB+128GB": "phone",
    "ASUS Vivobook 15 Laptop i5": "laptop",
    "MacBook Air M2": "laptop",
    "Xiaomi 20000mAh Power Bank Fast Charging": "powerbank",
    "Redmi Buds 4 Wireless Earbuds": "audio",
    "iPhone 14 Silicone Case": "accessory",
    "Laptop Sleeve Bag 15.6": "accessory",
    "USB Type-C Cable 3A": "charger_cable",
    "Oversized T-shirt Cotton": "apparel",
    "Samsung Galaxy Tab A9 Tablet": "tablet",
    "Smart Watch Series 9": "wearable",
    "Realme C55 33W Fast Charging 6GB+128GB": "phone",
    "ASUS Laptop with built-in mic and bag": "laptop",
    "Samsung Galaxy Tab A9 with Case": "tablet",
    "Case for iPhone 14": "accessory",
    "Xiaomi Power Bank for iPhone": "powerbank",
    "Hot Item - Samsung Galaxy A15": "phone",
    # Pc2: the whole marketplace. Tricky ones first: a word that belongs to another category must not win.
    "Samsung 55 inch Smart TV 4K": "tv_display",
    "Xiaomi Redmi Note 13 Pro 5G 108MP Camera 8GB RAM": "phone",
    "Infinix Hot 40i 8GB RAM 128GB": "phone",
    "Realme C55 6GB+128GB": "phone",
    "Samsung Refrigerator Inverter 2 Door": "small_appliance",
    "Baby Monitor with Camera": "baby",
    "Philips Air Fryer 4L": "small_appliance",
    "Desk Lamp LED Rechargeable": "home_decor_lighting",
    "Laptop Cooling Pad with Fan": "accessory",
    "Lenovo IdeaPad 15 512GB SSD": "laptop",
    "Mechanical Keyboard Hot Swappable Keycap RGB": "computer_peripheral",
    "Vitamin C 500mg Tablets": "health_supplements",
    "Disposable Face Mask 3ply 50pcs": "medical_devices",
    "Hydrating Face Mask Sheet": "skincare",
    "Men's Cotton T-shirt Oversized": "apparel",
    "Women's Running Shoes Sneakers": "footwear",
    "Leather Handbag Women Sling Bag": "bags",
    "Gold Necklace Pendant 18k": "jewelry_accessories",
    "Matte Lipstick Waterproof": "makeup",
    "Hair Dryer 2000W Foldable": "haircare",
    "Shampoo and Conditioner Set": "haircare",
    "Electric Toothbrush Sonic": "personal_care",
    "Disposable Diapers Size M": "baby",
    "LEGO Classic Building Blocks": "toys",
    "Yoga Mat Non Slip": "sports_fitness",
    "Dumbbell Set 20kg Adjustable": "sports_fitness",
    "Dog Food Dry Adult 5kg": "pet",
    "Cat Litter Box": "pet",
    "Engine Oil 10W-40 Motorcycle": "automotive",
    "Motorcycle Helmet Full Face": "automotive",
    "Cordless Drill 21V Tool Set": "tools_hardware",
    "Flower Pot Ceramic with Saucer": "garden_plants",
    "Frying Pan Non-stick 28cm": "kitchen_dining",
    "Stainless Water Bottle 1L Tumbler": "kitchen_dining",
    "Office Chair Ergonomic Mesh": "furniture",
    "Bedsheet Set Queen Size Cotton": "home_textile",
    "Spiral Notebook A5 Ruled": "stationery_books",
    "Gel Pen 0.5 Black 12pcs": "stationery_books",
    "Acoustic Guitar 41 inch": "musical_instruments",
    "Kopiko Coffee Mix 30 sachets": "food_beverage",
    "Detergent Powder 1kg Laundry": "household_cleaning",
    "PS5 DualSense Controller": "gaming",
    "GoPro Hero 12 Action Camera": "camera",
    "Smart Plug WiFi 16A": "smart_home",
    "Epson Printer Ink Tank": "computer_peripheral",
    "Pencil Case Large Capacity": "stationery_books",
    "Screen Protector Tempered Glass": "accessory",
    "Apple Watch Band Silicone Strap": "accessory",
    "Stand Fan 16 inch": "small_appliance",
    "Phone Holder Car Mount": "accessory",
    "Wireless Mouse 2.4G Silent": "computer_peripheral",
    "Sunscreen SPF50 Face Lotion": "skincare",
    "Fake Nails Press On Set": "makeup",
    "Slim Laptop Backpack Anti-theft": "accessory",
    "Travel Backpack 40L": "bags",
    "Digital Kitchen Scale": "kitchen_dining",
    "🎖 TP-Link Official Store | Tapo C200C 1080p Indoor WiFi IP Camera": "camera",
    "【Local seller +COD】Wireless Mechanical Keyboard RGB": "computer_peripheral",
    "Random Seller Item 123": "other",
    "Hot Item Best Seller": "other",
    "": "other",
}
THIN = "ang nipis, parang madaling mabali"
THIN_PRAISE = "ang manipis ng phone, ganda tingnan"


def tagger() -> LexiconHazardTagger:
    # The app always gives the tagger a sentiment reader; "neutral" lets the learned quality add-on try to
    # bring the flag back, which is exactly what an exemption must also stop.
    return LexiconHazardTagger(rules="0.4", counterfeit_rules="c2", sentiment_label=lambda text: "neutral")


def quality(result: dict) -> bool:
    return QUALITY in (result.get("extra_tags") or [])


# pc3: the rest of the marketplace sections (digital goods, eyewear, motorcycles, collectibles, crafts, party, office, plumbing, electrical).
PC3_TITLES = {
    "Netflix Premium 1 month account": "digital_goods",
    "Mobile Legends game credits": "digital_goods",
    "Ray-Ban Style Sunglasses UV400": "eyewear",
    "Acuvue contact lenses monthly": "eyewear",
    "Mio Sporty Powerpipe": "motorcycle",
    "Motorcycle Side Mirror pair": "motorcycle",
    "Electric Bike 48V": "motorcycle",
    "PowMr 12V 100AH LiFePo4 Battery Solar Battery": "battery_solar",
    "Solar Inverter 3000W": "battery_solar",
    "Pokemon trading cards booster": "collectibles_hobbies",
    "Labubu blind box": "collectibles_hobbies",
    "Crochet yarn 100g": "crafts_diy",
    "Acrylic paint set 24 colors": "crafts_diy",
    "Birthday party balloons set": "party_gifts",
    "Casio scientific calculator": "office_equipment",
    "Shower head high pressure": "bath_plumbing",
    "Circuit breaker 20A": "electrical_supplies",
    "Intel Core i5 12400F Processor": "computer_peripheral",
    "TP-Link wifi extender": "computer_peripheral",
    "Redmi 13C 6GB RAM 128GB ROM": "phone",
    "A3x 5G 12+512GB Screen 6.67-inch Mediatek Dimensity 6300": "phone",
    # a word from a new category must not take a title from one that has its own exceptions
    "Tablet 8GB RAM 256GB ROM Helio G99": "tablet",
    "Asus Laptop Snapdragon X 16GB RAM": "laptop",
    "Birthday dress for girls": "apparel",
    "Cotton t-shirt party": "apparel",
    "Women clutch bag": "bags",
    "solar light 50000W Solar Led Outdoor Flood Light Street Lamp": "home_decor_lighting",
    "Motorcycle Bluetooth headset": "audio",
}


class MarketplaceScopeTests(unittest.TestCase):
    def test_new_sections(self) -> None:
        for title, expected in PC3_TITLES.items():
            with self.subTest(title=title):
                self.assertEqual(product_category.classify_listing({"name": title}), expected)

    def test_every_category_has_a_group(self) -> None:
        for name in product_category.CATEGORIES:
            self.assertTrue(product_category.group_of(name))
        self.assertEqual(len(product_category.CATEGORIES), 50)  # 49 categories and "other"


class ClassifyTests(unittest.TestCase):
    def test_titles(self) -> None:
        for title, expected in TITLES.items():
            with self.subTest(title=title):
                self.assertEqual(product_category.classify_listing({"name": title}), expected)

    def test_title_string_and_missing_name(self) -> None:
        self.assertEqual(product_category.classify_listing("Gaming Laptop"), "laptop")
        self.assertEqual(product_category.classify_listing({}), "other")
        self.assertEqual(product_category.classify_listing(None), "other")


class ExemptionTests(unittest.TestCase):
    def test_thin_is_not_a_complaint_on_a_phone_or_laptop(self) -> None:
        for category in ("phone", "laptop", "tablet", "powerbank", "wearable"):
            with self.subTest(product_kind=category):
                result = tagger().tag_sentence(THIN_PRAISE, product_kind=category)
                self.assertFalse(quality(result), result.get("extra_terms"))
                self.assertTrue(result.get("category_exempt"))

    def test_thin_is_still_a_complaint_without_a_category(self) -> None:
        self.assertTrue(quality(tagger().tag_sentence(THIN_PRAISE)))
        self.assertTrue(quality(tagger().tag_sentence(THIN_PRAISE, product_kind="other")))

    def test_thin_is_still_a_complaint_on_clothes_and_cables(self) -> None:
        for category in ("apparel", "charger_cable", "audio", "accessory"):
            with self.subTest(product_kind=category):
                self.assertTrue(quality(tagger().tag_sentence(THIN_PRAISE, product_kind=category)))

    def test_thin_part_or_material_stays_a_complaint_on_a_phone(self) -> None:
        for sentence in ("manipis na plastic ng case", "ang nipis ng cable", "the cable is too thin", "manipis ang tunog"):
            with self.subTest(sentence=sentence):
                self.assertTrue(quality(tagger().tag_sentence(sentence, product_kind="phone")))

    def test_cancelling_words_match_whole_words_only(self) -> None:
        # "case" inside "staircase" and "band" inside "husband" are not the phone's case or band.
        for sentence in ("manipis, sabi ng husband ko", "manipis, nakita ko sa staircase"):
            with self.subTest(sentence=sentence):
                self.assertFalse(quality(tagger().tag_sentence(sentence, product_kind="phone")))

    def test_every_category_file_is_valid(self) -> None:
        product_category.clear_cache()
        files = sorted(product_category.CATEGORY_DIR.glob("*.tsv"))
        self.assertTrue(files)
        for path in files:
            with self.subTest(file=path.name):
                # A file is named for a category (phone.tsv, phone.add.tsv) or a group (group_fashion.tsv); the
                # rules read both, so the check is that every file belongs to something and loads (pc3).
                stem = path.name[: -len('.add.tsv')] if path.name.endswith('.add.tsv') else path.stem
                groups = {product_category.group_of(name) for name in product_category.CATEGORIES}
                self.assertTrue(
                    stem == 'all' or stem in product_category.CATEGORIES or (stem.startswith('group_') and stem[len('group_'):] in groups), stem
                )
        for name in product_category.CATEGORIES:
            product_category._exceptions(name)
            product_category._additions(name)

    def test_a_bad_pattern_names_its_file(self) -> None:
        import tempfile

        with tempfile.TemporaryDirectory() as folder:
            (Path(folder) / "phone.tsv").write_text("(unclosed\tquality\t\twhy\n", encoding="utf-8")
            original = product_category.CATEGORY_DIR
            product_category.CATEGORY_DIR = Path(folder)
            product_category.clear_cache()
            try:
                with self.assertRaisesRegex(ValueError, "phone.tsv"):
                    product_category._exceptions("phone")
            finally:
                product_category.CATEGORY_DIR = original
                product_category.clear_cache()

    def test_other_complaints_on_a_phone_are_untouched(self) -> None:
        result = tagger().tag_sentence("manipis pero madaling masira at flimsy", product_kind="phone")
        self.assertTrue(quality(result))


class GroupAndMoreExemptionTests(unittest.TestCase):
    def test_every_category_belongs_to_a_group(self) -> None:
        for category in product_category.CATEGORIES:
            with self.subTest(category=category):
                self.assertTrue(product_category.group_of(category))
        self.assertEqual(product_category.group_of("phone"), "electronics")
        self.assertEqual(product_category.group_of("apparel"), "fashion")
        self.assertEqual(product_category.group_of("nonsense"), "other")
        self.assertEqual(product_category.group_of(None), "other")

    def test_thin_is_fine_on_a_keyboard_or_tv_but_not_on_its_keys(self) -> None:
        for kind in ("computer_peripheral", "tv_display"):
            with self.subTest(kind=kind):
                self.assertFalse(quality(tagger().tag_sentence("ang manipis ng ganda tingnan", product_kind=kind)))
                self.assertTrue(quality(tagger().tag_sentence("manipis ang keycaps", product_kind=kind)))

    def test_thin_stays_a_complaint_in_categories_without_a_file(self) -> None:
        for kind in ("skincare", "footwear", "home_textile", "kitchen_dining", "toys"):
            with self.subTest(kind=kind):
                self.assertTrue(quality(tagger().tag_sentence("ang manipis ng ganda tingnan", product_kind=kind)))


class ReviewTests(unittest.TestCase):
    def test_listing_title_sets_the_category_for_a_whole_review(self) -> None:
        phone = {"name": "Samsung Galaxy A15 Smartphone", "description": ""}
        shirt = {"name": "Cotton T-shirt", "description": ""}
        on_phone = tagger().tag_review(THIN_PRAISE, 5, listing=phone)
        on_shirt = tagger().tag_review(THIN_PRAISE, 5, listing=shirt)
        self.assertFalse(any(quality(item) for item in on_phone))
        self.assertTrue(any(quality(item) for item in on_shirt))

    def test_no_listing_means_old_behaviour(self) -> None:
        self.assertTrue(any(quality(item) for item in tagger().tag_review(THIN_PRAISE, 5)))


if __name__ == "__main__":
    unittest.main()
