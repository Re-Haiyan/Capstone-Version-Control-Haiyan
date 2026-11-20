"""Attribution pairs use the real production model, preserving its initial output."""
import sys,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'backend'),str(ROOT/'backend/sentiment-analysis'),str(ROOT/'tests')]
from defaketive_sentiment.registry import load_model
from defaketive_sentiment import category_context
from test_product_category import TITLES,PC3_TITLES
CUBE='Magnetic Cube Puzzle Toy';FAN='USB Ceiling Fan';CHARGER='USB Phone Charger';AUDIO='Bluetooth Soundbar'
CASES=[
(CUBE,'This cube feels sturdy, unlike some low-quality toys.','quality',False),
(CUBE,'Unlike my old cube, this one feels flimsy.','quality',True),
(CUBE,'Matibay ito, hindi tulad ng ibang low quality toys.','quality',False),
(CUBE,'Sturdy ito but this cube feels flimsy when turned.','quality',True),
(CUBE,'Sturdy, unlike some low-quality toys, but this one is defective.','defect',True),
(CHARGER,'My old charger overheated. This replacement stays cool.','safety',False),
(CHARGER,'My old charger overheated. This replacement also overheats.','safety',True),
(CHARGER,'Luma kong charger overheated. Itong bago stays cool.','safety',False),
(CHARGER,'Dati kong charger overheated. Itong bago umusok.','safety',True),
(CHARGER,'My old charger overheated.','safety',True),
(CHARGER,'Luma kong charger natunaw ang plug. Itong bago stays cool.','safety',False),
(CHARGER,'Hindi natunaw ang plug ng replacement.','safety',False),
(CHARGER,'This replacement overheated, unlike my old charger.','safety',True),
(CHARGER,'My old charger overheated but this replacement sparked.','safety',True),
(CUBE,'Akala ko fake, pero verified ang serial.','counterfeit',False),
(CUBE,'I thought it was fake, but the serial was verified.','counterfeit',False),
(CUBE,'Akala ko peke, pero na-verify ko ang serial.','counterfeit',False),
(CUBE,'Akala ko fake, pero hindi verified ang serial. Fake talaga.','counterfeit',True),
(CUBE,'Fake ang cube, invalid ang serial.','counterfeit',True),
(CUBE,'Verified ang serial pero fake ang logo.','counterfeit',True),
(CUBE,'The cube turns smoothly, but the magnets fell out.','defect',True),
(CUBE,'Smooth ang ikot pero natanggal ang mga magnet.','defect',True),
(CUBE,'Maayos ang ikot, pero nahulog ang magnet.','defect',True),
(CUBE,'The cube turns smoothly; the magnets did not fall out.','defect',False),
(FAN,'Stable ang kuryente pero biglang namamatay ang fan kahit nakasaksak.','defect',True),
(FAN,'Strong airflow but the fan keeps shutting off while plugged in.','defect',True),
(FAN,'Maayos ang hangin pero namamatay ang fan kahit nakasaksak.','defect',True),
(FAN,'Brownout sa amin but gumagana sa powerbank.','defect',False),
(FAN,'During the power outage, the plug melted while the fan ran on a power bank.','safety',True),
(AUDIO,'The soundbar powers on but has no audio.','defect',True),
(AUDIO,'May ilaw pero walang tunog ang soundbar.','defect',True),
(AUDIO,'The speaker powers on pero speaker walang audio.','defect',True),
(FAN,'Quiet:the fan makes no sound.','defect',False),
(AUDIO,'The soundbar has no audio problems.','defect',False),
(FAN,'Sabi sa listing may cable, pero wala sa box.','not_as_described',True),
(FAN,'The listing includes a cable, but missing from the box.','not_as_described',True),
(FAN,'Listing says may cable, pero wala sa box.','not_as_described',True),
(FAN,'Sabi sa listing may cable at may cable sa box.','not_as_described',False),
]
class Attribution(unittest.TestCase):
 @classmethod
 def setUpClass(cls):cls.model=load_model()
 def result(self,title,text):return self.model.analyze(text,5,listing={'name':title})
 def test_multilingual_pairs(self):
  for title,text,flag,present in CASES:
   with self.subTest(text=text):
    a=self.result(title,text);flags=set(a.get('review_tags',[])+a.get('review_extra_tags',[]));self.assertEqual(flag in flags,present,a)
    self.assertFalse(a['sentiment']['category_context']['sentiment_overridden'])
    if present:
     self.assertTrue(a['review_evidence'][flag]['spans'],a)
     for s in a['review_evidence'][flag]['spans']:self.assertEqual(text[s['review_start']:s['review_end']],s['text'])
 def test_current_unit_evidence_only(self):
  a=self.result(CHARGER,'My old charger overheated. This replacement also overheats.')
  self.assertEqual([s['text'] for s in a['review_evidence']['safety']['spans']],['overheats.'])
 def test_missing_component_full_quote(self):
  text='Sabi sa listing may cable, pero wala sa box.';a=self.result(FAN,text)
  self.assertTrue(any('cable' in s['text'] and 'wala sa box' in s['text'] for s in a['review_evidence']['not_as_described']['spans']))
 def test_49_category_matrix_attribution_and_mixed_complaint(self):
  titles={v:k for k,v in {**TITLES,**PC3_TITLES}.items()};self.assertEqual(len(category_context._profiles()['profiles']),49)
  for kind in category_context._profiles()['profiles']:
   with self.subTest(category=kind):
    a=self.result(titles[kind],'This item feels sturdy, unlike some low-quality toys.')
    self.assertNotIn('quality',a['review_extra_tags'])
    a=self.result(titles[kind],'Unlike my old item, this one feels flimsy.')
    self.assertIn('quality',a['review_extra_tags'])
 def test_cross_clause_hazard_never_hidden(self):
  for t in ['Sturdy, unlike some low-quality toys. The cable sparked.',
            'Akala ko fake, pero verified ang serial. Natunaw ang plug.',
            'This replacement stays cool but the cable sparked.',
            'My old charger overheated. This replacement melted its plug.']:
   with self.subTest(text=t):self.assertIn('safety',self.result(CHARGER,t)['review_tags'])
if __name__=='__main__':unittest.main()
