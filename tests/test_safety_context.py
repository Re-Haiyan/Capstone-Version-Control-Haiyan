import sys,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'backend/sentiment-analysis'))
from defaketive_sentiment.registry import load_model

class SafetyContext(unittest.TestCase):
 @classmethod
 def setUpClass(cls):cls.model=load_model()
 def result(self,text,title='USB Ceiling Fan'):
  a=self.model.analyze(text,5,listing={'name':title})
  self.assertEqual(a['label'],a['sentiment']['initial_label'])
  for e in a['review_evidence'].values():
   for s in e['spans']:
    if s['review_start'] is not None:self.assertEqual(text[s['review_start']:s['review_end']],s['text'])
  return a
 def test_lyric_and_real_incidents(self):
  lyric="If I warned you that the fire's gonna burn [Chorus: Singer]"
  self.assertNotIn('safety',self.result(lyric,'Foundation')['review_tags'])
  for incident in ['The charger burned my hand.','The cable sparked.','Umusok ang charger.','Natunaw ang plug.','The plug melted.']:
   with self.subTest(incident=incident):self.assertIn('safety',self.result(lyric+' '+incident,'Phone Charger')['review_tags'])
 def test_treadmill_context(self):
  text="The walkpad is good. A piece of plastic broke off and stuck to the mat, we almost stepped on it. The power switch also became defective and we're unable to turn it off without unplugging."
  a=self.result(text,'Electric Walking Pad Treadmill')
  self.assertTrue({'safety','defect'}<=set(a['review_tags']))
  quotes=[s['text'] for s in a['review_evidence']['safety']['spans']]
  self.assertTrue(any('almost stepped' in q for q in quotes));self.assertTrue(any('without unplugging' in q for q in quotes))
 def test_uncertainty_and_real_melt_are_both_visible(self):
  for text in ['Umiinit po nakakatakot Iwan bka umusok.','I am worried it might smoke.',
   'Works well but I fear smoke. The plug melted.',
   'Maganda pero baka umusok. Natunaw ang plug.',
   'Good airflow pero bka umusok at natunaw ang plug.']:
   with self.subTest(text=text):
    a=self.result(text);quotes=[s['text'] for s in a['review_evidence'].get('safety',{}).get('spans',[])]
    if 'melted' in text or 'natunaw' in text.lower():
     self.assertIn('safety',a['review_tags']);self.assertTrue(any('plug' in q.lower() for q in quotes))
    for q in quotes:
     if 'umusok' in q.lower():self.assertTrue('baka' in q.lower() or 'bka' in q.lower(),quotes)
 def test_expected_heat_context_is_not_lost(self):
  text='Build quality:sturdy but gets hot quickly. It did say that in the manual.'
  a=self.result(text,'Hair Dryer')
  self.assertTrue(all('manual' in q['text'] for q in a['review_evidence'].get('safety',{}).get('spans',[])))
 def test_multilingual_actual_and_normal_controls(self):
  yes=['Great charger but it burned my hand.','Maganda pero umusok ang charger.','Works well pero nag spark ang cable.','During a brownout the plug melted.','Okay pero natunaw ang plug.']
  no=['The charger did not overheat or smoke.','Walang usok o amoy sunog ang charger.','Normal warm air dries hair.','Warm during charging, no overheating.']
  for expected,rows in [(True,yes),(False,no)]:
   for text in rows:
    with self.subTest(text=text):self.assertEqual('safety' in self.result(text,'Phone Charger')['review_tags'],expected)
if __name__=='__main__':unittest.main()
