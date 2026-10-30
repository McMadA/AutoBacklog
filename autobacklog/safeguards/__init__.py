"""
Safeguards Package
"""

from autobacklog.safeguards.dirty_guard import (
    get_dirty_git_files,
    revert_zero_diff_item,
)
from autobacklog.safeguards.hardware import detect_connected_devices
from autobacklog.safeguards.quota_cache import (
    clear_quota_cache,
    is_model_exhausted,
    load_quota_cache,
    record_quota_exhaustion,
    save_quota_cache,
)
from autobacklog.safeguards.snapshot import (
    create_preflight_snapshot,
    restore_snapshot,
)

__all__ = [
    "create_preflight_snapshot",
    "restore_snapshot",
    "load_quota_cache",
    "save_quota_cache",
    "record_quota_exhaustion",
    "is_model_exhausted",
    "clear_quota_cache",
    "get_dirty_git_files",
    "revert_zero_diff_item",
    "detect_connected_devices",
]
