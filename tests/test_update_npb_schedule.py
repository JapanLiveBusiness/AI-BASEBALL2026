import unittest
from datetime import date
from unittest.mock import Mock, patch

from scripts import update_npb_schedule as schedule


class ScheduleFetchTests(unittest.TestCase):
    def test_stops_after_current_month_contains_next_slate(self):
        games = [{"home": "阪神", "away": "巨人", "time": "18:00"}]
        with patch.object(schedule, "fetch_month", return_value=("official", "html")) as fetch:
            with patch.object(schedule, "rows_from_html", return_value={"2026-10-25": games}):
                result = schedule.build_payload(date(2026, 10, 24))
        self.assertEqual(result["date"], "2026-10-25")
        self.assertEqual(result["count"], 1)
        fetch.assert_called_once_with(2026, 10)

    def test_tries_next_month_after_network_failure(self):
        with patch.object(schedule, "fetch_month", side_effect=[
            schedule.requests.ConnectTimeout("timeout"), ("official", "html")
        ]) as fetch:
            with patch.object(schedule, "rows_from_html", return_value={"2026-11-01": [{"home": "阪神"}]}):
                result = schedule.build_payload(date(2026, 10, 24))
        self.assertEqual(result["date"], "2026-11-01")
        self.assertEqual(fetch.call_count, 2)

    def test_all_failed_requests_still_fail_instead_of_publishing_stale_data(self):
        with patch.object(schedule, "fetch_month", side_effect=schedule.requests.ConnectTimeout("timeout")):
            with self.assertRaisesRegex(RuntimeError, "2026-10:.*2026-11:"):
                schedule.build_payload(date(2026, 10, 24))

    def test_fetch_configures_bounded_retry_and_separate_timeouts(self):
        session = Mock()
        session.get.return_value.text = "official html"
        session.get.return_value.apparent_encoding = "utf-8"
        with patch.object(schedule.requests, "Session") as factory:
            factory.return_value.__enter__.return_value = session
            url, html = schedule.fetch_month(2026, 10)
        retry = session.mount.call_args.args[1].max_retries
        self.assertEqual(retry.total, 2)
        self.assertEqual(retry.allowed_methods, frozenset({"GET"}))
        self.assertIn(503, retry.status_forcelist)
        self.assertEqual(session.get.call_args.kwargs["timeout"], (10, 25))
        self.assertEqual(html, "official html")
        self.assertIn("schedule_10_detail.html", url)


if __name__ == "__main__":
    unittest.main()
