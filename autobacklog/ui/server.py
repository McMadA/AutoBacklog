"""
AutoBacklog Web Server
Provides a zero-dependency local web interface for non-CLI users.
"""

import io
import json
import os
import socket
import sys
import threading
import time
import urllib.parse
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Optional

from autobacklog.adapters import get_backlog_adapter
from autobacklog.config import AutoBacklogConfig, load_config
from autobacklog.providers import get_ai_provider
from autobacklog.runner import BacklogRunner
from autobacklog.safeguards.quota_cache import (
    clear_quota_cache,
    load_quota_cache,
)

STATIC_DIR = os.path.join(os.path.dirname(__file__), "static")


class RunnerState:
    """Thread-safe state manager for the background runner."""

    def __init__(self, config: AutoBacklogConfig):
        self.config = config
        self.is_running = False
        self.stop_requested = False
        self.runner_thread: Optional[threading.Thread] = None
        self.active_task: Optional[dict] = None
        self.completed_tasks = []
        self.log_buffer = []
        self.max_log_lines = 1000
        self.lock = threading.Lock()

    def append_log(self, line: str):
        with self.lock:
            self.log_buffer.append(
                {"time": time.strftime("%H:%M:%S"), "text": line}
            )
            if len(self.log_buffer) > self.max_log_lines:
                self.log_buffer.pop(0)

    def get_logs(self):
        with self.lock:
            return list(self.log_buffer)

    def start_run(self, specific_id: Optional[int] = None):
        with self.lock:
            if self.is_running:
                return False, "Runner is already running"
            self.is_running = True
            self.stop_requested = False

        self.runner_thread = threading.Thread(
            target=self._run_worker, args=(specific_id,), daemon=True
        )
        self.runner_thread.start()
        return True, "Runner started"

    def stop_run(self):
        with self.lock:
            if not self.is_running:
                return False, "Runner is not running"
            self.stop_requested = True
            self.append_log("🛑 Stop request received from Web UI")
            return True, "Stop request sent"

    def _run_worker(self, specific_id: Optional[int]):
        try:
            self.append_log("🚀 Background runner initiated via Web UI")
            runner = BacklogRunner(self.config)
            
            # Monkey-patch log line interception to stream to Web UI
            orig_streamer_process = runner.reporter.set_current_task

            def hooked_set_current(item, model, tier):
                orig_streamer_process(item, model, tier)
                with self.lock:
                    self.active_task = {
                        "id": item.get("id"),
                        "title": item.get("title"),
                        "model": model,
                        "tier": tier,
                    }
                self.append_log(
                    f"🔄 Nu bezig: [#{item.get('id')}] {item.get('title')} ({model})"
                )

            runner.reporter.set_current_task = hooked_set_current

            orig_completed = runner.reporter.record_completed

            def hooked_record_completed(item, duration, model, commit):
                orig_completed(item, duration, model, commit)
                with self.lock:
                    self.completed_tasks.append(
                        {
                            "id": item.get("id"),
                            "title": item.get("title"),
                            "duration": f"{duration:.1f}s",
                            "model": model,
                            "commit": commit,
                        }
                    )
                    self.active_task = None
                self.append_log(
                    f"✅ Voltooid: [#{item.get('id')}] {item.get('title')} ({duration:.1f}s)"
                )

            runner.reporter.record_completed = hooked_record_completed

            runner.run(specific_id=specific_id)

        except Exception as e:
            self.append_log(f"❌ Error in runner worker: {e}")
        finally:
            with self.lock:
                self.is_running = False
                self.active_task = None
            self.append_log("🏁 Runner finished or paused.")


_GLOBAL_STATE: Optional[RunnerState] = None


