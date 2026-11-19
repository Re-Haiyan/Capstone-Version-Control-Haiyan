"""Pair fan interpretation repros with literal complaints and independent hazards."""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'backend'), str(ROOT / 'backend/sentiment-analysis')]
from defaketive_sentiment.registry import load_model

FAN = 'Vone USB Ceiling Fan 6 blade ceiling fan USB Cable Fan Household Hanging Fan Foldable Portable Fan'


class FanRemainingEvidence(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.model = load_model()

    def result(self, text, title=FAN):
        return self.model.analyze(text, 5, listing={'name': title})

    def flags(self, text, title=FAN):
        a = self.result(text, title)
        return set(a.get('review_tags') or []) | set(a.get('review_extra_tags') or [])

    def test_ordinary_wattage_not_disputed_rating(self):
        for text in ('The power consumption is minimal, only 5 watts, so it is energy efficient too.',
                     'Thanks seller gusto ko tlga itong USB fan KC tipid s kuryente 5watts lang eh pwde sa power bank.',
                     'Maganda po,matibay,pero since 5w lang siya,dont expect po na malakas,',
                     'It is only 5 W.', 'Limang watt lang ang konsumo nito.',
                     'It is rated 5W and consumes only 5 watts.'):
            with self.subTest(text=text):
                self.assertNotIn('not_as_described', self.flags(text))

    def test_disputed_rating_and_brand_remain(self):
        for text in ('Advertised as 25 watts but only 5 watts arrived.',
                     'Nakalagay 25W pero 5w lang ang dumating.',
                     'The listing says 25W, pero 5 watts lang ito.',
                     'It is rated 25W but only 5 watts arrived.',
                     'I ordered 25W but only 5 watts arrived.',
                     'Only 5 watts. I received the wrong item.',
                     'Mas mahal sa ibang same product pero ibang brand ang pinadala.'):
            with self.subTest(text=text):
                self.assertIn('not_as_described', self.flags(text))

    def test_local_outage_is_not_device_failure(self):
        for text in ('Gabit na gabit lalu na dito sa lugarnmin laging walang power.',
                     'Gamit na gamit dito sa lugar namin laging walang power.',
                     'The neighborhood has no power, but the fan runs on a power bank.',
                     'Brownout sa amin but gumagana sa powerbank.'):
            with self.subTest(text=text):
                self.assertNotIn('defect', self.flags(text))

    def test_outage_does_not_hide_hazard_or_failure(self):
        for text, flag in (
            ('Dito sa lugar namin laging walang power pero natunaw ang plug ng fan.', 'safety'),
            ('During the power outage, the plug melted while the fan ran on a power bank.', 'safety'),
            ('Brownout sa amin but umusok ang motor habang gumagana.', 'safety'),
            ('Dito sa lugar namin laging walang power pero sira ang motor ng fan.', 'defect'),
            ('Walang power ang fan kahit maayos ang outlet.', 'defect'),
        ):
            with self.subTest(text=text):
                self.assertIn(flag, self.flags(text))

    def test_quiet_operation_is_not_audio_failure(self):
        for text in ('Quiet:it almost no sound .bot disturbing. Quality:it is good .',
                     'Quiet:the fan makes no sound.', 'Tahimik ang fan at gumagana naman.',
                     'Quiet:almost no sound pero umiikot naman.'):
            with self.subTest(text=text):
                self.assertNotIn('defect', self.flags(text))
        self.assertIn('defect', self.flags('The speaker has no sound.', 'Bluetooth speaker'))
        self.assertIn('defect', self.flags('Quiet:almost no sound but the motor is broken.'))

    def test_low_consumption_not_airflow(self):
        for text in ('Quality:10 Performance:10 Ang Ganda nya mahina din sya Kumain Ng charge thanks po order Po Ako ulit',
                     'Mahina lang ang consume ng kuryente.',
                     'Mahina ang konsumo ng kuryente.',
                     'It consumes very little electricity.',
                     'Low consumption, okay ang fan.'):
            with self.subTest(text=text):
                self.assertNotIn('quality', self.flags(text))
        for text in ('Mahina lang ang consume ng kuryente pero mahina rin ang hangin.',
                     'Mahina kumain ng charge but the airflow is weak.',
                     'Works on a power bank but barely moves air.',
                     'Gumagana sa powerbank pero halos walang hangin.',
                     'It uses little electricity but the wind is very weak.'):
            with self.subTest(text=text):
                self.assertIn('quality', self.flags(text))

    def test_price_comparison_and_retracted_expectation(self):
        for text in ('Very like ko xa mas mahal sia sa ibang same product online peri keri labg kasi sulit and worth it naman.',
                     'Quality:maganda kala ko mahina lang malakas Pala.',
                     'I thought it would be weak but the airflow is strong.',
                     'Mas mahal than other products but worth it.'):
            with self.subTest(text=text):
                self.assertFalse(self.flags(text))
        for text in ('Kala ko malakas pero mahina pala ang hangin.',
                     'Mahina ang hangin kumpara sa clip fan.',
                     'I thought it was strong but the airflow is weak.'):
            with self.subTest(text=text):
                self.assertIn('quality', self.flags(text))

    def test_uncertain_fault_abstains_but_airflow_evidence_remains(self):
        text = 'Performance:3/10 Not sure if it defective, its working but the fan air is weak and no air is blowing out'
        self.assertNotIn('defect', self.flags(text))
        self.assertIn('quality', self.flags(text))
        for text in ('The motor is defective.', 'Sira ang motor.', 'Defective ang fan but okay ang powerbank.'):
            self.assertIn('defect', self.flags(text))

    def test_ambiguous_order_typo_is_not_asserted_shortage(self):
        self.assertNotIn('not_as_described', self.flags('mabilis din talaga kahapon kulang na order received na agad'))
        for text in ('Kulang na order ang natanggap ko.', 'Dalawa ang order ko pero isa lang dumating.',
                     'Only one arrived although I ordered two.'):
            with self.subTest(text=text):
                self.assertIn('not_as_described', self.flags(text))

    def test_no_airflow_literal_evidence(self):
        a = self.result('Parang pang bugaw lang ng langaw. Walang hangin')
        self.assertTrue(any('Walang hangin' in s['text'] for s in a['review_evidence']['quality']['spans']))
        self.assertFalse(a['sentiment']['category_context']['sentiment_overridden'])

    def test_interpretation_scopes_one_span_and_category(self):
        from defaketive_sentiment.concern_context import phrase_reason
        text = 'mahina lang ang consume ng kuryente pero mahina ang hangin'
        first, second = text.index('mahina'), text.rindex('mahina')
        self.assertIsNotNone(phrase_reason('small_appliance', 'quality', text, (first, first + 6)))
        self.assertIsNone(phrase_reason('small_appliance', 'quality', text, (second, second + 6)))
        for category in ('speaker', 'powerbank', 'phone', 'other', None):
            self.assertIsNone(phrase_reason(category, 'quality', text, (first, first + 6)))


if __name__ == '__main__':
    unittest.main()
