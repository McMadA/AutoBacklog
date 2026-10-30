import json
import threading
import time
import unittest
import urllib.request
from autobacklog.config import AutoBacklogConfig
from autobacklog.ui.server import RunnerState, AutoBacklogHandler, find_free_port, STATIC_DIR
from http.server import ThreadingHTTPServer
import autobacklog.ui.server as ui_server

class TestUIServer(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.config = AutoBacklogConfig(project_name="UnitTestProject")
        ui_server._GLOBAL_STATE = RunnerState(cls.config)
        # Bind to port 0 so the OS assigns a guaranteed free ephemeral port
        cls.httpd = ThreadingHTTPServer(("127.0.0.1", 0), AutoBacklogHandler)
        cls.port = cls.httpd.server_address[1]
        cls.thread = threading.Thread(target=cls.httpd.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.httpd.shutdown()
        cls.httpd.server_close()

    def test_get_index_html(self):
        url = f"http://127.0.0.1:{self.port}/"
        with urllib.request.urlopen(url) as res:
            self.assertEqual(res.status, 200)
            html = res.read().decode("utf-8")
            self.assertIn("AutoBacklog • Web UI", html)

    def test_api_status(self):
        url = f"http://127.0.0.1:{self.port}/api/status"
        with urllib.request.urlopen(url) as res:
            self.assertEqual(res.status, 200)
            data = json.loads(res.read().decode("utf-8"))
            self.assertFalse(data["running"])
            self.assertEqual(data["project_name"], "UnitTestProject")

    def test_api_config_get_and_post(self):
        # GET config
        url = f"http://127.0.0.1:{self.port}/api/config"
        with urllib.request.urlopen(url) as res:
            self.assertEqual(res.status, 200)
            cfg = json.loads(res.read().decode("utf-8"))
            self.assertEqual(cfg["project_name"], "UnitTestProject")

if __name__ == "__main__":
    unittest.main()
