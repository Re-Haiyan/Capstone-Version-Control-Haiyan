"""Literal operation/consumption wording, without suppressing real fan complaints."""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'backend'), str(ROOT / 'backend/sentiment-analysis')]
from defaketive_sentiment.registry import load_model

FAN = 'Vone USB Ceiling Fan 6 blade ceiling fan USB Cable Fan Household Hanging Fan Foldable Portable Fan'


class FanConcernPrecision(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.model = load_model()

    def analyze(self, text, stars=5):
        return self.model.analyze(text, stars, listing={'name': FAN})

    def flags(self, text, stars=5):
        r = self.analyze(text, stars)
        return set(r.get('review_tags') or []) | set(r.get('review_extra_tags') or [])

    def test_exact_successful_operation_clauses(self):
        for text in ('Gumagana naman magdamag ko ginamit sa powerbank.',
                     'kasi powerbank lng gagana na', 'gumagana nga s powerbank'):
            for stars in (1, 3, 5):
                with self.subTest(text=text, stars=stars):
                    self.assertNotIn('defect', self.flags(text, stars))

    def test_exact_quiet_airflow_praise(self):
        text = 'Performance:good. Best Feature:very nice product. Product Quality:very good nice quality. Malakas yung hangin at hindi maingay. Order ako ulit.'
        self.assertNotIn('quality', self.flags(text, 4))

    def test_consumption_is_not_airflow(self):
        for text in ('Tahimik lang at di sya malakas sa kuryente kaya maganda talaga sya gamitin.',
                     'Hindi cya malakas Kumain Ng kuryente',
                     'Hindi siya malakas sa konsumo ng kuryente.',
                     'It does not consume much electricity.'):
            with self.subTest(text=text):
                self.assertNotIn('quality', self.flags(text))

    def test_multilingual_success_and_denied_noise(self):
        for text in ('Works on a power bank.', 'Runs normally on a powerbank.',
                     'Gumagana sa powerbank.', 'Okay. Works on a powerbank, tahimik naman.',
                     'Strong airflow and not noisy.', 'Malakas ang hangin at hindi maingay.'):
            with self.subTest(text=text):
                self.assertFalse(self.flags(text), text)

    def test_actual_airflow_complaints_survive_mixed_operation(self):
        for text in ('Works on a power bank, but the airflow is weak.',
                     'Works on a power bank and the airflow is weak.',
                     'Gumagana sa powerbank pero mahina ang hangin.',
                     'Okay sa powerbank but weak ang airflow.',
                     'Hindi maingay pero mahina ang hangin.',
                     'Di sya malakas sa kuryente pero mahina ang hangin.',
                     'Di sya malakas ang hangin kahit may kuryente.',
                     'Parang pang bugaw lang ng langaw. Walang hangin'):
            with self.subTest(text=text):
                for stars in (1, 5):
                    self.assertIn('quality', self.flags(text, stars))

    def test_actual_faults_survive_mixed_operation(self):
        for text in ('Works on a power bank, but it stopped working.',
                     'Gumagana sa powerbank pero namamatay bigla.',
                     'Works sa powerbank but the motor is broken.',
                     'The fan does not work on a power bank.',
                     'Hindi gumagana sa powerbank.',
                     'Works on a power bank but keeps cutting out.'):
            with self.subTest(text=text):
                for stars in (1, 5):
                    self.assertIn('defect', self.flags(text, stars))

    def test_operation_gate_abstains_outside_scope_or_with_extra_complaints(self):
        from defaketive_sentiment.concern_context import operation_reason
        for category in ('phone', 'powerbank', 'other', None):
            self.assertIsNone(operation_reason(category, 'defect', 'gumagana nga s powerbank'))
        for text in ('Only works on a power bank', 'Hindi gumagana sa powerbank',
                     'Works on a power bank and stops intermittently',
                     'Malakas yung hangin at hindi maingay but the plastic is flimsy'):
            for flag in ('defect', 'quality'):
                self.assertIsNone(operation_reason('small_appliance', flag, text))

    def test_interpretations_quote_source_and_export_without_changing_sentiment(self):
        import json
        import dashboard_utils as du
        text = 'gumagana nga s powerbank'
        result = self.analyze(text)
        self.assertTrue(result['concern_interpretations'])
        self.assertFalse(result['sentiment']['category_context']['sentiment_overridden'])
        for observation in result['concern_interpretations']:
            self.assertIn(observation['text'], text)
        product = {'name': FAN, 'comments': [{'content': text, 'sentiment_analysis': result}]}
        row = du.review_rows([product])[0]
        self.assertEqual(json.loads(row['Concern interpretations']), result['concern_interpretations'])

    def test_all_other_concerns_and_melting_remain_independent(self):
        for text, flag in (
            ('Works on a power bank, but the plug sparked.', 'safety'),
            ('Gumagana nang maayos pero sobrang init at natunaw ang plug.', 'safety'),
            ('Works on a power bank, but it is fake, not original.', 'counterfeit'),
            ('Works on a power bank, but I received the wrong item.', 'not_as_described'),
        ):
            with self.subTest(text=text):
                self.assertIn(flag, self.flags(text, 1))


if __name__ == '__main__':
    unittest.main()
