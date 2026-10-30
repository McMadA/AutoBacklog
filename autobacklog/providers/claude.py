"""
Anthropic Claude Code CLI (@anthropic-ai/claude-code) Provider Adapter
"""

import os
import re
import shutil
from typing import List, Optional, Tuple

from autobacklog.providers.base import BaseAIProvider


class ClaudeProvider(BaseAIProvider):
    @property
    def name(self) -> str:
        return "claude"

    @property
    def display_name(self) -> str:
        return "Anthropic Claude Code (claude)"

    def find_executable(self) -> Optional[str]:
        p = (
            shutil.which("claude.cmd")
            or shutil.which("claude.exe")
            or shutil.which("claude")
        )
        if p and os.path.isfile(p):
            return p

        app_data = os.environ.get("APPDATA", "")
        candidates = [
            os.path.join(app_data, "npm", "claude.cmd"),
            os.path.join(app_data, "npm", "claude"),
            os.path.expanduser("~/.npm-global/bin/claude"),
            "/usr/local/bin/claude",
        ]
        for c in candidates:
            if c and os.path.isfile(c):
                return c

        if shutil.which("npx") or shutil.which("npx.cmd"):
            return "npx"
        return None

    def get_default_models(self) -> Tuple[str, Optional[str], str, Optional[str]]:
        large_primary = os.environ.get("CLAUDE_LARGE_MODEL", "claude-3-7-sonnet")
        large_fallback = os.environ.get("CLAUDE_LARGE_FALLBACK", "claude-3-opus")
        small_primary = os.environ.get("CLAUDE_SMALL_MODEL", "claude-3-5-haiku")
        small_fallback = os.environ.get(
            "CLAUDE_SMALL_FALLBACK", "claude-3-7-sonnet"
        )
        return large_primary, large_fallback, small_primary, small_fallback

    def build_cmd(
        self, prompt: str, model: str, effort: str = "high"
    ) -> List[str]:
        exe = self.find_executable() or "claude"
        if exe == "npx":
            cmd = [
                "npx",
                "@anthropic-ai/claude-code",
                "-p",
                prompt,
                "--dangerously-skip-permissions",
            ]
        else:
            cmd = [exe, "-p", prompt, "--dangerously-skip-permissions"]

        if model:
            cmd.extend(["--model", model])
        return cmd

    def parse_quota_error(self, output: str) -> Optional[int]:
        if not output:
            return None
        has_quota_kw = (
            "rate limit" in output.lower()
            or "hit your message limit" in output.lower()
            or "usage limit reached" in output.lower()
            or "429" in output
        )
        if not has_quota_kw:
            return None

        # Anthropic Claude Code countdown pattern: e.g. "resets in 4 hr 12 min" or "resets at 5 PM"
        match = re.search(
            r"resets in (?:(\d+)\s*(?:hours|hr|h))?\s*(?:(\d+)\s*(?:minutes|min|m))?",
            output,
            re.IGNORECASE,
        )
        if match:
            hours = int(match.group(1) or 0)
            minutes = int(match.group(2) or 0)
            tot_sec = hours * 3600 + minutes * 60
            if tot_sec > 0:
                return tot_sec
        return 3600 * 5  # Standard Anthropic 5-hour rolling window
