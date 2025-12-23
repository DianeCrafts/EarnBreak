from collections import deque
from statistics import variance

class RollingWindow:
    def __init__(self, size: int):
        self.values = deque(maxlen=size)

    def add(self, v):
        self.values.append(v)

    def mean(self):
        return sum(self.values) / len(self.values) if self.values else 0.0

    def var(self):
        return variance(self.values) if len(self.values) > 1 else 0.0

    def last(self):
        return self.values[-1] if self.values else 0.0
