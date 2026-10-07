"""Unit tests for conditional grace-period worker transitions."""
import os
import tempfile
import unittest
from datetime import datetime, timedelta
from pathlib import Path
from unittest import mock

from src.smart_power.actions.base import ActionResult
from src.smart_power.core import storage
from src.smart_power.core.models import ActiveSchedule, PowerActionType, ScheduleMode, ScheduleStatus
from src.smart_power import worker as worker_module


class FakeAction:
    is_destructive = True

    def __init__(self, results):
        self.results = list(results)
        self.calls = []

    def execute(self, force=False, dry_run=False):
        self.calls.append(force)
        if len(self.results) > 1:
            return self.results.pop(0)
        return self.results[0]


class WorkerFlowTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.NamedTemporaryFile(delete=False)
        tmp.close()
        self.state = Path(tmp.name)
        self._patch_state = mock.patch.object(storage, "default_state_path", return_value=self.state)
        self._patch_state.start()
        self._patch_env = mock.patch.dict(os.environ, {"SMART_POWER_DRY_RUN": ""})
        self._patch_env.start()

    def tearDown(self):
        self._patch_state.stop()
        self._patch_env.stop()
        try:
            os.remove(self.state)
        except OSError:
            pass

    def _write(self, **kwargs):
        now = datetime.now()
        schedule = ActiveSchedule(
            schedule_id="worker-test",
            action=PowerActionType.SHUTDOWN,
            mode=ScheduleMode.RELATIVE,
            target_time_iso=kwargs.get("target_time_iso",
                                       (now - timedelta(seconds=1)).isoformat(timespec="seconds")),
            created_at_iso=now.isoformat(timespec="seconds"),
            status=kwargs.get("status", ScheduleStatus.ARMED),
            grace_period_granted=kwargs.get("grace_period_granted", False),
            worker_pid=os.getpid(),
        )
        storage.save_state(schedule)
        return schedule

    def test_unblocked_action_completes_without_grace(self):
        self._write()
        fake = FakeAction([ActionResult(True, "ok")])
        with mock.patch.object(worker_module.registry, "get", return_value=fake):
            code = worker_module.worker_main(["--schedule-id", "worker-test", "--action",
                                              "shutdown", "--target", datetime.now().isoformat()])
        self.assertEqual(code, 0)
        self.assertEqual(fake.calls, [False])
        self.assertEqual(storage.load_state().status, ScheduleStatus.COMPLETED)

    def test_blocked_action_gets_grace_then_force(self):
        self._write()
        fake = FakeAction([ActionResult(False, "blocked", blocked=True),
                           ActionResult(True, "forced ok")])
        with mock.patch.object(worker_module.registry, "get", return_value=fake), \
                mock.patch.object(worker_module, "GRACE_SECONDS", 2.0):
            code = worker_module.worker_main(["--schedule-id", "worker-test", "--action",
                                              "shutdown", "--target", datetime.now().isoformat()])
        self.assertEqual(code, 0)
        self.assertEqual(fake.calls, [False, True])
        self.assertEqual(storage.load_state().status, ScheduleStatus.COMPLETED)


if __name__ == "__main__":
    unittest.main()
