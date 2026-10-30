"""
Local Markdown Plan Adapter
Parses items directly from PLAN.md or BACKLOG.md files.
"""

import os
import re
from typing import Any, Dict, List, Optional

from autobacklog.adapters.base import BaseBacklogAdapter
from autobacklog.config import AutoBacklogConfig


class MarkdownPlanAdapter(BaseBacklogAdapter):
    def __init__(self, config: AutoBacklogConfig):
        self.config = config
        self.b_cfg = config.backlog
        rel_path = self.b_cfg.file_path or "BACKLOG.md"
        self.file_path = os.path.join(config.workspace_dir, rel_path)

    @property
    def name(self) -> str:
        return "Local Markdown Plan"

    def fetch_items(self, include_ideas: bool = False) -> List[Dict[str, Any]]:
        if not os.path.exists(self.file_path):
            return []

        items = []
        try:
            with open(self.file_path, "r", encoding="utf-8") as f:
                content = f.read()

            # Pattern 1: Heading style: "### #123 Title" or "## 123. Title"
            heading_matches = re.finditer(
                r"^(?:#{2,4})\s+(?:#|Item\s+)?(\d+)[:\.\s]+([^\n]+)",
                content,
                re.MULTILINE,
            )
            found_ids = set()
            for m in heading_matches:
                t_id = int(m.group(1))
                if (
                    t_id in self.b_cfg.non_executable_ids
                    or t_id in found_ids
                ):
                    continue
                found_ids.add(t_id)
                title = m.group(2).strip()
                items.append(
                    {
                        "id": t_id,
                        "title": title,
                        "type": "Task",
                        "state": "Open",
                        "description": f"Extracted from {os.path.basename(self.file_path)} under #{t_id}",
                        "priority": 2,
                        "tags": ["MarkdownPlan"],
                        "url": f"file:///{self.file_path.replace('\\', '/')}",
                    }
                )

            # Pattern 2: Checkbox list style: "- [ ] Title (#123)" or "- [ ] #123 Title"
            checkbox_matches = re.finditer(
                r"^\s*-\s*\[([ xX])\]\s+(?:#(\d+)[:\.\s]+)?([^\n]+)",
                content,
                re.MULTILINE,
            )
            for m in checkbox_matches:
                is_done = m.group(1).lower() == "x"
                if is_done:
                    continue
                t_id_str = m.group(2)
                raw_title = m.group(3).strip()

                # Extract trailing #123 if present
                trailing_id_m = re.search(r"#(\d+)", raw_title)
                t_id = (
                    int(t_id_str)
                    if t_id_str
                    else (
                        int(trailing_id_m.group(1))
                        if trailing_id_m
                        else len(items) + 1
                    )
                )

                if (
                    t_id in self.b_cfg.non_executable_ids
                    or t_id in found_ids
                ):
                    continue
                found_ids.add(t_id)
                items.append(
                    {
                        "id": t_id,
                        "title": raw_title,
                        "type": "Task",
                        "state": "Open",
                        "description": f"Extracted checkbox item from {os.path.basename(self.file_path)}",
                        "priority": 2,
                        "tags": ["MarkdownCheckbox"],
                        "url": f"file:///{self.file_path.replace('\\', '/')}",
                    }
                )

        except Exception as e:
            print(f"⚠️ [MARKDOWN ADAPTER ERROR] Kon plan niet lezen: {e}")

        return items

    def get_item_details(self, item_id: Any) -> Optional[Dict[str, Any]]:
        items = self.fetch_items(include_ideas=True)
        for it in items:
            if str(it["id"]) == str(item_id):
                return it
        return None

    def set_state(
        self,
        item_id: Any,
        new_state: str,
        discussion_note: Optional[str] = None,
    ) -> bool:
        if new_state.lower() in ("closed", "done", "resolved"):
            return self._mark_checkbox_done(item_id)
        return True

    def post_discussion(self, item_id: Any, note: str) -> bool:
        # Markdown plans don't have interactive discussions, but we can append to a log or comment section if desired
        return True

    def _mark_checkbox_done(self, item_id: Any) -> bool:
        if not os.path.exists(self.file_path):
            return False
        try:
            with open(self.file_path, "r", encoding="utf-8") as f:
                content = f.read()

            # Replace - [ ] with - [x] for matching item
            pattern = rf"(^\s*-\s*\[)\s(\]\s+.*?(?:#{item_id}\b|\b{item_id}\b))"
            new_content = re.sub(
                pattern, r"\1x\2", content, flags=re.MULTILINE
            )
            if new_content != content:
                with open(
                    self.file_path, "w", encoding="utf-8", newline="\n"
                ) as f:
                    f.write(new_content)
                return True
        except Exception:
            pass
        return False
