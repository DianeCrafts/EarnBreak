import time
import threading
from pynput import keyboard, mouse
from collections import deque
from dataclasses import dataclass

@dataclass
class InputSnapshot:
    keystrokes: int
    mouse_distance: float
    idle_seconds: float


class InputCollector:
    def __init__(self):
        self._lock = threading.Lock()
        self.keystrokes = 0
        self.mouse_distance = 0.0
        self.last_activity = time.time()

        self._last_mouse_pos = None

        self.key_listener = keyboard.Listener(on_press=self._on_key)
        self.mouse_listener = mouse.Listener(on_move=self._on_move)

    def start(self):
        self.key_listener.start()
        self.mouse_listener.start()

    def _on_key(self, key):
        with self._lock:
            self.keystrokes += 1
            self.last_activity = time.time()

    def _on_move(self, x, y):
        with self._lock:
            if self._last_mouse_pos:
                dx = x - self._last_mouse_pos[0]
                dy = y - self._last_mouse_pos[1]
                self.mouse_distance += (dx**2 + dy**2) ** 0.5
            self._last_mouse_pos = (x, y)
            self.last_activity = time.time()

    def snapshot_and_reset(self) -> InputSnapshot:
        with self._lock:
            now = time.time()
            idle = max(0.0, now - self.last_activity)

            snap = InputSnapshot(
                keystrokes=self.keystrokes,
                mouse_distance=self.mouse_distance,
                idle_seconds=idle,
            )

            self.keystrokes = 0
            self.mouse_distance = 0.0

            return snap
