import unittest
from autobacklog.providers import get_ai_provider, AntigravityProvider, ClaudeProvider

class TestProviders(unittest.TestCase):
    def test_provider_factory(self):
        agy = get_ai_provider("agy")
        self.assertIsInstance(agy, AntigravityProvider)

        claude = get_ai_provider("claude")
        self.assertIsInstance(claude, ClaudeProvider)

    def test_quota_parsing_agy(self):
        agy = AntigravityProvider()
        err_msg = 'A G Y _ E R R O R: {"short_error": "RESOURCE_EXHAUSTED: Individual quota reached. Resets in 150h38m35s."}'
        seconds = agy.parse_quota_error(err_msg)
        self.assertIsNotNone(seconds)
        self.assertEqual(seconds, 150 * 3600 + 38 * 60 + 35)

    def test_quota_parsing_claude(self):
        claude = ClaudeProvider()
        err_msg = "Error 429: You have hit your message limit. Resets in 4 hours 15 minutes."
        seconds = claude.parse_quota_error(err_msg)
        self.assertIsNotNone(seconds)
        self.assertEqual(seconds, 4 * 3600 + 15 * 60)

if __name__ == "__main__":
    unittest.main()
