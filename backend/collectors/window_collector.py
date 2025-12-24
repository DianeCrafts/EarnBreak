# import pygetwindow as gw
# import win32gui
# import win32process
# import psutil
# from dataclasses import dataclass


# @dataclass
# class WindowSnapshot:
#     app: str
#     title: str
#     changed: bool
#     is_browser: bool


# class WindowCollector:
#     def __init__(self):
#         self.last_title = None

#     def snapshot(self) -> WindowSnapshot:
#         try:
#             win = gw.getActiveWindow()
#             if not win:
#                 return WindowSnapshot(
#                     app="unknown",
#                     title="",
#                     changed=False,
#                     is_browser=False,
#                 )

#             title = win.title or ""
#             hwnd = win._hWnd

#             app = "unknown"
#             is_browser = False

#             try:
#                 _, pid = win32process.GetWindowThreadProcessId(hwnd)
#                 proc = psutil.Process(pid)
#                 app = proc.name().lower()  # e.g. "code.exe", "chrome.exe"

#                 is_browser = app in (
#                     "chrome.exe",
#                     "msedge.exe",
#                     "firefox.exe",
#                     "brave.exe",
#                 )
#             except Exception:
#                 pass

#             changed = title != self.last_title
#             self.last_title = title

#             return WindowSnapshot(
#                 app=app,
#                 title=title,
#                 changed=changed,
#                 is_browser=is_browser,
#             )

#         except Exception:
#             return WindowSnapshot(
#                 app="unknown",
#                 title="",
#                 changed=False,
#                 is_browser=False,
#             )


import pygetwindow as gw
import win32process
import psutil
from dataclasses import dataclass


@dataclass
class WindowSnapshot:
    app: str
    title: str
    app_changed: bool
    title_changed: bool
    is_browser: bool


class WindowCollector:
    def __init__(self):
        self.last_app = None
        self.last_title = None

    def snapshot(self) -> WindowSnapshot:
        try:
            win = gw.getActiveWindow()
            if not win:
                return WindowSnapshot(
                    app="unknown",
                    title="",
                    app_changed=False,
                    title_changed=False,
                    is_browser=False,
                )

            title = win.title or ""
            hwnd = win._hWnd

            app = "unknown"
            is_browser = False

            try:
                _, pid = win32process.GetWindowThreadProcessId(hwnd)
                proc = psutil.Process(pid)
                app = proc.name().lower()

                is_browser = app in {
                    "chrome.exe",
                    "msedge.exe",
                    "firefox.exe",
                    "brave.exe",
                }
            except Exception:
                pass

            app_changed = app != self.last_app
            title_changed = title != self.last_title

            self.last_app = app
            self.last_title = title

            return WindowSnapshot(
                app=app,
                title=title,
                app_changed=app_changed,
                title_changed=title_changed,
                is_browser=is_browser,
            )

        except Exception:
            return WindowSnapshot(
                app="unknown",
                title="",
                app_changed=False,
                title_changed=False,
                is_browser=False,
            )
