"""Development cases, never used as independent validation evidence."""
import sys,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'backend/sentiment-analysis')]
from defaketive_sentiment.registry import load_model

class SupportedConcerns(unittest.TestCase):
 @classmethod
 def setUpClass(cls):cls.model=load_model()
 def analyze(self,title,text):return self.model.analyze(text,5,listing={'name':title})
 def check(self,title,text,flag,expected):
  a=self.analyze(title,text)
  self.assertEqual(flag in a['review_tags']+a.get('review_extra_tags',[]),expected,a)
  self.assertEqual(a['label'],a['sentiment']['initial_label'])
  if expected:
   for span in a['review_evidence'][flag]['spans']:
    self.assertEqual(text[span['review_start']:span['review_end']],span['text'])
  return a
 def test_mechanical_near_miss_and_failed_stop(self):
  for t in [
   'The treadmill is great. A piece of plastic broke off and stuck to the mat, we almost stepped on it.',
   "The treadmill power switch also became defective and we're unable to turn it off without unplugging."]:
   for f in ['safety','defect']:
    with self.subTest(text=t,flag=f):self.check('Electric Walking Pad Treadmill',t,f,True)
 def test_lyric_attribution_and_independent_real_incidents(self):
  lyric="If I warned you that the fire's gonna burn [Chorus: Singer]"
  self.check('Face Foundation',lyric,'safety',False)
  for incident in ['The charger burned my hand.','The cable sparked.','Umusok ang charger.','Natunaw ang plug.','The plug melted.']:
   with self.subTest(incident=incident):self.check('Phone Charger',lyric+' '+incident,'safety',True)
  self.check('Phone Charger','It burned my hand while I was quoting a song.','safety',True)
 def test_safety_controls(self):
  for t in ['Great charger but smoke came out.','Maganda pero umusok ang charger.','Fast charging pero nag spark ang cable.','The plug melted during a power outage.']:
   with self.subTest(text=t):self.check('Phone Charger',t,'safety',True)
  for title,t in [('Hair Dryer','Warm air is normal when drying hair.'),('Phone Charger','The charger did not overheat or smoke.'),('Electric Walking Pad Treadmill','The plastic packaging was removed before walking. The power switch works.')]:
   with self.subTest(text=t):self.check(title,t,'safety',False)
 def test_quality_pairs(self):
  cases=[
   ('Laptop','Ok naman madali lang malobat',True),
   ('Power Bank','Maganda pero ang dali malowbat.',True),
   ('Power Bank','Hindi mabilis malobat, good battery life.',False),
   ('Power Bank','Looks good but the battery drains too fast.',True),
   ('Power Bank','The battery does not drain too fast.',False),
   ('Tablet','The tab lags. But okay for the price.',True),
   ('Tablet','The tab does not lag and works well.',False),
   ('CCTV Camera','Resolution:medyo malabo compared sa ibang camera na gamit ko.',True),
   ('CCTV Camera','Clear image, unlike some other low-grade cameras.',False),
   ('Guitar','Great sound but very poorly made.',True),
   ('Curtain','Material is very thin. It is see thru.',True),
   ('Cordless Screwdriver','Sturdy but the magnetic part is weak.',True),
   ('Cordless Screwdriver','Matibay pero mahina ang kapit ng magnet.',True),
   ('Cordless Screwdriver','The magnetic part is not weak.',False),
   ('Portable Car Washer Pressure Washer','hindi rin malakas yung lumalabas na tubig',True),
   ('Phone Charger','The other charger is low-grade; this one is sturdy.',False),
   ('USB Ceiling Fan','Works on a power bank, but barely moves air.',True),
  ]
  for title,text,expected in cases:
   with self.subTest(text=text):self.check(title,text,'quality',expected)
 def test_curly_quote_evidence_is_original_text(self):
  text='Material is very thin. It\u2019s see thru \u2639\ufe0f\u2639\ufe0f\u2639\ufe0f'
  a=self.check('Kitchen Curtain',text,'quality',True)
  self.assertTrue(all(s['review_start'] is not None for s in a['review_evidence']['quality']['spans']))
if __name__=='__main__':unittest.main()
