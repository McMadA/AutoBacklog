"""
Google Antigravity (agy.exe) Provider Adapter
"""

import os
import re
import shutil
from typing import List, Optional, Tuple

from autobacklog.providers.base import BaseAIProvider


class AntigravityProvider(BaseAIProvider):
    @property
    def name(self) -> str:
        return "agy"

    @property
    def display_name(self) -> str:
        return "Google Antigravity (agy.exe)"

    def find_executable(self) -> Optional[str]:
        p = shutil.which("agy") or shutil.which("agy.exe")
        if p and os.path.isfile(p):
            return p

        # Common user directory locations
        local_app_data = os.environ.get("LOCALAPPDATA", "")
        candidates = [
            os.path.join(local_app_data, "agy", "bin", "agy.exe"),
            os.path.join(local_app_data, "Programs", "agy", "bin", "agy.exe"),
            os.path.expanduser("~/.antigravity/bin/agy"),
            os.path.expanduser("~/.agy/bin/agy"),
        ]
        for c in candidates:
            if c and os.path.isfile(c):
                return c
        return None

    def get_default_models(self) -> Tuple[str, Optional[str], str, Optional[str]]:
        large_primary = os.environ.get("AGY_LARGE_MODEL", "gemini-4-argon-high")
        large_fallback = os.environ.get(
            "AGY_LARGE_FALLBACK", "claude-opus-5-5-high"
        )
        small_primary = os.environ.get(
            "AGY_SMALL_MODEL", "gemini-3.8-flash-high"
        )
        small_fallback = os.environ.get(
            "AGY_SMALL_FALLBACK", "claude-sonnet-5-5-high"
        )
        return large_primary, large_fallback, small_primary, small_fallback

    def build_cmd(
        self, prompt: str, model: str, effort: str = "high"
    ) -> List[str]:
        exe = self.find_executable() or "agy"
        cmd = [
            exe,
            "-p",
            prompt,
            "--dangerously-skip-permissions",
            "--model",
            model,
        ]
        if effort:
            cmd.extend(["--effort", effort])
        return cmd

    def parse_quota_error(self, output: str) -> Optional[int]:
        if not output:
            return None
        has_quota_kw = (
            "Individual quota reached" in output
            or "RESOURCE_EXHAUSTED" in output
            or "error_code\":429" in output
            or "Rate limit exceeded" in output
        )
        if not has_quota_kw:
            return None

        # Parse countdown: e.g. "Resets in 150h38m35s" or "Resets in 4h20m"
        match = re.search(
            r"Resets in (?:(\d+)d)?(?:(\d+)h)?(?:(\d+)m)?(?:(\d+)s)?",
            output,
            re.IGNORECASE,
        )
        if match:
            days = int(match.group(1) or 0)
            hours = int(match.group(2) or 0)
            minutes = int(match.group(3) or 0)
            seconds = int(match.group(4) or 0)
            tot_sec = days * 86400 + hours * 3600 + minutes * 60 + seconds
            if tot_sec > 0:
                return tot_sec
        return 3600 * 24  # default 24h fallback
