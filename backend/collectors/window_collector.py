import time
import pygetwindow as gw
from dataclasses import dataclass

@dataclass
class WindowSnapshot:
    app: str
    title: str
    changed: bool


class WindowCollector:
    def __init__(self):
        self.last_window = None

    def snapshot(self) -> WindowSnapshot:
        try:
            win = gw.getActiveWindow()
            if not win:
                return WindowSnapshot("Unknown", "", False)

            title = win.title or ""
            app = win._hWnd if hasattr(win, "_hWnd") else title

            changed = title != self.last_window
            self.last_window = title

            return WindowSnapshot(app=str(app), title=title, changed=changed)
        except Exception:
            return WindowSnapshot("Unknown", "", False)
