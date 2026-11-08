import csv
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from merge_direct_annotations import parse_aspects, read_parts


class DirectAnnotationsTest(unittest.TestCase):
    def test_supported_aspects(self):
        self.assertEqual(parse_aspects('delivery=positive;functionality=negative'),
                         {'delivery': 'positive', 'functionality': 'negative'})
        self.assertEqual(parse_aspects(''), {})

    def test_invalid_and_duplicate_aspects_rejected(self):
        for text in ('delivery=happy', 'delivery=positive;delivery=negative', 'brand=positive'):
            with self.subTest(text=text), self.assertRaises(ValueError):
                parse_aspects(text)

    def test_incomplete_batch_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'part_1.tsv'
            with path.open('w', newline='', encoding='utf-8') as handle:
                writer = csv.writer(handle, delimiter='\t')
                writer.writerow(['id','sentiment','confidence','aspects'])
                writer.writerow(['R00001','positive','high',''])
            with self.assertRaisesRegex(ValueError, 'exactly 1000'):
                read_parts(Path(folder), {'R00001'})


if __name__ == '__main__':
    unittest.main()
