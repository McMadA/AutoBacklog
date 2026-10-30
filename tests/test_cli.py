import os
import subprocess
import sys
import tempfile
import unittest

class TestCLI(unittest.TestCase):
    def test_cli_version(self):
        res = subprocess.run(
            [sys.executable, "-m", "autobacklog", "--version"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        self.assertEqual(res.returncode, 0)
        self.assertIn("autobacklog 0.1.0", res.stdout)

    def test_cli_init_and_dryrun(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            # Test init
            res = subprocess.run(
                [sys.executable, "-m", "autobacklog", "init", "--type", "markdown"],
                cwd=tmpdir,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
            )
            self.assertEqual(res.returncode, 0)
            config_file = os.path.join(tmpdir, "autobacklog.yaml")
            self.assertTrue(os.path.exists(config_file))

            # Create a mock markdown backlog
            docs_dir = os.path.join(tmpdir, "docs")
            os.makedirs(docs_dir, exist_ok=True)
            plan_file = os.path.join(docs_dir, "PLAN.md")
            with open(plan_file, "w", encoding="utf-8") as f:
                f.write("# Plan\n- [ ] First Test Task (#101)\n")

            # Test dry-run
            res_dry = subprocess.run(
                [sys.executable, "-m", "autobacklog", "dry-run"],
                cwd=tmpdir,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
            )
            self.assertEqual(res_dry.returncode, 0)
            self.assertIn("First Test Task", res_dry.stdout)

if __name__ == "__main__":
    unittest.main()
