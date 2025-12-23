from dataclasses import dataclass
from threading import Lock
from time import time

@dataclass
class BrowserSnapshot:
    domain: str = ""
    title: str = ""
    scroll_count: int = 0
    key_count: int = 0
    ts: float = 0.0

class BrowserCollector:
    def __init__(self):
        self._lock = Lock()
        self._snap = BrowserSnapshot()

    def update(self, domain: str, title: str, scroll_count: int, key_count: int):
        with self._lock:
            self._snap = BrowserSnapshot(
                domain=domain or "",
                title=title or "",
                scroll_count=int(scroll_count or 0),
                key_count=int(key_count or 0),
                ts=time(),
            )

    def snapshot(self) -> BrowserSnapshot:
        with self._lock:
            return self._snap
