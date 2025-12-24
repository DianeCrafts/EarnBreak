from dataclasses import dataclass
from time import time
from collections import deque
from context_engine.taxonomy import semantic_distance


@dataclass
class ContextState:
    primary: str
    current: str
    seconds_since_primary: float
    seconds_on_primary: float
    support_trip_active: bool
    support_trips_5m: int
    successful_returns_5m: int
    drift_events_5m: int


class TaskReturnEngine:
    """
    Tracks whether context switching is supportive (research loops)
    or drifting (loss of focus).

    Primary task:
    - Locked only on work_primary
    - Never overridden by browser contexts
    """

    def __init__(self, return_window_sec: int = 120):
        self.primary = "unknown"
        self.current = "unknown"

        self.return_window_sec = return_window_sec

        # Timestamps
        self.last_primary_enter_ts = None
        self.last_primary_leave_ts = None

        # Trip tracking
        self.trip_active = False
        self.trip_start = 0.0

        # Rolling 5-min stats
        self.support_trips = deque()
        self.success_returns = deque()
        self.drift_events = deque()

    # -------------------------
    # Helpers
    # -------------------------

    def _prune(self):
        now = time()
        cutoff = now - 300

        while self.support_trips and self.support_trips[0] < cutoff:
            self.support_trips.popleft()
        while self.success_returns and self.success_returns[0] < cutoff:
            self.success_returns.popleft()
        while self.drift_events and self.drift_events[0] < cutoff:
            self.drift_events.popleft()

    # -------------------------
    # Update logic
    # -------------------------

    def update(self, new_context: str):
        now = time()
        self._prune()

        if new_context == "unknown":
            return

        prev = self.current
        self.current = new_context

        # -------- Lock primary --------
        if self.primary == "unknown" and new_context == "work_primary":
            self.primary = "work_primary"
            self.last_primary_enter_ts = now
            self.last_primary_leave_ts = None
            return

        # -------- On primary --------
        if new_context == self.primary:
            if prev != self.primary:
                # Just returned
                self.last_primary_enter_ts = now
                self.last_primary_leave_ts = None

                if self.trip_active:
                    if now - self.trip_start <= self.return_window_sec:
                        self.success_returns.append(now)
                    else:
                        self.drift_events.append(now)
                    self.trip_active = False
            return

        # -------- Left primary --------
        if prev == self.primary and new_context != self.primary:
            self.last_primary_leave_ts = now
            self.trip_active = True
            self.trip_start = now
            self.support_trips.append(now)

        # -------- Drift detection --------
        if self.trip_active:
            dist = semantic_distance(self.primary, new_context)
            if (
                dist >= 0.8
                and (now - self.trip_start) > min(30, self.return_window_sec / 4)
            ):
                if not self.drift_events or (now - self.drift_events[-1]) > 20:
                    self.drift_events.append(now)

    # -------------------------
    # Snapshot
    # -------------------------

    def snapshot(self) -> ContextState:
        self._prune()
        now = time()

        if self.current == self.primary and self.last_primary_enter_ts:
            seconds_on_primary = now - self.last_primary_enter_ts
            seconds_since_primary = 0.0
        elif self.last_primary_leave_ts:
            seconds_on_primary = 0.0
            seconds_since_primary = now - self.last_primary_leave_ts
        else:
            seconds_on_primary = 0.0
            seconds_since_primary = 0.0

        return ContextState(
            primary=self.primary,
            current=self.current,
            seconds_since_primary=round(seconds_since_primary, 1),
            seconds_on_primary=round(seconds_on_primary, 1),
            support_trip_active=self.trip_active,
            support_trips_5m=len(self.support_trips),
            successful_returns_5m=len(self.success_returns),
            drift_events_5m=len(self.drift_events),
        )
