from dataclasses import dataclass
from features.rolling import RollingWindow
import math

@dataclass
class InputFeatures:
    keys_per_min: float
    mouse_dist_per_min: float
    idle_ratio: float
    entropy: float
    burst_score: float


class InputFeatureExtractor:
    def __init__(self):
        self.keys = RollingWindow(60)
        self.mouse = RollingWindow(60)
        self.idle = RollingWindow(60)

    def update(self, snapshot):
        self.keys.add(snapshot.keystrokes)
        self.mouse.add(snapshot.mouse_distance)
        self.idle.add(min(1.0, snapshot.idle_seconds))

    def extract(self) -> InputFeatures:
        keys_pm = self.keys.mean() * 60
        mouse_pm = self.mouse.mean() * 60
        idle_ratio = self.idle.mean()

        # entropy proxy: variance of activity
        entropy = min(1.0, math.log1p(self.keys.var() + self.mouse.var()) / 5)

        # burst score: work happens in bursts, not constant trickle
        burst = 1.0 - min(1.0, self.keys.var() / 50)

        return InputFeatures(
            keys_per_min=keys_pm,
            mouse_dist_per_min=mouse_pm,
            idle_ratio=idle_ratio,
            entropy=entropy,
            burst_score=burst,
        )
