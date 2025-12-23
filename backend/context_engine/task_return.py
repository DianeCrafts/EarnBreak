from dataclasses import dataclass
from time import time
from collections import deque
from context_engine.taxonomy import semantic_distance

@dataclass
class ContextState:
    primary: str
    current: str
    seconds_since_primary: float
    support_trip_active: bool
    support_trips_5m: int
    successful_returns_5m: int
    drift_events_5m: int


class TaskReturnEngine:
    """
    Tracks whether app switching is supportive (returning) or drifting.
    Uses a short "return window" to reward research loops.
    """

    def __init__(self, return_window_sec: int = 120):
        self.primary = "unknown"
        self.current = "unknown"
        self.return_window_sec = return_window_sec

        self.last_primary_ts = time()

        # support trip tracking
        self.trip_active = False
        self.trip_start = 0.0
        self.trip_from = "unknown"

        # rolling 5-min stats (store timestamps)
        self.support_trips = deque()
        self.success_returns = deque()
        self.drift_events = deque()

    def _prune(self):
        now = time()
        cutoff = now - 300
        while self.support_trips and self.support_trips[0] < cutoff:
            self.support_trips.popleft()
        while self.success_returns and self.success_returns[0] < cutoff:
            self.success_returns.popleft()
        while self.drift_events and self.drift_events[0] < cutoff:
            self.drift_events.popleft()

    def update(self, new_context: str):
        now = time()
        self._prune()

        prev = self.current
        self.current = new_context

        # Initialize primary when we first see real work
        if self.primary == "unknown" and new_context in ("work_primary", "work_support"):
            self.primary = "work_primary" if new_context == "work_primary" else "work_support"
            self.last_primary_ts = now
            return

        # If we are on primary context, refresh timer and maybe end trip successfully
        if new_context == self.primary:
            self.last_primary_ts = now

            if self.trip_active:
                # returned from a trip
                if now - self.trip_start <= self.return_window_sec:
                    self.success_returns.append(now)
                else:
                    # returned but too late -> drift
                    self.drift_events.append(now)
                self.trip_active = False

            return

        # If we left primary, decide if it's a "support trip" or "drift"
        dist = semantic_distance(self.primary, new_context)

        if not self.trip_active and prev == self.primary:
            # trip starts when leaving primary
            self.trip_active = True
            self.trip_start = now
            self.trip_from = self.primary
            self.support_trips.append(now)

        # If we are away from primary and distance is high, consider drift marker
        # (we don't spam drift events; only if it persists)
        if self.trip_active and (now - self.trip_start) > min(30, self.return_window_sec / 4) and dist >= 0.8:
            # record a drift event once per trip (max)
            if not self.drift_events or (now - self.drift_events[-1]) > 20:
                self.drift_events.append(now)

    def snapshot(self) -> ContextState:
        self._prune()
        now = time()
        return ContextState(
            primary=self.primary,
            current=self.current,
            seconds_since_primary=max(0.0, now - self.last_primary_ts),
            support_trip_active=self.trip_active,
            support_trips_5m=len(self.support_trips),
            successful_returns_5m=len(self.success_returns),
            drift_events_5m=len(self.drift_events),
        )
