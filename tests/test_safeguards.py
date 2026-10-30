import os
import tempfile
import time
import unittest
from autobacklog.safeguards.quota_cache import (
    load_quota_cache,
    save_quota_cache,
    record_quota_exhaustion,
    is_model_exhausted,
    clear_quota_cache,
)
from autobacklog.safeguards.snapshot import create_preflight_snapshot

class TestSafeguards(unittest.TestCase):
    def test_quota_cache_roundtrip(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            cache_file = os.path.join(tmpdir, "model_quota_cache.json")
            
            # Record exhaustion for 3600 seconds
            record_quota_exhaustion(cache_file, "gemini-4-test", 3600)
            
            exhausted, rem_str = is_model_exhausted(cache_file, "gemini-4-test")
            self.assertTrue(exhausted)
            self.assertIn("1h", rem_str)

            # Check non-exhausted model
            exhausted_other, _ = is_model_exhausted(cache_file, "gemini-flash")
            self.assertFalse(exhausted_other)

            clear_quota_cache(cache_file)
            self.assertFalse(os.path.exists(cache_file))

    def test_preflight_snapshot(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = os.path.join(tmpdir, "code.py")
            with open(test_file, "w") as f:
                f.write("print('hello')\n")
            
            _, zip_path, _ = create_preflight_snapshot(tmpdir, "_snapshots", "test-tag")
            self.assertIsNotNone(zip_path)
            self.assertTrue(os.path.exists(zip_path))

if __name__ == "__main__":
    unittest.main()
