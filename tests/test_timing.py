"""Unit tests for timing helpers."""
import unittest
from datetime import datetime, timedelta

from src.smart_power.core import timing


class TimingTests(unittest.TestCase):
    def test_relative_minutes(self):
        ok, _, seconds = timing.parse_relative_duration("25")
        self.assertTrue(ok)
        self.assertEqual(seconds, 1500)

    def test_relative_hours(self):
        ok, _, seconds = timing.parse_relative_duration("2h")
        self.assertTrue(ok)
        self.assertEqual(seconds, 7200)

    def test_relative_rejects_zero(self):
        ok, _, _ = timing.parse_relative_duration("0")
        self.assertFalse(ok)

    def test_exact_future_today(self):
        now = datetime(2026, 10, 3, 10, 0, 0)
        ok, extra, target = timing.parse_exact_time("15:30", now)
        self.assertTrue(ok)
        self.assertEqual((target.hour, target.minute, target.day), (15, 30, 3))
        self.assertEqual(extra, "")

    def test_exact_past_rolls_to_tomorrow(self):
        now = datetime(2026, 10, 3, 16, 0, 0)
        ok, extra, target = timing.parse_exact_time("14:00", now)
        self.assertTrue(ok)
        self.assertEqual(extra, "Tomorrow")
        self.assertEqual(target.day, 4)

    def test_overdue_detection(self):
        target = datetime.now() - timedelta(seconds=60)
        self.assertTrue(timing.is_overdue(target))
        self.assertFalse(timing.is_overdue(datetime.now() + timedelta(minutes=5)))

    def test_countdown_format(self):
        self.assertEqual(timing.format_countdown(3661), "01:01:01")


if __name__ == "__main__":
    unittest.main()
