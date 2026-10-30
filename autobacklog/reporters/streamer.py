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
            sys.stdout.write(f"\r⏳ {line} [x{self.repeat_count}]")
            sys.stdout.flush()
            return
        elif self.repeat_count > 0 and is_polling:
            sys.stdout.write("\n")
            self.repeat_count = 0

        self.last_clean_line = line
        print(line)

        if self.log_file:
            try:
                self.log_file.write(line + "\n")
                self.log_file.flush()
            except Exception:
                pass
