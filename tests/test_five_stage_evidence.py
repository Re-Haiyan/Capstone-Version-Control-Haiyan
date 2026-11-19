"""Evidence provenance and independent full-review concern regressions."""
import copy
import sys
import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'backend'),str(ROOT/'backend/sentiment-analysis'),str(ROOT/'tests')]
from defaketive_sentiment import category_context as cc,registry
from defaketive_sentiment.product_category import classify_listing
from test_product_category import TITLES,PC3_TITLES
import dashboard_utils as du
class ContextEvidence(unittest.TestCase):
 def test_sold_object_wins_over_incidental_specs(self):
  for title,category in {
   'Lenovo M20 Laptop Office Wired Mouse Desktop Computer Mouse Gaming Mouse Mouse pad':'computer_peripheral',
   'GOOJODOQ Bluetooth Wireless Mouse Modern Slim And Silent Rechargeable iPad Tablet Phone Universal Portable':'computer_peripheral',
   'Lenovo ThinkPad X240 Laptop Intel Quad/Dual-Core i7/i5 8GB RAM 128G SSD+500GB/1T HDD ROM Built-in WEBCAM/Camera Online class/learning Wifi Bluetooth Ms office 365 Windows11 Pro Portable Business Notebook Computer Ultra-thin 12.5 inch Screen':'laptop',
   'Birch Juice Eye Balm Stick Under Eye Care':'skincare',
   'Bullet Juice & Vegetable Extractor 12PCS Set Blender Multifunction High Speed Food Processor':'small_appliance',
   'Laptop Stand for Lenovo ThinkPad Intel Windows11':'accessory',
   'Replacement Screen for Lenovo ThinkPad Intel Windows11':'accessory',
   'Case for Wireless Mouse':'accessory',
   'Wireless Mouse Case':'accessory',
   'Fresh Vegetable Juice':'food_beverage',
  }.items():
   with self.subTest(title=title):self.assertEqual(classify_listing(title),category)
  self.assertNotEqual(classify_listing('Replacement Blade for Juice & Vegetable Extractor'),'small_appliance')
 def test_live_discovery_identifies_the_actual_toy(self):
  self.assertEqual(classify_listing('Electric Car For Kids Ride On Jeep Off-road 4 Wheel Vehicle With Remote Control Rechargeable Car With Light And Music'),'toys')
  self.assertEqual(classify_listing('Charger for Electric Car For Kids'),'charger_cable')
  # This ambiguous suffix must not trigger the new explicit ride-on rule.
  self.assertNotEqual(classify_listing('Electric Car For Kids 12V Charger'),'toys')
  self.assertNotEqual(classify_listing('Electric Car For Kids Replacement Battery'),'toys')
  self.assertEqual(classify_listing('Electric Car Charging Adapter'),'charger_cable')
 def test_other_gap_discoveries_identify_sold_items(self):
  for title,category in {
   '【Y.I.A】 5ply 50g MC Milk Cotton Yarn 90 PLUS COLOR Crochet Thread wool Knitted Weaving Crafts DIY Gift Woven':'crafts_diy',
   'PUREGOLD P300 Worth eVoucher (via email)':'digital_goods',
   'CHNT CHINT NXB-63 2P AC 230/400V Miniature Circuit Breaker C 6 10 16 20 25 32 40 63A Overload Protector DZ47 C Style Air Switch':'electrical_supplies',
   'Fresh Milk 1L':'food_beverage','Crochet Yarn Pattern Book':'stationery_books',
   'Protective Case for Circuit Breaker':'accessory','Circuit Breaker Cover':'accessory',
  }.items():
   with self.subTest(title=title):self.assertEqual(classify_listing(title),category)
 def test_usb_fan_and_its_parts(self):
  self.assertEqual(classify_listing('Vone USB Ceiling Fan 6 blade ceiling fan USB Cable Fan Household Hanging Fan Foldable Portable Fan'),'small_appliance')
  self.assertEqual(classify_listing('USB Cable for Ceiling Fan'),'charger_cable')
  self.assertEqual(classify_listing('USB Ceiling Fan Power Adapter'),'charger_cable')
 def test_all_categories_preserve_both_sides_and_literal_quotes(self):
  titles={v:k for k,v in {**TITLES,**PC3_TITLES}.items()}
  for category,p in cc._profiles()['profiles'].items():
   with self.subTest(category=category):
    review=p['positive_phrases'][0]+' but '+p['negative_phrases'][0]
    r=cc.check(review,{'name':titles[category]},'neutral')
    self.assertTrue(r['mixed_feedback'],r);self.assertTrue(r['abstained']);self.assertIsNone(r['context_signal'])
    self.assertFalse(r['sentiment_overridden']);self.assertFalse(r['used_for_decision'])
    for q in r['observations']:self.assertEqual(review[q['start']:q['end']],q['text'])
 def test_negated_evidence_is_retained_as_negated(self):
  r=cc.check('Not clear sound.',{'name':'Bluetooth Speaker'},'negative')
  self.assertTrue(any(q['negated'] for q in r['observations']))
  self.assertIsNone(r['context_signal'])
 def test_unmapped_normalized_wording_abstains_without_inventing_a_quote(self):
  r=cc.check('ｄｉｇｉｔａｌ ｃｏｄｅ',{'name':'Gift Voucher'},'neutral')
  self.assertEqual(r['status'],'ambiguous');self.assertTrue(r['abstained']);self.assertFalse(r['observations'])
 def test_long_review_and_unclassified(self):
  text='Delivery was on time. '*300+'Clear sound.'
  r=cc.check(text,{'name':'Bluetooth Speaker'},'neutral')
  self.assertTrue(any(q['text']=='Clear sound' for q in r['observations']))
  r=cc.check('Good.',{'name':'XYZ 88991'},'positive');self.assertEqual(r['status'],'unclassified');self.assertFalse(r['observations'])
 def test_export_retains_mixed_evidence(self):
  m=registry.load_model();p=du.analyze_products([{'name':'Bluetooth Speaker','comments':[{'content':'Clear sound but sound keeps crackling','rating':3}]}])[0]
  row=du.review_rows([p])[0];self.assertIn('explicit_complaint',row['Category observations']);self.assertTrue(row['Mixed category feedback'])
 def test_export_preserves_historical_five_flags_scores_and_text(self):
  import json
  flags=['safety','defect','counterfeit','quality','not_as_described']
  scores={'negative':.1,'neutral':.2,'positive':.7}
  p={'name':'Historical item','product_category':'other','comments':[{'content':'Exact saved review.','rating':5,'sentiment_analysis':{'label':'positive','sentiment':{'initial_label':'positive','probabilities':scores},'review_tags':flags[:3],'review_extra_tags':flags[3:],'review_evidence':{'safety':{'spans':[{'text':'Exact saved review.'}]}}}}]}
  before=copy.deepcopy(p);row=du.review_rows([p])[0]
  self.assertEqual(row['Review'],'Exact saved review.');self.assertEqual(row['Initial sentiment'],'positive')
  self.assertEqual(json.loads(row['Initial sentiment scores']),scores)
  self.assertEqual(set(row['Review-reported concerns'].split(', ')),set(flags))
  self.assertEqual(json.loads(row['Concern evidence']),p['comments'][0]['sentiment_analysis']['review_evidence'])
  self.assertEqual(p,before)
