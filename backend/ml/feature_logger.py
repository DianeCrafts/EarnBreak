import csv
import os
from threading import Lock
from dataclasses import fields
from ml.feature_schema import FeatureRow


class FeatureLogger:
    SCHEMA_VERSION = 1

    def __init__(self, path="data/features.csv"):
        self.path = path
        self._lock = Lock()

        os.makedirs(os.path.dirname(path), exist_ok=True)
        self._init_file()

    def _init_file(self):
        if not os.path.exists(self.path):
            with open(self.path, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)

                # Stable, explicit header order
                header = [f.name for f in fields(FeatureRow)]
                writer.writerow(header)

    def log(self, row: FeatureRow):
        with self._lock:
            with open(self.path, "a", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)

                writer.writerow(
                    [getattr(row, f.name) for f in fields(FeatureRow)]
                )
                f.flush()
                os.fsync(f.fileno())
