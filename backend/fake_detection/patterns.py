def detect_fake_focus(input_f, window_f):
    reasons = []

    if input_f.entropy < 0.05 and input_f.keys_per_min < 5:
        reasons.append("Low entropy input (possible macro)")

    if input_f.mouse_dist_per_min < 50 and input_f.keys_per_min < 3:
        reasons.append("Minimal real interaction")

    if window_f.app_switch_rate > 20:
        reasons.append("Rapid app switching")

    return reasons
