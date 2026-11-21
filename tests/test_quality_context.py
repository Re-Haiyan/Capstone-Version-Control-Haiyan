import sys,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'backend/sentiment-analysis'))
from defaketive_sentiment.registry import load_model
class QualityContext(unittest.TestCase):
 @classmethod
 def setUpClass(cls):cls.model=load_model()
 def check(self,title,text,expected):
  a=self.model.analyze(text,5,listing={'name':title});self.assertEqual('quality' in a.get('review_extra_tags',[]),expected,a)
  self.assertEqual(a['label'],a['sentiment']['initial_label']);return a
 def test_paired_praise_complaint_and_mixed(self):
  cases=[
   ('Cotton Shirt','So thin, breathable and comfortable for hot weather.',False),
   ('Kitchen Curtain','I love it because the material is very thin and airy.',False),
   ('Cotton Shirt','Maganda at manipis ang tela, presko at comfortable.',False),
   ('Kitchen Curtain','Not happy with it. Material is very thin.',True),
   ('Kitchen Curtain','Beautiful design but the material is too thin.',True),
   ('USB Handheld Fan','Wind strength:weak, not conducive for humid weather.',True),
   ('USB Handheld Fan','Strong wind and quiet operation.',False),
   ('USB Handheld Fan','Maganda pero mahina ang buga.',True),
   ('USB Handheld Fan','Good build but the air coverage is quite limited.',True),
   ('Power Bank','Mabilis po siyang mag lowbat.',True),
   ('Power Bank','Hindi mabilis ma lowbat, works all day.',False),
   ('Power Bank','Not a slow charger, it works fast.',False),
   ('Power Bank','Great design but slow charger.',True),
   ('Power Bank','My old charger was a slow charger. This one is fast.',False),
   ('Tablet','Napakabagal. naglalag gamitin.',True),
   ('Thermal Tumbler','Good design but very poor insulation.',True),
   ('Car Cleaning Towel','Water absorption:sablay',True),
   ('Car Cleaning Towel','Excellent water absorption.',False),
   ('Hair Dryer','Strong wind but frizzes hair too.',True),
  ]
  for title,text,expected in cases:
   with self.subTest(text=text):self.check(title,text,expected)
 def test_independent_fault_and_hazard_survive(self):
  for text,flag in [('Good quality but the cable sparked.','safety'),('Looks good but the plug melted.','safety'),('Works on powerbank but the motor stopped working.','defect')]:
   with self.subTest(text=text):
    a=self.model.analyze(text,5,listing={'name':'USB Fan'});self.assertIn(flag,a['review_tags'])
if __name__=='__main__':unittest.main()
