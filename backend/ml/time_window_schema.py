from dataclasses import dataclass


@dataclass
class TimeWindowFeatureRow:
    window_start_ts: float
    window_duration: float

    keys_mean: float
    keys_std: float
    mouse_mean: float
    idle_ratio_mean: float
    longest_idle_streak: float

    percent_time_on_primary: float
    num_context_switches: int
    fragmentation_score: float
    time_away_from_primary: float

    percent_browser_time: float
    doomscroll_prob_mean: float
    doomscroll_duration: float

    face_present_ratio: float
    gaze_on_screen_ratio: float
    head_motion_mean: float

    session_elapsed_time: float
    time_since_last_break: float

    label: str
