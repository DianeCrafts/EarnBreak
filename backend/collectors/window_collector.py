import pygetwindow as gw
import win32gui
import win32process
import psutil
from dataclasses import dataclass


@dataclass
class WindowSnapshot:
    app: str
    title: str
    changed: bool
    is_browser: bool


class WindowCollector:
    def __init__(self):
        self.last_title = None

    def snapshot(self) -> WindowSnapshot:
        try:
            win = gw.getActiveWindow()
            if not win:
                return WindowSnapshot(
                    app="unknown",
                    title="",
                    changed=False,
                    is_browser=False,
                )

            title = win.title or ""
            hwnd = win._hWnd

            app = "unknown"
            is_browser = False

            try:
                _, pid = win32process.GetWindowThreadProcessId(hwnd)
                proc = psutil.Process(pid)
                app = proc.name().lower()  # e.g. "code.exe", "chrome.exe"

                is_browser = app in (
                    "chrome.exe",
                    "msedge.exe",
                    "firefox.exe",
                    "brave.exe",
                )
            except Exception:
                pass

            changed = title != self.last_title
            self.last_title = title

            return WindowSnapshot(
                app=app,
                title=title,
                changed=changed,
                is_browser=is_browser,
            )

        except Exception:
            return WindowSnapshot(
                app="unknown",
                title="",
                changed=False,
                is_browser=False,
            )
