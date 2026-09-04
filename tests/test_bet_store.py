import json
from pathlib import Path
import tempfile
import unittest

from bet_store import DuplicateBetError, append_bet, delete_bet, load_bets, update_bet


class BetStoreTest(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.path = Path(self.temp_dir.name) / "bet_records.json"

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_append_update_and_delete_round_trip(self):
        append_bet(self.path, {"id": "bet-1", "team": "阪神", "status": "pending"})
        updated = update_bet(self.path, "bet-1", {"status": "final", "result": "win"})

        self.assertEqual(updated["status"], "final")
        self.assertEqual(load_bets(self.path)[0]["result"], "win")

        deleted = delete_bet(self.path, "bet-1")
        self.assertEqual(deleted["team"], "阪神")
        self.assertEqual(load_bets(self.path), [])

    def test_duplicate_id_is_rejected_without_overwriting_data(self):
        append_bet(self.path, {"id": "bet-1", "team": "阪神"})
        with self.assertRaises(DuplicateBetError):
            append_bet(self.path, {"id": "bet-1", "team": "巨人"})
        self.assertEqual(load_bets(self.path)[0]["team"], "阪神")

    def test_legacy_records_receive_stable_ids_and_persist_on_update(self):
        self.path.write_text(
            json.dumps([{"date": "2026-08-20", "team": "阪神", "status": "pending"}], ensure_ascii=False),
            encoding="utf-8",
        )
        first_id = load_bets(self.path)[0]["id"]
        self.assertTrue(first_id.startswith("legacy-"))
        self.assertEqual(load_bets(self.path)[0]["id"], first_id)

        update_bet(self.path, first_id, {"status": "final"})
        raw = json.loads(self.path.read_text(encoding="utf-8"))
        self.assertEqual(raw[0]["id"], first_id)
        self.assertEqual(raw[0]["status"], "final")

    def test_saved_file_is_valid_json_after_every_mutation(self):
        append_bet(self.path, {"id": "bet-1", "team": "阪神"})
        json.loads(self.path.read_text(encoding="utf-8"))
        update_bet(self.path, "bet-1", {"memo": "更新"})
        json.loads(self.path.read_text(encoding="utf-8"))
        delete_bet(self.path, "bet-1")
        self.assertEqual(json.loads(self.path.read_text(encoding="utf-8")), [])


if __name__ == "__main__":
    unittest.main()
