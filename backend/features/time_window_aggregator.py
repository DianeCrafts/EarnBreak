import time
import numpy as np


class TimeWindowAggregator:
    def __init__(self, window_sec: int):
        self.window_sec = window_sec
        self.reset()

    def reset(self):
        self.start_ts = time.time()
        self.samples = []

    def add_sample(
        self,
        *,
        input_f,
        window_f,
        browser_intent,
        ctx_state,
        cam,
        is_browser: bool,
        is_on_primary: bool,
        app_changed: bool,
        ts: float,
    ):
        self.samples.append(
            {
                "ts": ts,

                # input
                "keys": input_f.keys_per_min,
                "mouse": input_f.mouse_dist_per_min,
                "idle_ratio": input_f.idle_ratio,

                # window
                "app_switch_rate": window_f.app_switch_rate,
                "app_changed": app_changed, 

                # browser
                "doomscroll_prob": browser_intent.doomscroll_prob,
                "is_browser": is_browser,

                # semantic
                "is_on_primary": is_on_primary,

                # camera
                "face_present": cam.face_present,
                "gaze_on_screen": cam.gaze_on_screen,
                "head_motion": cam.head_motion,
            }
        )


    def is_complete(self) -> bool:
        return (time.time() - self.start_ts) >= self.window_sec

    # --------------------------------------------------
    # Aggregation helpers
    # --------------------------------------------------

    def _mean(self, key):
        vals = [s[key] for s in self.samples]
        return float(np.mean(vals)) if vals else 0.0

    def _std(self, key):
        vals = [s[key] for s in self.samples]
        return float(np.std(vals)) if len(vals) > 1 else 0.0

    # --------------------------------------------------
    # Main aggregation
    # --------------------------------------------------

    def aggregate(self, *, session_start_ts: float, last_break_ts: float) -> dict:
        duration = time.time() - self.start_ts

        idle_streak = 0
        longest_idle_streak = 0

        for s in self.samples:
            if s["idle_ratio"] > 0.9:
                idle_streak += 1
                longest_idle_streak = max(longest_idle_streak, idle_streak)
            else:
                idle_streak = 0

        percent_on_primary = np.mean([s["is_on_primary"] for s in self.samples])

        browser_samples = [s for s in self.samples if s["is_browser"]]
        doomscroll_duration = sum(
            1 for s in browser_samples if s["doomscroll_prob"] > 0.7
        )

        fragmentation = self._mean("app_switch_rate")
        num_context_switches = sum(1 for s in self.samples if s["app_changed"])
        fragmentation_score = (
            num_context_switches / duration if duration > 0 else 0.0
        )
        return {
            "window_start_ts": self.start_ts,
            "window_duration": duration,

            "keys_mean": self._mean("keys"),
            "keys_std": self._std("keys"),
            "mouse_mean": self._mean("mouse"),
            "idle_ratio_mean": self._mean("idle_ratio"),
            "longest_idle_streak": float(longest_idle_streak),

            "percent_time_on_primary": float(percent_on_primary),
            "num_context_switches": num_context_switches,
            "fragmentation_score": fragmentation_score,
            "time_away_from_primary": float(duration * (1 - percent_on_primary)),

            "percent_browser_time": float(len(browser_samples) / max(len(self.samples), 1)),
            "doomscroll_prob_mean": self._mean("doomscroll_prob"),
            "doomscroll_duration": float(doomscroll_duration),

            "face_present_ratio": self._mean("face_present"),
            "gaze_on_screen_ratio": self._mean("gaze_on_screen"),
            "head_motion_mean": self._mean("head_motion"),

            "session_elapsed_time": float(time.time() - session_start_ts),
            "time_since_last_break": float(time.time() - last_break_ts),
        }

