def clamp(x): 
    return max(0.0, min(1.0, x))


def compute_focus(input_f, window_f, fake_reasons, browser_intent):
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

    return clamp(score), reasons

