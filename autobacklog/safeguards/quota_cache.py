"""
Persistent AI Model Quota & Rate-Limit Cache
Saves model exhaustion timestamps and calculates countdowns across restarts.
"""

import json
import os
import time
from typing import Dict, Optional, Tuple


def load_quota_cache(cache_path: str) -> Dict[str, dict]:
    """Loads cache and automatically prunes expired quota entries."""
    if not os.path.exists(cache_path):
        return {}

    try:
        with open(cache_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        now = time.time()
        active = {}
        for model, info in data.items():
            reset_epoch = info.get("reset_epoch", 0)
            if reset_epoch > now:
                remaining_sec = max(0, int(round(reset_epoch - now)))
                hrs = remaining_sec // 3600
                mins = (remaining_sec % 3600) // 60
                info["remaining_sec"] = remaining_sec
                info["remaining_str"] = f"{hrs}h{mins:02d}m"
                active[model] = info

        return active
    except Exception:
        return {}


def save_quota_cache(cache_path: str, data: Dict[str, dict]):
    try:
        os.makedirs(os.path.dirname(cache_path), exist_ok=True)
        with open(cache_path, "w", encoding="utf-8", newline="\n") as f:
            json.dump(data, f, indent=2)
    except Exception:
        pass


def record_quota_exhaustion(cache_path: str, model: str, reset_seconds: int):
    cache = load_quota_cache(cache_path)
    now = time.time()
    reset_epoch = now + reset_seconds

    hrs = reset_seconds // 3600
    mins = (reset_seconds % 3600) // 60
    rem_str = f"{hrs}h{mins:02d}m"

    cache[model] = {
        "exhausted_at": now,
        "reset_epoch": reset_epoch,
        "reset_seconds": reset_seconds,
        "remaining_sec": reset_seconds,
        "remaining_str": rem_str,
    }
    save_quota_cache(cache_path, cache)


def is_model_exhausted(cache_path: str, model: str) -> Tuple[bool, Optional[str]]:
    cache = load_quota_cache(cache_path)
    if model in cache:
        return True, cache[model].get("remaining_str", "actief")
    return False, None


def clear_quota_cache(cache_path: str):
    if os.path.exists(cache_path):
        try:
            os.remove(cache_path)
        except Exception:
            pass