class FullReviewConcerns(unittest.TestCase):
 @classmethod
 def setUpClass(cls):cls.model=registry.load_model()
 def check(self,text,title='USB Ceiling Fan'):
  return self.model.analyze(text,5,listing={'name':title})
 def test_savings_punctuation_does_not_become_shock(self):
  for text in ('Very useful at tipid a kuryente,kaya dn mga power bank.','Tipid sa kuryente,powered by USB.'):
   with self.subTest(text=text):self.assertNotIn('safety',self.check(text)['review_tags'])
 def test_shocks_and_separate_hazards_survive_savings_and_praise(self):
  for text in ('Tipid sa kuryente, pero nakuryente ako.','Very useful at tipid a kuryente,kaya sulit. The plug sparked.','Great fan! The cable burned my hand.'):
   with self.subTest(text=text):
    r=self.check(text);self.assertIn('safety',r['review_tags']);self.assertTrue(r['review_evidence']['safety']['spans'])
 def test_full_review_after_initial_model_window(self):
  r=self.check('Excellent quality. '*300+'The cable sparked and burned my hand.')
  self.assertIn('safety',r['review_tags']);self.assertTrue(r['review_evidence']['safety']['spans'])
 def test_negated_shock(self):self.assertNotIn('safety',self.check('The fan did not spark or overheat.')['review_tags'])
 def test_food_flavor_exemption_does_not_hide_incidents(self):
  for text in ('Smoky cheese flavor.','The food tasted burnt.','The food was hot.'):
   with self.subTest(text=text):self.assertNotIn('safety',self.check(text,'Instant Coffee')['review_tags'])
  for text in ('The hot soup burned my hand.','Maganda at sulit. Pero umusok ang produkto.','I love this product! It sparked and burned my hand.'):
   with self.subTest(text=text):self.assertIn('safety',self.check(text,'Instant Coffee')['review_tags'])
if __name__=='__main__':unittest.main()