class AutoBacklogHandler(BaseHTTPRequestHandler):
    def end_headers(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header(
            "Access-Control-Allow-Methods", "GET, POST, OPTIONS"
        )
        self.send_header(
            "Access-Control-Allow-Headers", "Content-Type"
        )
        super().end_headers()

    def do_OPTIONS(self):
        self.send_response(200)
        self.end_headers()

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path

        if path == "/" or path == "/index.html":
            self._serve_file(os.path.join(STATIC_DIR, "index.html"), "text/html")
        elif path.startswith("/static/"):
            rel = path[len("/static/") :]
            fpath = os.path.join(STATIC_DIR, rel)
            ctype = "text/plain"
            if rel.endswith(".css"):
                ctype = "text/css"
            elif rel.endswith(".js"):
                ctype = "application/javascript"
            elif rel.endswith(".svg"):
                ctype = "image/svg+xml"
            self._serve_file(fpath, ctype)
        elif path == "/api/status":
            self._handle_api_status()
        elif path == "/api/config":
            self._handle_api_config()
        elif path == "/api/backlog":
            self._handle_api_backlog()
        elif path == "/api/logs":
            self._handle_api_logs()
        else:
            self.send_error(404, "Not Found")

    def do_POST(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path

        content_length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_length) if content_length > 0 else b""
        payload = {}
        if body:
            try:
                payload = json.loads(body.decode("utf-8"))
            except Exception:
                pass

        if path == "/api/run":
            task_id = payload.get("id")
            ok, msg = _GLOBAL_STATE.start_run(specific_id=task_id)
            self._send_json({"ok": ok, "message": msg})
        elif path == "/api/stop":
            ok, msg = _GLOBAL_STATE.stop_run()
            self._send_json({"ok": ok, "message": msg})
        elif path == "/api/clear-quota":
            q_file = os.path.join(
                _GLOBAL_STATE.config.workspace_dir,
                _GLOBAL_STATE.config.safeguards.quota_cache_file,
            )
            clear_quota_cache(q_file)
            _GLOBAL_STATE.append_log("🧹 Quota cache gewist via Web UI")
            self._send_json({"ok": True, "message": "Quota cache cleared"})
        elif path == "/api/config":
            self._save_api_config(payload)
        else:
            self.send_error(404, "Not Found")

    def _serve_file(self, filepath: str, content_type: str):
        if not os.path.exists(filepath):
            self.send_error(404, "File Not Found")
            return
        try:
            with open(filepath, "rb") as f:
                content = f.read()
            self.send_response(200)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(content)))
            self.end_headers()
            self.wfile.write(content)
        except Exception as e:
            self.send_error(500, f"Error reading file: {e}")

    def _send_json(self, data: dict, status: int = 200):
        body = json.dumps(data, indent=2).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _handle_api_status(self):
        q_file = os.path.join(
            _GLOBAL_STATE.config.workspace_dir,
            _GLOBAL_STATE.config.safeguards.quota_cache_file,
        )
        quota_data = load_quota_cache(q_file)
        self._send_json(
            {
                "running": _GLOBAL_STATE.is_running,
                "active_task": _GLOBAL_STATE.active_task,
                "completed_count": len(_GLOBAL_STATE.completed_tasks),
                "completed_tasks": _GLOBAL_STATE.completed_tasks,
                "quota": quota_data,
                "project_name": _GLOBAL_STATE.config.project_name,
            }
        )

    def _handle_api_config(self):
        cfg = _GLOBAL_STATE.config
        data = {
            "project_name": cfg.project_name,
            "workspace_dir": cfg.workspace_dir,
            "max_rounds": cfg.max_rounds,
            "cooldown_seconds": cfg.cooldown_seconds,
            "backlog": {
                "type": cfg.backlog.type,
                "org_url": cfg.backlog.org_url,
                "project": cfg.backlog.project,
                "repo": cfg.backlog.repo,
                "file_path": cfg.backlog.file_path,
            },
            "provider": {
                "type": cfg.provider.type,
                "large_model": cfg.provider.large_model,
                "small_model": cfg.provider.small_model,
            },
            "safeguards": {
                "create_snapshots": cfg.safeguards.create_snapshots,
                "auto_revert_zero_diff": cfg.safeguards.auto_revert_zero_diff,
            },
        }
        self._send_json(data)

    def _save_api_config(self, payload: dict):
        # Update active config in memory and save to autobacklog.yaml
        cfg = _GLOBAL_STATE.config
        if "project_name" in payload:
            cfg.project_name = payload["project_name"]
        if "backlog" in payload:
            b = payload["backlog"]
            cfg.backlog.type = b.get("type", cfg.backlog.type)
            cfg.backlog.org_url = b.get("org_url", cfg.backlog.org_url)
            cfg.backlog.project = b.get("project", cfg.backlog.project)
            cfg.backlog.repo = b.get("repo", cfg.backlog.repo)
            cfg.backlog.file_path = b.get("file_path", cfg.backlog.file_path)
        if "provider" in payload:
            pv = payload["provider"]
            cfg.provider.type = pv.get("type", cfg.provider.type)
            cfg.provider.large_model = pv.get("large_model")
            cfg.provider.small_model = pv.get("small_model")

        # Save to YAML
        yaml_path = os.path.join(cfg.workspace_dir, "autobacklog.yaml")
        try:
            import yaml

            save_dict = {
                "project_name": cfg.project_name,
                "system_prompt_intro": cfg.system_prompt_intro,
                "max_rounds": cfg.max_rounds,
                "cooldown_seconds": cfg.cooldown_seconds,
                "backlog": {
                    "type": cfg.backlog.type,
                    "org_url": cfg.backlog.org_url,
                    "project": cfg.backlog.project,
                    "repo": cfg.backlog.repo,
                    "file_path": cfg.backlog.file_path,
                },
                "provider": {
                    "type": cfg.provider.type,
                    "large_model": cfg.provider.large_model,
                    "small_model": cfg.provider.small_model,
                },
            }
            with open(yaml_path, "w", encoding="utf-8") as f:
                yaml.dump(save_dict, f, default_flow_style=False)
            _GLOBAL_STATE.append_log(f"💾 Instellingen opgeslagen in {yaml_path}")
            self._send_json({"ok": True, "message": "Configuratie opgeslagen"})
        except Exception as e:
            self._send_json(
                {"ok": False, "message": f"Fout bij opslaan: {e}"}, status=500
            )

    def _handle_api_backlog(self):
        try:
            adapter = get_backlog_adapter(_GLOBAL_STATE.config)
            items = adapter.fetch_items(
                include_ideas=_GLOBAL_STATE.config.backlog.include_ideas
            )
            # Annotate each item with tier
            annotated = []
            for it in items:
                tier = (
                    "LARGE"
                    if any(
                        kw in (it.get("title", "") + it.get("description", "")).lower()
                        for kw in ["refactor", "architectuur", "schema", "engine", "migration"]
                    )
                    else "SMALL"
                )
                it["tier"] = tier
                annotated.append(it)
            self._send_json({"ok": True, "items": annotated})
        except Exception as e:
            self._send_json({"ok": False, "items": [], "error": str(e)})

    def _handle_api_logs(self):
        logs = _GLOBAL_STATE.get_logs()
        self._send_json({"ok": True, "logs": logs})

    def log_message(self, format, *args):
        # Suppress noisy HTTP request console logging
        pass


def find_free_port(start_port: int = 8080) -> int:
    port = start_port
    while port < start_port + 100:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            if s.connect_ex(("localhost", port)) != 0:
                return port
            port += 1
    return start_port


def start_web_ui(
    config: Optional[AutoBacklogConfig] = None,
    port: int = 8080,
    open_browser: bool = True,
):
    global _GLOBAL_STATE
    cfg = config or load_config()
    _GLOBAL_STATE = RunnerState(cfg)

    actual_port = find_free_port(port)
    server_address = ("127.0.0.1", actual_port)
    httpd = ThreadingHTTPServer(server_address, AutoBacklogHandler)

    url = f"http://localhost:{actual_port}"
    print("=" * 80)
    print(f"🌐 AutoBacklog Web UI draait op: {url}")
    print("💡 Sluit af met Ctrl+C in deze terminal")
    print("=" * 80)

    if open_browser:
        threading.Timer(0.8, lambda: webbrowser.open(url)).start()

    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n👋 AutoBacklog Web UI afgesloten.")
        httpd.server_close()
