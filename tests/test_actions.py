"""Unit tests for action commands and dry-run behavior."""
import unittest

from src.smart_power.actions import registry
from src.smart_power.actions.windows_ops import abort_command, restart_command, shutdown_command


class ActionTests(unittest.TestCase):
    def test_registry_has_four_actions(self):
        self.assertEqual(len(registry.all_actions()), 4)

    def test_shutdown_commands(self):
        self.assertNotIn("/f", shutdown_command(False))
        self.assertIn("/f", shutdown_command(True))
        self.assertIn("/f", restart_command(True))

    def test_abort_command(self):
        self.assertEqual(abort_command()[-1], "/a")

    def test_dry_run_executes_safely(self):
        for action in registry.all_actions():
            result = action.execute(dry_run=True)
            self.assertTrue(result.success)

    def test_destructive_flags(self):
        self.assertTrue(registry.get("shutdown").is_destructive)
        self.assertFalse(registry.get("lock").is_destructive)


if __name__ == "__main__":
    unittest.main()
