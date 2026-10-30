"""
Azure DevOps Boards Adapter
Supports az boards CLI and Azure DevOps REST API with automatic offline caching.
"""

import json
import os
import re
import subprocess
from typing import Any, Dict, List, Optional

from autobacklog.adapters.base import BaseBacklogAdapter
from autobacklog.config import AutoBacklogConfig


class AzureBoardsAdapter(BaseBacklogAdapter):
    def __init__(self, config: AutoBacklogConfig):
        self.config = config
        self.b_cfg = config.backlog
        self.org_url = self.b_cfg.org_url.rstrip("/")
        self.project = self.b_cfg.project
        self.offline_cache_path = os.path.join(
            config.workspace_dir, self.b_cfg.offline_cache_file
        )

    @property
    def name(self) -> str:
        return "Azure DevOps Boards"

    def fetch_items(self, include_ideas: bool = False) -> List[Dict[str, Any]]:
        wiql = self.b_cfg.wiql or (
            f"SELECT [System.Id],[System.WorkItemType],[System.Title],[System.State],[System.Tags],[Microsoft.VSTS.Common.Priority] "
            f"FROM WorkItems WHERE [System.TeamProject]='{self.project}' "
            f"AND [System.State] NOT IN ('Closed','Resolved','Removed') "
            f"ORDER BY [Microsoft.VSTS.Common.Priority], [System.Id]"
        )

        cmd = [
            "az",
            "boards",
            "query",
            "--org",
            self.org_url,
            "--project",
            self.project,
            "--wiql",
            wiql,
            "-o",
            "json",
        ]

        try:
            res = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                cwd=self.config.workspace_dir,
                timeout=45,
            )
            if res.returncode == 0:
                raw_items = json.loads(res.stdout)
                self._save_offline_cache(raw_items)
                return self._parse_items(raw_items, include_ideas)
            else:
                err_text = res.stderr or res.stdout
                print(
                    f"⚠️ [OFFLINE / AZURE ERROR] Azure DevOps query faalde: {err_text.strip()}"
                )
                return self._load_offline_cache(include_ideas)
        except Exception as e:
            print(f"⚠️ [OFFLINE / AZURE ERROR] Uitzondering bij ophalen: {e}")
            return self._load_offline_cache(include_ideas)

    def _parse_items(
        self, raw_items: List[Dict[str, Any]], include_ideas: bool
    ) -> List[Dict[str, Any]]:
        parsed = []
        for it in raw_items:
            f = it.get("fields", {})
            w_id = it.get("id")
            w_type = f.get("System.WorkItemType", "Task")
            w_title = f.get("System.Title", "").strip()
            w_state = f.get("System.State", "New")
            tags_str = f.get("System.Tags", "")
            tags = [
                t.strip() for t in tags_str.split(";") if t.strip()
            ] if tags_str else []

            if not include_ideas and "Idee" in tags:
                continue

            parsed.append(
                {
                    "id": w_id,
                    "title": w_title,
                    "type": w_type,
                    "state": w_state,
                    "description": f.get("System.Description", ""),
                    "priority": f.get("Microsoft.VSTS.Common.Priority", 2),
                    "tags": tags,
                    "url": f"{self.org_url}/{self.project}/_workitems/edit/{w_id}",
                }
            )
        return parsed

    def get_item_details(self, item_id: Any) -> Optional[Dict[str, Any]]:
        cmd = [
            "az",
            "boards",
            "work-item",
            "show",
            "--org",
            self.org_url,
            "--id",
            str(item_id),
            "-o",
            "json",
        ]
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
                f = data.get("fields", {})
                desc_html = f.get(
                    "System.Description",
                    f.get("Microsoft.VSTS.Common.AcceptanceCriteria", ""),
                )
                clean_desc = self._strip_html(desc_html)
                return {
                    "id": item_id,
                    "title": f.get("System.Title", ""),
                    "type": f.get("System.WorkItemType", "Task"),
                    "state": f.get("System.State", "New"),
                    "description": clean_desc,
                    "tags": [
                        t.strip()
                        for t in f.get("System.Tags", "").split(";")
                        if t.strip()
                    ],
                    "url": f"{self.org_url}/{self.project}/_workitems/edit/{item_id}",
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
        cmd = [
            "az",
            "boards",
            "work-item",
            "update",
            "--org",
            self.org_url,
            "--id",
            str(item_id),
            "--state",
            new_state,
        ]
        if discussion_note:
            cmd.extend(["--discussion", discussion_note])

        try:
            res = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                cwd=self.config.workspace_dir,
                timeout=30,
            )
            return res.returncode == 0
        except Exception:
            return False

    def post_discussion(self, item_id: Any, note: str) -> bool:
        cmd = [
            "az",
            "boards",
            "work-item",
            "update",
            "--org",
            self.org_url,
            "--id",
            str(item_id),
            "--discussion",
            note,
        ]
        try:
            res = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
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
                print(
                    f"📂 [OFFLINE CACHE] {len(raw_items)} items geladen uit {self.offline_cache_path}"
                )
                return self._parse_items(raw_items, include_ideas)
            except Exception:
                pass
        return []

    @staticmethod
    def _strip_html(html_str: str) -> str:
        if not html_str:
            return ""
        text = re.sub(r"<br\s*/?>", "\n", html_str, flags=re.IGNORECASE)
        text = re.sub(
            r"</div>", "\n", text, flags=re.IGNORECASE
        )
        text = re.sub(r"</p>", "\n\n", text, flags=re.IGNORECASE)
        text = re.sub(r"<[^>]+>", "", text)
        text = text.replace("&nbsp;", " ").replace("&amp;", "&").replace(
            "&lt;", "<"
        ).replace("&gt;", ">")
        return re.sub(r"\n{3,}", "\n\n", text).strip()
