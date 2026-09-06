import unittest
from virtual_dashboard import handicap_side_badge, calendar_html


class HandicapBadgeTests(unittest.TestCase):
    def test_sign_and_original_notation(self):
        for token in ['0.8', '+0.3', '1半', '1半5', '１．５']:
            self.assertIn('>🉇</span>', handicap_side_badge({'handicap_raw': token}))
        for token in ['-0.2', '-1半5', '－０．８']:
            self.assertIn('>🉈</span>', handicap_side_badge({'handicap_raw': token}))

    def test_zero_and_unknown(self):
        for token in ['0', '-0.0', '+0', 0]:
            self.assertIn('ハンデなし', handicap_side_badge({'handicap_raw': token}))
        for token in [None, '', 'NaN', 'bad', '<script>']:
            result = handicap_side_badge({'handicap_raw': token, 'stored_handicap': 1})
            self.assertIn('>?</span>', result)
            self.assertNotIn('<script>', result)

    def test_placement_and_no_mutation(self):
        row = dict(date='2026-09-05', team='巨人', bet_amount=100000,
                   handicap_raw='-0.2', status='calculated', points_delta=18000)
        before = dict(row)
        html = calendar_html([row], '2026-09')
        self.assertIn('10万</span> <span class="vp-handicap-side"', html)
        self.assertIn('>🉈</span>', html)
        self.assertIn('+18,000', html)
        self.assertEqual(before, row)
