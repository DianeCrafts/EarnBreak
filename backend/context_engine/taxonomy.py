
APP_PROCESS_MAP = {
    # Code editors / IDEs
    "code.exe": "work_primary",
    "pycharm.exe": "work_primary",
    "idea.exe": "work_primary",
    "intellij.exe": "work_primary",

    # Terminals
    "cmd.exe": "work_primary",
    "powershell.exe": "work_primary",
    "wt.exe": "work_primary",

    # Office / writing
    "excel.exe": "work_primary",
    "powerpnt.exe": "work_primary",
    "winword.exe": "work_primary",
    "notion.exe": "work_primary",
    "obsidian.exe": "work_primary",
}

# Browser intent categories come from BrowserIntentEngine


def map_to_context(
    app: str,
    window_title: str,
    browser_category: str,
    is_browser: bool,
) -> str:
    """
    Decide semantic context.
    Priority:
    1. App process (strongest)
    2. Browser intent (if browser active)
    3. Fallback
    """

    app = (app or "").lower()
    title = (window_title or "").lower()

    # -------------------------
    # Non-browser apps (strong signal)
    # -------------------------
    if not is_browser:
        if app in APP_PROCESS_MAP:
            return APP_PROCESS_MAP[app]

        # Fallback heuristics
        if "visual studio code" in title:
            return "work_primary"
        if "terminal" in title or "powershell" in title:
            return "work_primary"

        return "unknown"

    # -------------------------
    # Browser (only if active)
    # -------------------------
    if browser_category in ("work_support", "search"):
        return "work_support"
    if browser_category == "social":
        return "social"
    if browser_category == "passive_media":
        return "passive_media"
    if browser_category == "browser_other":
        return "browser_other"

    return "unknown"

# Semantic distance matrix (0 = same, 1 = very different)
DIST = {
    ("work_primary", "work_primary"): 0.0,
    ("work_primary", "work_support"): 0.2,
    ("work_support", "work_primary"): 0.2,
    ("work_support", "work_support"): 0.0,

    ("work_primary", "browser_other"): 0.5,
    ("browser_other", "work_primary"): 0.5,

    ("work_primary", "social"): 0.9,
    ("social", "work_primary"): 0.9,

    ("work_primary", "passive_media"): 1.0,
    ("passive_media", "work_primary"): 1.0,

    ("work_support", "social"): 0.8,
    ("social", "work_support"): 0.8,

    ("work_support", "passive_media"): 0.9,
    ("passive_media", "work_support"): 0.9,

    ("unknown", "work_primary"): 0.3,
    ("work_primary", "unknown"): 0.3,

    ("unknown", "passive_media"): 0.8,
    ("passive_media", "unknown"): 0.8,
}

def semantic_distance(a: str, b: str) -> float:
    return DIST.get((a, b), 0.6)
