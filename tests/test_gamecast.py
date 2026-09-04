import unittest

from gamecast import gamecast_snapshot, occupied_bases, select_featured_game


class GamecastTest(unittest.TestCase):
    def test_featured_game_prefers_live_then_hawks(self):
        games = [
            {"home": "阪神", "away": "巨人", "status": "scheduled"},
            {"home": "ソフトバンク", "away": "西武", "status": "scheduled"},
            {"home": "楽天", "away": "日本ハム", "status": "in_progress"},
        ]
        self.assertEqual(select_featured_game(games)["home"], "楽天")
        self.assertEqual(select_featured_game(games[:2])["home"], "ソフトバンク")

    def test_snapshot_normalizes_live_counts_and_bases(self):
        snapshot = gamecast_snapshot(
            {
                "status": "live",
                "inning": 7,
                "inning_half": "表",
                "balls": 9,
                "strikes": 1,
                "outs": 2,
                "runners": ["first", "3"],
                "current_pitcher": "投手A",
                "current_batter": "打者B",
            }
        )
        self.assertEqual(snapshot["inning_label"], "7回表")
        self.assertEqual(snapshot["balls"], 3)
        self.assertEqual(snapshot["strikes"], 1)
        self.assertEqual(snapshot["bases"], {1, 3})

    def test_missing_live_details_are_not_invented(self):
        snapshot = gamecast_snapshot({"status": "scheduled"})
        self.assertEqual(snapshot["inning_label"], "試合前")
        self.assertEqual(snapshot["pitcher"], "投手情報待ち")
        self.assertEqual(snapshot["lineup"], [])
        self.assertEqual(occupied_bases({}), set())


if __name__ == "__main__":
    unittest.main()
