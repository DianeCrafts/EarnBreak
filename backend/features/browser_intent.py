from dataclasses import dataclass
import time
from collections import defaultdict

WORK_SUPPORT_DOMAINS = {
    "chat.openai.com", "docs.python.org", "developer.mozilla.org",
    "stackoverflow.com", "github.com"
}
SEARCH_DOMAINS = {"google.com", "duckduckgo.com", "bing.com"}
SOCIAL_DOMAINS = {"instagram.com", "tiktok.com", "x.com", "twitter.com", "reddit.com"}
VIDEO_DOMAINS = {"youtube.com", "netflix.com", "twitch.tv"}


def normalize_domain(domain: str) -> str:
    return domain.lower().replace("www.", "").strip()


@dataclass
class BrowserIntent:
    domain: str
    category: str
    doomscroll_prob: float
    reasons: list[str]


class BrowserIntentEngine:
    def __init__(self):
        self._last_ts = time.time()

        self._domain_dwell = defaultdict(float)
        self._active_domain = ""

        self._prev_scroll = 0
        self._prev_keys = 0

    def update(self, snap):
        now = time.time()
        dt = max(0.0, now - self._last_ts)
        self._last_ts = now

        domain = normalize_domain(snap.domain)

        if domain:
            self._domain_dwell[domain] += dt
            self._active_domain = domain

    def infer(self, snap) -> BrowserIntent:
        domain = normalize_domain(snap.domain)
        reasons = []

        # Delta interaction
        dscroll = max(0, snap.scroll_count - self._prev_scroll)
        dkeys = max(0, snap.key_count - self._prev_keys)

        self._prev_scroll = snap.scroll_count
        self._prev_keys = snap.key_count

        scroll_rate = dscroll
        key_rate = dkeys
        dwell = self._domain_dwell.get(domain, 0.0)

        # Category
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

        doom = 0.0

        if category in ("social", "passive_media"):
            if scroll_rate >= 6 and key_rate <= 1 and dwell >= 30:
                doom = 0.9
                reasons.append("High scrolling + low typing + long dwell")
            elif scroll_rate >= 4 and key_rate == 0 and dwell >= 15:
                doom = 0.7
                reasons.append("Sustained passive scrolling")
            elif dwell >= 60 and key_rate == 0:
                doom = 0.6
                reasons.append("Long dwell with no interaction")

        if category in ("work_support", "search") and key_rate >= 1:
            doom = min(doom, 0.1)

        return BrowserIntent(
            domain=domain,
            category=category,
            doomscroll_prob=doom,
            reasons=reasons,
        )

    def neutral(self) -> BrowserIntent:
        return BrowserIntent(
            domain="",
            category="non_browser",
            doomscroll_prob=0.0,
            reasons=[],
        )
