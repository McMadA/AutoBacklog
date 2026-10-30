"""
Pre-Flight Safety Net & Snapshot Manager
Creates git tag checkpoints and ZIP backups before long autonomous runs.
"""

import datetime
import os
import shutil
import subprocess
import zipfile
from typing import Optional, Tuple


def create_preflight_snapshot(
    workspace_dir: str,
    snapshots_dir: str = "_snapshots",
    tag_prefix: str = "checkpoint-night",
) -> Tuple[Optional[str], Optional[str], Optional[str]]:
    """
    Creates:
    1. A git checkpoint tag.
    2. A ZIP archive containing workspace files.
    Returns (snapshot_folder, zip_path, git_tag).
    """
    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    abs_snapshots_dir = os.path.join(workspace_dir, snapshots_dir)
    os.makedirs(abs_snapshots_dir, exist_ok=True)

    # 1. Git Tag Checkpoint
    git_tag = None
    try:
        tag_name = f"{tag_prefix}_{ts}"
        subprocess.run(
            ["git", "tag", "-f", tag_name],
            cwd=workspace_dir,
            capture_output=True,
            check=True,
        )
        git_tag = tag_name
    except Exception:
        pass

    # 2. ZIP Archive
    zip_path = os.path.join(abs_snapshots_dir, f"snapshot_{ts}.zip")
    snapshot_folder = os.path.join(abs_snapshots_dir, f"snapshot_{ts}")
    count = 0

    ignored_dirs = {
        ".git",
        "node_modules",
        "_snapshots",
        ".gradle",
        "build",
        "dist",
        "__pycache__",
        ".vault",
    }

    try:
        with zipfile.ZipFile(
            zip_path, "w", zipfile.ZIP_DEFLATED, compresslevel=6
        ) as zf:
            for root, dirs, files in os.walk(workspace_dir):
                dirs[:] = [
                    d
                    for d in dirs
                    if d not in ignored_dirs and not d.startswith(".cortex")
                ]
                for file in files:
                    if file.endswith((".zip", ".tar", ".gz", ".apk", ".aab")):
                        continue
                    full_p = os.path.join(root, file)
                    rel_p = os.path.relpath(full_p, workspace_dir)
                    try:
                        zf.write(full_p, rel_p)
                        count += 1
                    except Exception:
                        pass
    except Exception as e:
        print(f"⚠️ [SNAPSHOT ERROR] Kon snapshot ZIP niet maken: {e}")
        return None, None, git_tag

    return snapshot_folder, zip_path, git_tag


def restore_snapshot(
    workspace_dir: str, snapshots_dir: str = "_snapshots"
) -> bool:
    """Restores the latest snapshot ZIP or git tag."""
    abs_snapshots_dir = os.path.join(workspace_dir, snapshots_dir)
    if not os.path.exists(abs_snapshots_dir):
        print(f"❌ Geen snapshots gevonden in {abs_snapshots_dir}")
        return False

    zips = sorted(
        [
            os.path.join(abs_snapshots_dir, f)
            for f in os.listdir(abs_snapshots_dir)
            if f.startswith("snapshot_") and f.endswith(".zip")
        ]
    )
    if not zips:
        print(f"❌ Geen snapshot ZIP-bestanden gevonden in {abs_snapshots_dir}")
        return False

    latest_zip = zips[-1]
    print(f"🔄 Herstellen vanaf laatste snapshot: {latest_zip}")

    try:
        with zipfile.ZipFile(latest_zip, "r") as zf:
            zf.extractall(workspace_dir)
        print("✅ Snapshot succesvol hersteld over werkdirectory!")
        return True
    except Exception as e:
        print(f"❌ Fout tijdens uitpakken van snapshot: {e}")
        return False
