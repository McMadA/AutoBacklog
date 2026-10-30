"""
Smart Console Streamer
Deduplicates noisy polling messages, cleans terminal overlap, and formats raw JSON errors.
"""

import re
import sys


class SmartConsoleStreamer:
    def __init__(self, log_file=None):
        self.log_file = log_file
        self.last_clean_line = ""
        self.repeat_count = 0

    @staticmethod
    def _safe_write(text: str):
        try:
            sys.stdout.write(text)
            sys.stdout.flush()
        except UnicodeEncodeError:
            try:
                sys.stdout.buffer.write(text.encode("utf-8", errors="replace"))
                sys.stdout.buffer.flush()
            except Exception:
                sys.stdout.write(text.encode("ascii", errors="replace").decode("ascii"))
                sys.stdout.flush()

    def process_line(self, raw_line: str):
        if not raw_line:
            return

        line = raw_line.rstrip("\r\n")

        # Beautify raw 429 JSON errors
        if "RESOURCE_EXHAUSTED" in line and "short_error" in line:
            m = re.search(r"Resets in ([^\.\"]+)", line)
            rem = m.group(1) if m else "zie logs"
            line = f"🚨 [QUOTA EXHAUSTED] Individueel quotum bereikt. Reset over: {rem}"

        # Deduplicate polling messages (e.g. "Waiting for task-123...")
        is_polling = bool(
            re.match(
                r"^\s*(Waiting for|Standing by|I have launched|Watching|Waiting)\b",
                line,
                re.IGNORECASE,
            )
        )

        if is_polling and line == self.last_clean_line:
            self.repeat_count += 1
            self._safe_write(f"\r⏳ {line} [x{self.repeat_count}]")
            return
        elif self.repeat_count > 0 and is_polling:
            self._safe_write("\n")
            self.repeat_count = 0

        self.last_clean_line = line
        self._safe_write(line + "\n")

        if self.log_file:
            try:
                self.log_file.write(line + "\n")
                self.log_file.flush()
            except Exception:
                pass
