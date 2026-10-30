import os
import unittest
from autobacklog.config import load_config, generate_template_config

class TestConfig(unittest.TestCase):
    def test_default_config(self):
        cfg = load_config()
        self.assertIsNotNone(cfg.workspace_dir)
        self.assertEqual(cfg.max_rounds, 1000)
        self.assertEqual(cfg.cooldown_seconds, 10)

    def test_template_generation(self):
        azure_tpl = generate_template_config("azure")
        self.assertIn("azure_boards", azure_tpl)

        gh_tpl = generate_template_config("github")
        self.assertIn("github_issues", gh_tpl)

        md_tpl = generate_template_config("markdown")
        self.assertIn("markdown", md_tpl)

if __name__ == "__main__":
    unittest.main()
