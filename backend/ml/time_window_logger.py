import csv
import os
from dataclasses import asdict
from typing import Optional

from ml.time_window_schema import TimeWindowFeatureRow


class TimeWindowLogger:
    def __init__(self, path: str = "data/time_windows.csv"):
        self.path = path
        self._ensure_file()

    def _ensure_file(self):
        if not os.path.exists(os.path.dirname(self.path)):
            os.makedirs(os.path.dirname(self.path), exist_ok=True)

        if not os.path.exists(self.path):
            with open(self.path, "w", newline="") as f:
                writer = csv.DictWriter(
                    f, fieldnames=TimeWindowFeatureRow.__annotations__.keys()
                )
                writer.writeheader()

    def log(self, row: TimeWindowFeatureRow):
        with open(self.path, "a", newline="") as f:
            writer = csv.DictWriter(
                f, fieldnames=TimeWindowFeatureRow.__annotations__.keys()
            )
            writer.writerow(asdict(row))
