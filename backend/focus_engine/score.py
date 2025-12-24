# backend/focus_engine/score.py

def clamp(x: float) -> float:
    return max(0.0, min(1.0, x))


def compute_focus(input_f, window_f, fake_reasons, browser_intent, ctx_state, camera):
    """
    Focus score philosophy:
    - Start neutral
    - Add positive evidence of focus
    - Subtract negative evidence of distraction
    - Use camera as confidence amplifier
    """

    score = 0.5
    reasons = []

    # ======================================================
    # POSITIVE EVIDENCE (focus signals)
    # ======================================================

    # Active engagement
    if input_f.keys_per_min >= 4:
        score += 0.20
        reasons.append("Active typing detected")

    # On primary task
    if ctx_state.current == ctx_state.primary:
        score += 0.20
        reasons.append("On primary task")

    # Sustained focus streak
    if window_f.focus_streak >= 30:
        score += 0.20
        reasons.append("Sustained focus")

    # Supportive browsing while active
    if (
        browser_intent.category in ("work_support", "search")
        and input_f.keys_per_min >= 3
    ):
        score += 0.10
        reasons.append("Supportive browsing for work")

    # Productive task returns
    if ctx_state.support_trips_5m >= 3:
        rate = ctx_state.successful_returns_5m / max(1, ctx_state.support_trips_5m)
        if rate >= 0.7:
            score += 0.10
            reasons.append("Quick returns to task")

    # ======================================================
    # NEGATIVE EVIDENCE (distraction signals)
    # ======================================================

    # High idle time
    if input_f.idle_ratio > 0.6:
        score -= 0.30
        reasons.append("High idle time")

    # Frequent context switching (non-work)
    if window_f.app_switch_rate > 15:
        if browser_intent.category not in ("work_support", "search"):
            score -= 0.25
            reasons.append("Frequent context switching")

    # Doomscrolling
    if browser_intent.doomscroll_prob >= 0.7:
        score -= 0.40
        reasons.append(f"Doomscrolling ({browser_intent.category})")
        reasons.extend(browser_intent.reasons)

    # Away from primary task too long
    if ctx_state.seconds_since_primary > 120:
        score -= 0.30
        reasons.append("Away from primary task too long")

    # Fake activity
    if fake_reasons:
        score -= 0.40
        reasons.extend(fake_reasons)

    # ======================================================
    # CAMERA FUSION (confidence amplifier — ALWAYS applied)
    # ======================================================

    # Idle ambiguity
    if input_f.idle_ratio > 0.6:
        if camera.face_present < 0.3:
            score -= 0.50
            reasons.append("Away from desk")
        else:
            score -= 0.15
            reasons.append("Idle but present")

    # Doomscroll confirmation
    if browser_intent.doomscroll_prob >= 0.6:
        if camera.gaze_on_screen < 0.3:
            score -= 0.30
            reasons.append("Low attention during passive media")
        else:
            score -= 0.10
            reasons.append("Passive media but attentive")

    # ======================================================
    # FATIGUE SIGNALS (NO penalty)
    # ======================================================

    if camera.yawn_prob > 0.7:
        reasons.append("Signs of fatigue detected")
    elif camera.blink_rate_60s > 18:
        reasons.append("Possible eye fatigue")

    # ======================================================
    # FINAL
    # ======================================================

    return clamp(score), reasons
