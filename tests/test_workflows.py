"""Workflow contracts: offline regression gate before automatic publication."""
from pathlib import Path
import unittest
import yaml

ROOT = Path(__file__).resolve().parents[1]
WORKFLOWS = ROOT / ".github/workflows"
UNIT_COMMAND = "python -m unittest discover -s tests -p 'test_*.py' -v"


class WorkflowTests(unittest.TestCase):
    def load(self, name):
        path = WORKFLOWS / name
        self.assertTrue(path.exists(), name + " is missing")
        # BaseLoader preserves GitHub's YAML 1.2 'on' key as a string.
        return yaml.load(path.read_text(), Loader=yaml.BaseLoader)

    def commands(self, workflow):
        return "\n".join(step.get("run", "") for job in workflow["jobs"].values()
                         for step in job["steps"])

    def test_both_existing_workflows_run_all_unittests(self):
        for name in ("validate.yml", "sync-crypto-rules.yml"):
            with self.subTest(workflow=name):
                commands = self.commands(self.load(name))
                self.assertIn(UNIT_COMMAND, commands)
                if name.startswith("sync"):
                    self.assertLess(commands.index("python scripts/build_crypto_custom.py\n"), commands.index(UNIT_COMMAND))
                    self.assertLess(commands.index(UNIT_COMMAND), commands.index("git commit"))
                    self.assertNotIn("git add .", commands)
                self.assertNotIn("check_providers.py", commands)

    def test_provider_health_is_independent_scheduled_readonly_job(self):
        workflow = self.load("provider-health.yml")
        self.assertEqual(set(workflow["on"]), {"schedule", "workflow_dispatch"})
        self.assertEqual(workflow["permissions"], {"contents": "read"})
        commands = self.commands(workflow)
        self.assertIn("python scripts/check_providers.py", commands)
        self.assertNotIn("git push", commands)
        for job in workflow["jobs"].values():
            self.assertIn("timeout-minutes", job)
            for step in job["steps"]:
                self.assertNotEqual(step.get("continue-on-error"), "true")
