def clamp(x): 
    return max(0.0, min(1.0, x))


def compute_focus(input_f, window_f, fake_reasons):
    score = 1.0
    reasons = []

    # Idle penalty
    if input_f.idle_ratio > 0.5:
        score -= 0.4
        reasons.append("High idle time")

    # App switching
    if window_f.app_switch_rate > 15:
        score -= 0.3
        reasons.append("Frequent app switching")

    # Entropy / fake activity
    if fake_reasons:
        score -= 0.4
        reasons.extend(fake_reasons)

    # Reward streak
    if window_f.focus_streak > 30:
        score += 0.2
        reasons.append("Sustained focus streak")

    return clamp(score), reasons
