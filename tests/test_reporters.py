import io
import os
import tempfile
import unittest
from autobacklog.reporters import SmartConsoleStreamer, RunProgressReporter

class TestReporters(unittest.TestCase):
    def test_smart_console_streamer_dedup(self):
        buf = io.StringIO()
        streamer = SmartConsoleStreamer(log_file=buf)
        
        # Test quota line beautification
        raw_quota = 'A G Y _ E R R O R: {"short_error": "RESOURCE_EXHAUSTED (code 429): Individual quota reached. Resets in 150h38m35s."}'
        streamer.process_line(raw_quota)
        self.assertIn("QUOTA EXHAUSTED", streamer.last_clean_line)

        # Test deduplication logic
        streamer.process_line("Waiting for task-1 to complete.")
        streamer.process_line("Waiting for task-1 to complete.")
        self.assertEqual(streamer.repeat_count, 1)

    def test_run_progress_reporter(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            reporter = RunProgressReporter(tmpdir, "RUN_SUMMARY.md")
            self.assertEqual(len(reporter.completed_tasks), 0)

            # Record active task
            reporter.set_current_task({"id": 101, "title": "Setup CI"}, "gemini-4", "LARGE")
            self.assertIsNotNone(reporter.current_task)

            # Verify file was written
            sum_path = os.path.join(tmpdir, "RUN_SUMMARY.md")
            self.assertTrue(os.path.exists(sum_path))

            # Record completed
            reporter.record_completed({"id": 101, "title": "Setup CI"}, 12.5, "gemini-4", "abc1234")
            self.assertEqual(len(reporter.completed_tasks), 1)

            with open(sum_path, "r", encoding="utf-8") as f:
                content = f.read()
            self.assertIn("#101", content)
            self.assertIn("Setup CI", content)
            self.assertIn("abc1234", content)

if __name__ == "__main__":
    unittest.main()
