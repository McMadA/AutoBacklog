"""
Run Progress Reporter & Live RUN_SUMMARY.md Generator
"""

import datetime
import os
from typing import Any, Dict, List, Optional


class RunProgressReporter:
    def __init__(self, workspace_dir: str, filename: str = "RUN_SUMMARY.md"):
        self.workspace_dir = workspace_dir
        self.filepath = os.path.join(workspace_dir, filename)
        self.start_time = datetime.datetime.now()
        self.completed_tasks: List[Dict[str, Any]] = []
        self.failed_tasks: List[Dict[str, Any]] = []
        self.current_task: Optional[Dict[str, Any]] = None

    def set_current_task(self, item: Dict[str, Any], model: str, tier: str):
        self.current_task = {
            "id": item.get("id"),
            "title": item.get("title"),
            "model": model,
            "tier": tier,
            "started_at": datetime.datetime.now().strftime("%H:%M:%S"),
        }
        self.write_summary()

    def record_completed(
        self,
        item: Dict[str, Any],
        duration_sec: float,
        model: str,
        commit_hash: Optional[str] = None,
    ):
        self.completed_tasks.append(
            {
                "id": item.get("id"),
                "title": item.get("title"),
                "duration": f"{duration_sec:.1f}s",
                "model": model,
                "commit": commit_hash or "lokaal",
                "time": datetime.datetime.now().strftime("%H:%M:%S"),
            }
        )
        self.current_task = None
        self.write_summary()

    def record_failed(
        self, item: Dict[str, Any], reason: str, model: str
    ):
        self.failed_tasks.append(
            {
                "id": item.get("id"),
                "title": item.get("title"),
                "reason": reason,
                "model": model,
                "time": datetime.datetime.now().strftime("%H:%M:%S"),
            }
        )
        self.current_task = None
        self.write_summary()

    def write_summary(self):
        elapsed = datetime.datetime.now() - self.start_time
        lines = [
            "# 🚀 AutoBacklog Execution Dashboard",
            "",
            f"**Gestart om:** `{self.start_time.strftime('%Y-%m-%d %H:%M:%S')}` | **Totale Looptijd:** `{str(elapsed).split('.')[0]}`",
            "",
            "## 📊 Live Status",
        ]

        if self.current_task:
            lines.extend(
                [
                    f"* 🔄 **Nu Bezig:** [#{self.current_task['id']}] {self.current_task['title']}",
                    f"  * Model: `{self.current_task['model']}` ({self.current_task['tier']})",
                    f"  * Gestart: `{self.current_task['started_at']}`",
                ]
            )
        else:
            lines.append("* ⏸️ Geen actieve taak (in afwachting of cooldown)")

        lines.extend(
            [
                "",
                f"**Voortgang:** {len(self.completed_tasks)} voltooid | {len(self.failed_tasks)} gestopt/gepauzeerd",
                "",
                "## ✅ Voltooide Taken",
                "| ID | Titel | Model | Looptijd | Commit | Tijd |",
                "|---|---|---|---|---|---|",
            ]
        )

        if not self.completed_tasks:
            lines.append("| - | *Nog geen taken voltooid in deze sessie* | - | - | - | - |")
        else:
            for t in reversed(self.completed_tasks):
                lines.append(
                    f"| #{t['id']} | {t['title']} | `{t['model']}` | {t['duration']} | `{t['commit']}` | {t['time']} |"
                )

        if self.failed_tasks:
            lines.extend(
                [
                    "",
                    "## ⚠️ Gestopte / Gepauzeerde Taken",
                    "| ID | Titel | Reden | Model | Tijd |",
                    "|---|---|---|---|---|",
                ]
            )
            for t in reversed(self.failed_tasks):
                lines.append(
                    f"| #{t['id']} | {t['title']} | {t['reason']} | `{t['model']}` | {t['time']} |"
                )

        try:
            with open(self.filepath, "w", encoding="utf-8", newline="\n") as f:
                f.write("\n".join(lines) + "\n")
        except Exception:
            pass
