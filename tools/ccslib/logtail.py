"""logtail.py - follow log files incrementally (survives truncation, handles partial last lines)."""
import os


class Tail:
    def __init__(self, path, backfill=200):
        self.path = path; self.pos = None; self.buf = b''; self.backfill = backfill

    def read_new(self, max_bytes=2_000_000):
        try: size = os.path.getsize(self.path)
        except OSError: self.pos = None; return []
        if self.pos is None:                                   # first open: start `backfill` lines before the end
            start = max(0, size - 256 * 1024)
            with open(self.path, 'rb') as f:
                f.seek(start); data = f.read()
            lines = data.decode('utf-8', 'replace').splitlines()[-self.backfill:] if self.backfill else []
            self.pos = size; self.buf = b''; return lines
        if size < self.pos: self.pos = 0; self.buf = b''      # truncated / rotated
        if size == self.pos: return []
        with open(self.path, 'rb') as f:
            f.seek(self.pos); data = f.read(min(max_bytes, size - self.pos))
        self.pos += len(data); data = self.buf + data
        parts = data.split(b'\n'); self.buf = parts.pop()      # last element is an unfinished line
        return [p.decode('utf-8', 'replace').rstrip('\r') for p in parts]
