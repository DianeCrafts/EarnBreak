from dataclasses import dataclass
from features.rolling import RollingWindow
import math

@dataclass
class WindowFeatures:
    app_switch_rate: float
    focus_streak: int
    title_entropy: float


class WindowFeatureExtractor:
    def __init__(self):
        self.switches = RollingWindow(60)
        self.streak = 0
        self.title_changes = RollingWindow(60)
        self.last_title = None

    def update(self, snapshot):
        self.switches.add(1 if snapshot.changed else 0)

        if snapshot.changed:
            self.streak = 0
        else:
            self.streak += 1

        title_changed = snapshot.title != self.last_title
        self.title_changes.add(1 if title_changed else 0)
        self.last_title = snapshot.title

    def extract(self) -> WindowFeatures:
        return WindowFeatures(
            app_switch_rate=self.switches.mean() * 60,
            focus_streak=self.streak,
            title_entropy=min(1.0, self.title_changes.mean()),
        )
