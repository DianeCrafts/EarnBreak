def clamp(x): 
    return max(0.0, min(1.0, x))


def compute_focus(input_f, window_f, fake_reasons, browser_intent, ctx_state, camera):

    score = 1.0
    reasons = []

    # ---- Idle penalty ----
    if input_f.idle_ratio > 0.5:
        score -= 0.4
        reasons.append("High idle time")

    # ---- App switching (context-aware) ----
    if window_f.app_switch_rate > 15:
        if browser_intent.category in ("work_support", "search"):
            reasons.append("Frequent app switching, but context is work-related")
        else:
            score -= 0.25
            reasons.append("Frequent context switching")

    # ---- Doomscroll penalty ----
    if browser_intent.doomscroll_prob >= 0.7:
        score -= 0.4
        reasons.append(
            f"Passive browsing detected ({browser_intent.category})"
        )
        reasons.extend(browser_intent.reasons)

    # ---- Supportive browsing reward ----
    if browser_intent.category in ("work_support", "search"):
        if input_f.keys_per_min >= 3:
            score += 0.15
            reasons.append("Browser activity supports active work")

    # ---- Fake activity ----
    if fake_reasons:
        score -= 0.4
        reasons.extend(fake_reasons)

    # ---- Deep focus streak ----
    if window_f.focus_streak > 30 and browser_intent.doomscroll_prob < 0.3:
        score += 0.2
        reasons.append("Sustained focus without distraction")

    # ---- Task return reward/penalty ----
    # If you left primary, you have a short window to return (research loop)
    if ctx_state.support_trip_active and ctx_state.seconds_since_primary > 120:
        score -= 0.25
        reasons.append("Away from primary task too long (no return)")

    # Reward high return success rate
    if ctx_state.support_trips_5m >= 3:
        rate = ctx_state.successful_returns_5m / max(1, ctx_state.support_trips_5m)
        if rate >= 0.7:
            score += 0.15
            reasons.append("Productive switching (quick returns detected)")
        elif rate <= 0.3 and ctx_state.drift_events_5m >= 1:
            score -= 0.15
            reasons.append("Switching often leads to drift")

            # =========================
        # Camera fusion (v1)
        # =========================

        # ---- Idle ambiguity resolution ----
        if input_f.idle_ratio > 0.6:
            if camera.face_present < 0.3:
                score -= 0.35
                reasons.append("Away from desk (no face detected)")
            else:
                score -= 0.10
                reasons.append("Low interaction (likely reading/thinking)")

        # ---- Doomscroll confirmation ----
        if browser_intent.doomscroll_prob >= 0.6:
            if camera.gaze_on_screen < 0.3:
                score -= 0.20
                reasons.append("Attention away during passive media")
            else:
                # Gaze confirms intentional watching
                score -= 0.05
                reasons.append("Passive media, but attention engaged")

        # ---- Fatigue awareness (NO penalty) ----
        if camera.yawn_prob > 0.7:
            reasons.append("Signs of fatigue detected")
        elif camera.blink_rate_60s > 18:
            reasons.append("High blink rate (possible eye fatigue)")



    return clamp(score), reasons

