import os
import tempfile
import unittest
from autobacklog.config import AutoBacklogConfig
from autobacklog.adapters import get_backlog_adapter, MarkdownPlanAdapter

class TestAdapters(unittest.TestCase):
    def test_markdown_plan_adapter(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            plan_file = os.path.join(tmpdir, "PLAN.md")
            with open(plan_file, "w", encoding="utf-8") as f:
                f.write("""# Development Plan
### #101 Setup Database
- [ ] Connect SQLite (#102)
- [x] Initial Schema (#103)
""")

            cfg = AutoBacklogConfig(workspace_dir=tmpdir)
            cfg.backlog.type = "markdown"
            cfg.backlog.file_path = "PLAN.md"

            adapter = get_backlog_adapter(cfg)
            self.assertEqual(adapter.name, "Local Markdown Plan")

            items = adapter.fetch_items()
            ids = [it["id"] for it in items]
            self.assertIn(101, ids)
            self.assertIn(102, ids)
            self.assertNotIn(103, ids) # Done items excluded

            # Test marking an item done
            adapter.set_state(102, "Closed")
            with open(plan_file, "r", encoding="utf-8") as f:
                updated_content = f.read()
            self.assertIn("- [x] Connect SQLite (#102)", updated_content)

if __name__ == "__main__":
    unittest.main()
