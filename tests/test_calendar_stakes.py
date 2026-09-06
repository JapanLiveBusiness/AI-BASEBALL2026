import unittest
from virtual_dashboard import calendar_html, bet_amount_label
from virtual_replay import replay_records, load_verified_scores


class CalendarStakesTests(unittest.TestCase):
    def test_labels(self):
        self.assertEqual(bet_amount_label({'bet_amount':200000}), '20万 pt')
        self.assertEqual(bet_amount_label({'bet_units':-40}), '40万 pt')
        self.assertEqual(bet_amount_label({'bet_amount':12500}), '12,500 pt')
        for value in [None, 0, -1, 'NaN', 'Infinity', 'bad']:
            self.assertEqual(bet_amount_label({'bet_amount':value}), '金額要確認')

    def test_edits_reviews_deleted_and_escaping(self):
        records = [dict(id='a', date='2026-09-03', team='中日', opponent='広島',
                        bet_amount=100000, handicap=0, status='final',
                        virtual_edit={'bet_amount':200000}),
                   dict(id='b', date='2026-09-03', team='<script>x</script>',
                        opponent='阪神', bet_amount=400000),
                   dict(id='c', date='2026-09-03', team='削除対象', virtual_deleted=True)]
        result = replay_records(records, load_verified_scores())['results']
        html = calendar_html(result, '2026-09')
        self.assertIn('20万 pt', html)
        self.assertIn('40万 pt', html)
        self.assertIn('-200,000 pt', html)
        self.assertIn('要確認 1', html)
        self.assertNotIn('削除対象', html)
        self.assertNotIn('<script>', html)
        self.assertIn('&lt;script&gt;', html)
        self.assertEqual(html.count('class="vp-bet"'), 2)
