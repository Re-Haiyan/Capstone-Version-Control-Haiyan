"""Exact backup-title regressions and read-only historical report compatibility."""
import copy
import sys
import unittest
from pathlib import Path
from unittest.mock import patch
ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT/'backend'), str(ROOT/'backend/sentiment-analysis')]
import dashboard_utils as du
from defaketive_sentiment.product_category import classify_listing
CASES = {
 'HP 14" HD AMD Athlon 7120 4GB RAM / 128GB UFS AMD Radeon Graphics Win 11 Home Moonlight Blue': ('phone','laptop'),
 'POCO Pad C1 | 4+64GB/6+128GB | 9.7" 2K 120Hz crystal-clear display, Massive 7600mAh (typ) battery, Snapdragon® 6s 4G Gen 2 Mobile Platform, Powered by Xiaomi HyperOS 3': ('phone','tablet'),
 '🎖 TP-Link Official Store | Tapo C200C | 1080p Indoor 360 Degrees Pan and Tilt Wireless WiFi IP Security CCTV Sale Hidden Camera Connect to Cellphone Two Way Audio with Mic and Speaker [NO WALL MOUNT INCLUDED]': ('phone','camera'),
 '【Local Stock & 360° Phone View】V380 PRO 100% Original dual lens CCTV camera connect to cellphone cctv camera wifi connect 360 ip security cameras needed 8MP Two-Way Audio Night Vision waterproof with audio and speaker cctv security small cameras': ('phone','camera'),
 'Original LCD For Infinix Smart 8 / Smart 8 HD / Smart 8 Pro X6525 X6525B /Smart 8 Plus X6526 LCD Display Touch Screen with Frame Replacement': ('phone','accessory'),
 'Original LCD For Oppo Realme Note 50/Note 60 RMX3834 LCD Display with Frame Touch Screen Replacement': ('phone','accessory'),
}
class ProductionCategoryPort(unittest.TestCase):
 def test_exact_titles(self):
  for title,(_,category) in CASES.items():
   with self.subTest(title=title): self.assertEqual(classify_listing(title),category)
 def test_historical_flags_and_results_preserved_until_recheck(self):
  for title,(old,new) in CASES.items():
   with self.subTest(title=title):
    report={'name':title,'product_category':old,'sentiment_summary':{'schema_version':'defaketive-summary-2.0','verdict':{'state':'safety_warning'}},'comments':[{'content':'It sparked.','sentiment_analysis':{'model_version':'same+pc7+xlmr-same','label':'positive','review_tags':['safety','defect','counterfeit'],'review_extra_tags':['quality','not_as_described']}}]}
    before=copy.deepcopy(report)
    with patch.object(du,'sentiment_model_version',return_value='same+pc8+xlmr-same'):
     self.assertFalse(du.analysis_is_current([report]))
    self.assertEqual(report,before)
 def test_unknown_replacement_retains_saved_alias_fallback(self):
  self.assertEqual(classify_listing({'name':'Unbranded Replacement Widget','category':'Kitchen Dining'}),'kitchen_dining')
 def test_controls(self):
  for title,expected in {'Samsung Galaxy A15 Smartphone':'phone','POCO X7 5G Phone':'phone','Android Phone with LCD Screen':'phone','Case for POCO Pad C1':'accessory','USB-C Charger for HP 14 inch':'charger_cable','Wall Mount Bracket for CCTV Camera':'accessory','USB Cable for Ceiling Fan':'charger_cable','Vone USB Ceiling Fan 6 blade ceiling fan USB Cable Fan Household Hanging Fan Foldable Portable Fan':'small_appliance'}.items():
   with self.subTest(title=title): self.assertEqual(classify_listing(title),expected)
if __name__=='__main__':unittest.main()
