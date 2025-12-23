# A small, human-readable taxonomy. You can expand anytime.

APP_KEYWORDS = {
    "vscode": "work_primary",
    "pycharm": "work_primary",
    "intellij": "work_primary",
    "excel": "work_primary",
    "powerpoint": "work_primary",
    "word": "work_primary",
    "notion": "work_primary",
    "obsidian": "work_primary",
    "terminal": "work_primary",
    "cmd": "work_primary",
    "powershell": "work_primary",
}

# Browser intent categories are already produced by Step 1:
# work_support, search, social, passive_media, browser_other, unknown

def map_to_context(window_title: str, browser_category: str) -> str:
    """
    Decide a coarse semantic context for scoring continuity.
    Priority: explicit app keywords -> browser category -> fallback.
    """
    t = (window_title or "").lower()

    for k, ctx in APP_KEYWORDS.items():
        if k in t:
            return ctx

    # Browser category mapping to semantic contexts
    if browser_category in ("work_support", "search"):
        return "work_support"
    if browser_category in ("social",):
        return "social"
    if browser_category in ("passive_media",):
        return "passive_media"
    if browser_category in ("browser_other",):
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
}

def semantic_distance(a: str, b: str) -> float:
    return DIST.get((a, b), 0.6)
