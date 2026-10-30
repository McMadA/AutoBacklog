"""
Git Dirty State Inspector & Zero-Diff Safeguard
"""

import os
import subprocess
from typing import List, Optional, Set

from autobacklog.adapters.base import BaseBacklogAdapter


def get_dirty_git_files(
    workspace_dir: str,
    ignored_patterns: Optional[Set[str]] = None,
) -> List[str]:
    """
    Returns modified, staged, or untracked files excluding noise patterns.
    """
    defaults_ignored = {
        "run_summary.md",
        "agy_execution.log",
        "autobacklog.log",
        ".env",
        "ui.xml",
    }
    ignored = (
        defaults_ignored
        if ignored_patterns is None
        else defaults_ignored.union(ignored_patterns)
    )

    try:
        res = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=workspace_dir,
            capture_output=True,
            text=True,
            stderr=subprocess.DEVNULL,
        )
        if res.returncode != 0:
            return []

        dirty = []
        for line in res.stdout.splitlines():
            line = line.strip()
            if not line:
                continue
            parts = line.split(maxsplit=1)
            if len(parts) == 2:
                norm_p = parts[1].replace("\\", "/")
                b_name = os.path.basename(norm_p).lower()
                if (
                    b_name in ignored
                    or norm_p.lower() in ignored
                    or norm_p.startswith("_snapshots/")
                    or b_name.startswith("a8_")
                ):
                    continue
                dirty.append(norm_p)
        return dirty
    except Exception:
        return []


def revert_zero_diff_item(
    adapter: BaseBacklogAdapter,
    item_id: int,
    previous_state: str = "New",
    reason: str = "Taak geannuleerd/onderbroken zonder codewijzigingen",
) -> bool:
    """
    Safely resets a backlog item back to its initial state when aborted with zero diff.
    """
    note = (
        f"🤖 [AutoBacklog Herstel] Taak status teruggezet naar '{previous_state}'. "
        f"Reden: {reason}. Geen wijzigingen aangebracht aan de codebase."
    )
    return adapter.set_state(
        item_id, new_state=previous_state, discussion_note=note
    )
