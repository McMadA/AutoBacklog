"""
GitHub Issues Adapter
Uses GitHub CLI (`gh`) or REST API to fetch and update issues and PRs.
"""

import json
import os
import subprocess
from typing import Any, Dict, List, Optional

from autobacklog.adapters.base import BaseBacklogAdapter
from autobacklog.config import AutoBacklogConfig


class GitHubIssuesAdapter(BaseBacklogAdapter):
    def __init__(self, config: AutoBacklogConfig):
        self.config = config
        self.b_cfg = config.backlog
        self.repo = self.b_cfg.repo or self._detect_repo()
        self.offline_cache_path = os.path.join(
            config.workspace_dir, self.b_cfg.offline_cache_file
        )

    @property
    def name(self) -> str:
        return "GitHub Issues"

    def _detect_repo(self) -> str:
        try:
            res = subprocess.run(
                ["git", "config", "--get", "remote.origin.url"],
                capture_output=True,
                text=True,
                cwd=self.config.workspace_dir,
            )
            if res.returncode == 0:
                url = res.stdout.strip()
                # ssh or https matching
                if "github.com" in url:
                    clean = (
                        url.split("github.com")[-1]
                        .lstrip(":/")
                        .removesuffix(".git")
                    )
                    return clean
        except Exception:
            pass
        return ""

    def fetch_items(self, include_ideas: bool = False) -> List[Dict[str, Any]]:
        cmd = [
            "gh",
            "issue",
            "list",
            "--state",
            "open",
            "--limit",
            "100",
            "--json",
            "number,title,body,labels,state,url",
        ]
        if self.repo:
            cmd.extend(["--repo", self.repo])

        try:
            res = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                cwd=self.config.workspace_dir,
                timeout=30,
            )
            if res.returncode == 0:
                raw_items = json.loads(res.stdout)
                self._save_offline_cache(raw_items)
                return self._parse_items(raw_items, include_ideas)
            else:
                print(
                    f"⚠️ [GITHUB ERROR] gh issue list faalde: {res.stderr.strip()}"
                )
                return self._load_offline_cache(include_ideas)
        except Exception as e:
            print(f"⚠️ [GITHUB ERROR] Uitzondering: {e}")
            return self._load_offline_cache(include_ideas)

    def _parse_items(
        self, raw_items: List[Dict[str, Any]], include_ideas: bool
    ) -> List[Dict[str, Any]]:
        parsed = []
        for it in raw_items:
            num = it.get("number")
            title = it.get("title", "").strip()
            body = it.get("body", "")
            state = it.get("state", "OPEN")
            raw_labels = it.get("labels", [])
            labels = [
                l["name"] if isinstance(l, dict) else str(l)
                for l in raw_labels
            ]

            if not include_ideas and (
                "idea" in labels or "idee" in [l.lower() for l in labels]
            ):
                continue

            parsed.append(
                {
                    "id": num,
                    "title": title,
                    "type": "Issue",
                    "state": state,
                    "description": body,
                    "priority": 2,
                    "tags": labels,
                    "url": it.get(
                        "url", f"https://github.com/{self.repo}/issues/{num}"
                    ),
                }
            )
        return parsed

    def get_item_details(self, item_id: Any) -> Optional[Dict[str, Any]]:
        cmd = [
            "gh",
            "issue",
            "view",
            str(item_id),
            "--json",
            "number,title,body,labels,state,url",
        ]
        if self.repo:
            cmd.extend(["--repo", self.repo])
        try:
            res = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                cwd=self.config.workspace_dir,
                timeout=30,
            )
            if res.returncode == 0:
                data = json.loads(res.stdout)
                raw_labels = data.get("labels", [])
                labels = [
                    l["name"] if isinstance(l, dict) else str(l)
                    for l in raw_labels
                ]
                return {
                    "id": data.get("number"),
                    "title": data.get("title"),
                    "type": "Issue",
                    "state": data.get("state"),
                    "description": data.get("body", ""),
                    "tags": labels,
                    "url": data.get("url"),
                }
        except Exception:
            pass
        return None

    def set_state(
        self,
        item_id: Any,
        new_state: str,
        discussion_note: Optional[str] = None,
    ) -> bool:
        if discussion_note:
            self.post_discussion(item_id, discussion_note)

        norm_state = new_state.lower()
        if norm_state in ("closed", "done", "resolved"):
            cmd = ["gh", "issue", "close", str(item_id)]
            if self.repo:
                cmd.extend(["--repo", self.repo])
            try:
                res = subprocess.run(
                    cmd,
                    capture_output=True,
                    cwd=self.config.workspace_dir,
                    timeout=30,
                )
                return res.returncode == 0
            except Exception:
                return False
        return True

    def post_discussion(self, item_id: Any, note: str) -> bool:
        cmd = ["gh", "issue", "comment", str(item_id), "--body", note]
        if self.repo:
            cmd.extend(["--repo", self.repo])
        try:
            res = subprocess.run(
                cmd,
                capture_output=True,
                cwd=self.config.workspace_dir,
                timeout=30,
            )
            return res.returncode == 0
        except Exception:
            return False

    def _save_offline_cache(self, raw_items: List[Dict[str, Any]]):
        try:
            os.makedirs(os.path.dirname(self.offline_cache_path), exist_ok=True)
            with open(
                self.offline_cache_path, "w", encoding="utf-8", newline="\n"
            ) as f:
                json.dump(raw_items, f, indent=2)
        except Exception:
            pass

    def _load_offline_cache(self, include_ideas: bool) -> List[Dict[str, Any]]:
        if os.path.exists(self.offline_cache_path):
            try:
                with open(self.offline_cache_path, "r", encoding="utf-8") as f:
                    raw_items = json.load(f)
                return self._parse_items(raw_items, include_ideas)
            except Exception:
                pass
        return []
