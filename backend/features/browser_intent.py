from dataclasses import dataclass
import time

WORK_SUPPORT_DOMAINS = {
    "chat.openai.com", "docs.python.org", "developer.mozilla.org",
    "stackoverflow.com", "github.com"
}
SEARCH_DOMAINS = {"google.com", "www.google.com", "duckduckgo.com", "bing.com"}
SOCIAL_DOMAINS = {"instagram.com", "www.instagram.com", "tiktok.com", "x.com", "twitter.com", "reddit.com"}
VIDEO_DOMAINS = {"youtube.com", "www.youtube.com", "netflix.com", "twitch.tv"}

@dataclass
class BrowserIntent:
    domain: str
    category: str
    doomscroll_prob: float
    reasons: list[str]

class BrowserIntentEngine:
    def __init__(self):
        self._last_domain = ""
        self._last_ts = time.time()
        self._dwell = 0.0

        self._prev_scroll = 0
        self._prev_keys = 0

    def update(self, snap):
        now = time.time()
        dt = now - self._last_ts
        self._last_ts = now

        if snap.domain == self._last_domain:
            self._dwell += dt
        else:
            self._dwell = 0.0
            self._last_domain = snap.domain
            self._prev_scroll = snap.scroll_count
            self._prev_keys = snap.key_count

    def infer(self, snap) -> BrowserIntent:
        domain = snap.domain.lower()
        reasons = []

        # Interaction rates (delta since last)
        dscroll = max(0, snap.scroll_count - self._prev_scroll)
        dkeys = max(0, snap.key_count - self._prev_keys)
        self._prev_scroll = snap.scroll_count
        self._prev_keys = snap.key_count

        scroll_rate = dscroll  # per second tick
        key_rate = dkeys

        # Base category
        if domain in WORK_SUPPORT_DOMAINS:
            category = "work_support"
        elif domain in SEARCH_DOMAINS:
            category = "search"
        elif domain in SOCIAL_DOMAINS:
            category = "social"
        elif domain in VIDEO_DOMAINS:
            category = "passive_media"
        elif domain:
            category = "browser_other"
        else:
            category = "unknown"

        # Doomscroll heuristic (behavioral signature)
        doom = 0.0
        if category in ("social", "passive_media"):
            # lots of scroll + little/no typing + long dwell => doomscroll
            if scroll_rate >= 6 and key_rate <= 1 and self._dwell >= 30:
                doom = 0.9
                reasons.append("High scrolling + low typing + long dwell on social/media")
            elif scroll_rate >= 4 and key_rate == 0 and self._dwell >= 15:
                doom = 0.7
                reasons.append("Sustained passive scrolling")
            elif self._dwell >= 60 and key_rate == 0:
                doom = 0.6
                reasons.append("Long dwell with no input on social/media")

        # If work-support with typing, doomscroll near zero
        if category in ("work_support", "search") and key_rate >= 1:
            doom = min(doom, 0.1)

        return BrowserIntent(domain=domain, category=category, doomscroll_prob=doom, reasons=reasons)
    
    def neutral(self) -> BrowserIntent:
        """
        Returns a neutral browser intent when the browser
        is NOT the active foreground window.
        """
        return BrowserIntent(
            domain="",
            category="non_browser",
            doomscroll_prob=0.0,
            reasons=[]
        )

