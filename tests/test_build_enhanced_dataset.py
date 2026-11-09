from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from build_enhanced_dataset import features, language, norm, text_hash


class EnhancedDatasetTest(unittest.TestCase):
    def test_normalization_merges_trivial_variants(self):
        self.assertEqual(norm('  Wrong COLOR dumating!! '), 'wrong color dumating')
        self.assertEqual(text_hash('Wrong color dumating.'), text_hash('wrong  color dumating'))

    def test_language_heuristic(self):
        self.assertEqual(language('hindi gumagana ang item sayang lang'), 'tagalog')
        self.assertEqual(language('the item is very good and works well'), 'english')
        self.assertEqual(language('maganda yung item pero the battery is bad'), 'taglish')
        self.assertEqual(language('xkcdqz'), 'unknown')

    def test_template_flag(self):
        self.assertTrue(features('Sleek and stylish design, Fast charging speed, Great value,')['is_template'])
        self.assertFalse(features('sira agad, ayaw gumana')['is_template'])


if __name__ == '__main__':
    unittest.main()
