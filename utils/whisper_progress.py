import re
import sys
from typing import Optional


class WhisperProgressRedirector:
    def __init__(self, original_stream, send_progress_fn=None):
        self.original_stream = original_stream
        self.send_progress_fn = send_progress_fn
        self.buffer = ""
        self.last_percent = -1
        self.percent_regex = re.compile(r'(\d{1,3})%\|')

    def write(self, text: str) -> int:
        # Weiterhin normal ins Original-Log schreiben
        self.original_stream.write(text)
        self.original_stream.flush()

        # Für Parsing puffern
        self.buffer += text

        while "\n" in self.buffer:
            line, self.buffer = self.buffer.split("\n", 1)
            self._handle_line(line)

        # tqdm schreibt oft mit \r statt \n
        if "\r" in self.buffer:
            parts = self.buffer.split("\r")
            self.buffer = parts[-1]
            for part in parts[:-1]:
                self._handle_line(part)

        return len(text)

    def flush(self) -> None:
        self.original_stream.flush()

    def _handle_line(self, line: str) -> None:
        match = self.percent_regex.search(line)
        if not match:
            return

        percent = int(match.group(1))
        if percent == self.last_percent:
            return

        self.last_percent = percent

        if self.send_progress_fn:
            self.send_progress_fn(f"Transkription bei {percent}%")