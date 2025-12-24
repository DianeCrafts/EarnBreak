# context_engine/taxonomy.py
from __future__ import annotations

import re
from typing import Dict, Tuple

# --------------------------------------------
# Context definitions
# --------------------------------------------

# These are the semantic contexts your pipeline uses everywhere.
WORK_PRIMARY = "work_primary"
WORK_SUPPORT = "work_support"
SOCIAL = "social"
PASSIVE_MEDIA = "passive_media"
BROWSER_OTHER = "browser_other"
BREAK = "break"
UNKNOWN = "unknown"

PRIMARY_CONTEXTS = {WORK_PRIMARY}

# --------------------------------------------
# App/process → context mapping (strong signal)
# --------------------------------------------

APP_PROCESS_MAP: Dict[str, str] = {
    # Code editors / IDEs
    "code.exe": WORK_PRIMARY,
    "pycharm.exe": WORK_PRIMARY,
    "idea.exe": WORK_PRIMARY,
    "intellij.exe": WORK_PRIMARY,

    # Terminals
    "cmd.exe": WORK_PRIMARY,
    "powershell.exe": WORK_PRIMARY,
    "wt.exe": WORK_PRIMARY,

    # Office / writing
    "excel.exe": WORK_PRIMARY,
    "powerpnt.exe": WORK_PRIMARY,
    "winword.exe": WORK_PRIMARY,
    "notion.exe": WORK_PRIMARY,
    "obsidian.exe": WORK_PRIMARY,
}

# (Optional) title patterns for extra robustness
TITLE_PRIMARY_PATTERNS = [
    r"\bvisual studio code\b",
    r"\bvscode\b",
    r"\bpycharm\b",
    r"\bintellij\b",
    r"\bterminal\b",
    r"\bpowershell\b",
]

TITLE_BREAK_PATTERNS = [
    r"\bbreak\b",
    r"\blocked\b",
]

def is_primary_context(ctx: str) -> bool:
    return ctx in PRIMARY_CONTEXTS


def map_to_context(
    app: str,
    window_title: str,
    browser_category: str,
    is_browser: bool,
) -> str:
    """
    Decide semantic context.
    Priority:
      1) App process (strongest)
      2) Browser intent category (only if browser active)
      3) Title heuristics
      4) Fallback
    """
    app = (app or "").lower().strip()
    title = (window_title or "").lower().strip()

    # -------------------------
    # Non-browser apps (strong signal)
    # -------------------------
    if not is_browser:
        if app in APP_PROCESS_MAP:
            return APP_PROCESS_MAP[app]

        # Title heuristics (useful if process name is unknown)
        for pat in TITLE_PRIMARY_PATTERNS:
            if re.search(pat, title):
                return WORK_PRIMARY

        for pat in TITLE_BREAK_PATTERNS:
            if re.search(pat, title):
                return BREAK

        return UNKNOWN

    # -------------------------
    # Browser (only if active)
    # -------------------------
    if browser_category in ("work_support", "search"):
        return WORK_SUPPORT
    if browser_category == "social":
        return SOCIAL
    if browser_category == "passive_media":
        return PASSIVE_MEDIA
    if browser_category == "browser_other":
        return BROWSER_OTHER

    return UNKNOWN


# --------------------------------------------
# Semantic distance matrix (0 = same, 1 = very different)
# Keep it partial; we provide a sane default.
# --------------------------------------------

DIST: Dict[Tuple[str, str], float] = {
    (WORK_PRIMARY, WORK_PRIMARY): 0.0,
    (WORK_PRIMARY, WORK_SUPPORT): 0.2,
    (WORK_SUPPORT, WORK_PRIMARY): 0.2,
    (WORK_SUPPORT, WORK_SUPPORT): 0.0,

    (WORK_PRIMARY, BROWSER_OTHER): 0.5,
    (BROWSER_OTHER, WORK_PRIMARY): 0.5,

    (WORK_PRIMARY, SOCIAL): 0.9,
    (SOCIAL, WORK_PRIMARY): 0.9,

    (WORK_PRIMARY, PASSIVE_MEDIA): 1.0,
    (PASSIVE_MEDIA, WORK_PRIMARY): 1.0,

    (WORK_SUPPORT, SOCIAL): 0.8,
    (SOCIAL, WORK_SUPPORT): 0.8,

    (WORK_SUPPORT, PASSIVE_MEDIA): 0.9,
    (PASSIVE_MEDIA, WORK_SUPPORT): 0.9,

    (UNKNOWN, WORK_PRIMARY): 0.3,
    (WORK_PRIMARY, UNKNOWN): 0.3,

    (UNKNOWN, PASSIVE_MEDIA): 0.8,
    (PASSIVE_MEDIA, UNKNOWN): 0.8,
}

def semantic_distance(a: str, b: str) -> float:
    if a == b:
        return 0.0
    return DIST.get((a, b), 0.6)
