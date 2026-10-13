"""Unit tests for atomic persistence and stale-process cleanup."""
import os
import tempfile
import unittest
from datetime import datetime, timedelta
from pathlib import Path

from src.smart_power.core import storage
from src.smart_power.core.models import ActiveSchedule, PowerActionType, ScheduleMode, ScheduleStatus


def _sample(pid):
    now = datetime.now()
    return ActiveSchedule(
        schedule_id="test-schedule",
        action=PowerActionType.LOCK,
        mode=ScheduleMode.RELATIVE,
        target_time_iso=(now + timedelta(minutes=5)).isoformat(timespec="seconds"),
        created_at_iso=now.isoformat(timespec="seconds"),
        status=ScheduleStatus.ARMED,
        worker_pid=pid,
    )


class StorageTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.NamedTemporaryFile(delete=False)
        tmp.close()
        self.path = Path(tmp.name)

    def tearDown(self):
        try:
            os.remove(self.path)
        except OSError:
            pass

    def test_round_trip(self):
        storage.save_state(_sample(os.getpid()), self.path)
        loaded = storage.load_state(self.path)
        self.assertIsNotNone(loaded)
        self.assertEqual(loaded.schedule_id, "test-schedule")

    def test_corrupt_file_returns_none(self):
        self.path.write_text("{not-json", encoding="utf-8")
        self.assertIsNone(storage.load_state(self.path))

    def test_stale_pid_is_pruned(self):
        storage.save_state(_sample(999999999), self.path)
        self.assertIsNone(storage.prune_stale_state(self.path))
        self.assertIsNone(storage.load_state(self.path))

    def test_live_pid_is_kept(self):
        storage.save_state(_sample(os.getpid()), self.path)
        self.assertIsNotNone(storage.prune_stale_state(self.path))


if __name__ == "__main__":
    unittest.main()
