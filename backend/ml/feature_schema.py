from dataclasses import dataclass
from typing import Literal


@dataclass
class FeatureRow:
    # ==================
    # Metadata
    # ==================
    schema_version: int
    session_id: str
    tick: int
    ts: float

    # ==================
    # Input features
    # ==================
    keys_per_min: float
    mouse_dist_per_min: float
    idle_ratio: float

    # ==================
    # Task & context
    # ==================
    primary_context: str
    current_context: str
    seconds_since_primary: float

    is_on_primary: bool
    just_returned: bool
    just_left_primary: bool

    # ==================
    # Window dynamics
    # ==================
    app_switch_rate: float

    # ==================
    # Browser intent
    # ==================
    browser_category: str
    doomscroll_prob: float

    # ==================
    # Camera
    # ==================
    face_present: float
    gaze_on_screen: float
    head_motion: float
    blink_rate_60s: float
    yawn_prob: float

    # ==================
    # Rule-based output
    # ==================
    focus_score: float

    # ==================
    # Self-supervised anchor
    # ==================
    anchor_type: Literal["focus", "unfocus", "unknown"]
