"""Panel pipeline: refined product-title category regression (synthetic titles only).

This checks the classifier proposed for staging, not a new independent
category-accuracy measurement, and never touches the VM or stored reports.
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend" / "sentiment-analysis"))

from defaketive_sentiment import product_category


CASES = {
    # Specific product-title disambiguation (pc5/pc6), retained under pc7.
    "Matte Lipstick in Travel Cup": "makeup",
    "Collagen Face Serum Vitamin C 30ml": "skincare",
    "Herbal Shampoo with Dish Soap Gift": "haircare",
    "RC Toy Car Remote Control Rechargeable": "toys",
    "Whey Protein Isolate 1kg": "health_supplements",
    "( BUY 1 TAKE 1 ) NEW Cetaphil Baby Gentle Wash & Shampoo 400ml": "haircare",
    "Ceelin Gummies with Zinc 30s Bottle": "health_supplements",
    "Samsung Galaxy A15 Smartphone with Lip Balm": "phone",
    # Negative controls; cases and protein shakers are not consumables.
    "Lipstick Case Holder Travel Organizer": "accessory",
    "Shaker Cup for Whey Protein": "kitchen_dining",
    "Whey Protein Shaker Bottle": "kitchen_dining",
    "Baby Feeding Bottle 240ml": "baby",
    "Dish Soap Lemon 500ml": "household_cleaning",
    # Solar/gamepad collision previously observed in product reports.
    "PowMr 4.5kw/6.5kw On-grid/Off-grid Hybrid Inverter 24Vdc/48Vdc 230VAC Pure Sine Wave Solar Inverter Built in 120A MPPT Solar Controller Support Lifepo4 Battery RGB Light": "battery_solar",
    "MPPT Solar Charge Controller 100A for 12V 24V Off-grid Battery": "battery_solar",
    "Solar Controller for LiFePO4 Battery": "battery_solar",
    "PWM Solar Charging Controller 30A": "battery_solar",
    "PS5 DualSense Controller": "gaming",
    "Xbox Wireless Controller": "gaming",
    "Nintendo Switch Gamepad": "gaming",
    "Gaming Controller Bluetooth Wireless for Android": "gaming",
    "Game Controller USB for PC": "gaming",
    "Samsung Refrigerator Inverter 2 Door": "small_appliance",
    "Window Air Conditioner 1HP": "small_appliance",
    "Portable Air-Conditioner 1HP": "small_appliance",
    "Portable Air Conditioner 12000 BTU": "small_appliance",
    "Hair Conditioner With Keratin 200mL": "haircare",
    "Shampoo Conditioner Set": "haircare",
    "3KW Off Grid Solar Inverter 48V": "battery_solar",
    "Random Seller Item 123": "other",
}


class PanelCategoryRefinementTests(unittest.TestCase):
    def test_title_examples(self) -> None:
        for title, expected in CASES.items():
            with self.subTest(title=title):
                self.assertEqual(product_category.classify_listing({"name": title}), expected)

    def test_hp_notebook_specs_without_laptop_keyword(self) -> None:
        cases = {
            'HP 14" HD AMD Athlon 7120 4GB RAM / 128GB UFS AMD Radeon Graphics Win 11 Home Moonlight Blue': "laptop",
            'HP 15.6" Intel Core i5 8GB RAM Windows 11': "laptop",
            'Sleeve for HP 14" AMD Athlon 4GB RAM Windows 11': "accessory",
            'USB-C Charger for HP 14" AMD Athlon Windows 11': "charger_cable",
            "Android Dual SIM 4GB RAM 128GB UFS": "phone",
            "HP 14 inch Monitor": "tv_display",
        }
        for title, expected in cases.items():
            with self.subTest(title=title):
                self.assertEqual(product_category.classify_listing(title), expected)

    def test_device_names_take_priority_over_compatibility_words(self) -> None:
        cases = {
            'POCO Pad C1 | 4+64GB/6+128GB | 9.7" display Snapdragon': "tablet",
            "POCO Pad C1 Protective Case": "accessory",
            "TP-Link Official Store | Tapo C200C | WiFi IP Security CCTV Hidden Camera Connect to Cellphone": "camera",
            "V380 PRO Dual Lens CCTV Camera connect to cellphone": "camera",
            "Android Smartphone with CCTV Camera Viewer": "phone",
            "Wall Mount Bracket for CCTV Camera": "accessory",
            "Original LCD For Infinix Smart 8 / Smart 8 HD LCD Display With Frame Replacement": "accessory",
            "OEM LCD Screen for iPhone 15": "accessory",
            "Android Phone with LCD Screen": "phone",
        }
        for title, expected in cases.items():
            with self.subTest(title=title):
                self.assertEqual(product_category.classify_listing(title), expected)

    def test_taxonomy_size_and_explicit_revision(self) -> None:
        self.assertEqual(len(product_category.CATEGORIES), 50)  # 49 + Other
        self.assertEqual(product_category.PRODUCT_CATEGORY_REVISION, "pc8")

    def test_descriptions_do_not_choose_category(self) -> None:
        self.assertEqual(product_category.classify_listing(
            {"name": "Random Seller Item 123", "description": "PS5 solar controller"}
        ), "other")


if __name__ == "__main__":
    unittest.main()
