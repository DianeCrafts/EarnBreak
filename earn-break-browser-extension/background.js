async function postTelemetry(payload) {
  try {
    await fetch("http://localhost:8000/telemetry/browser", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
  } catch (e) {
    // backend might be down; ignore
  }
}

function getDomain(url) {
  try { return new URL(url).hostname; } catch { return ""; }
}

async function tick() {
  const [tab] = await chrome.tabs.query({ active: true, lastFocusedWindow: true });
  if (!tab?.id) return;

  const domain = getDomain(tab.url || "");
  // Ask the content script for scroll/key counts + document title
  let counts = { scrollCount: 0, keyCount: 0, title: tab.title || "" };

  try {
    counts = await chrome.tabs.sendMessage(tab.id, { type: "EARN_BREAK_GET_COUNTS" });
  } catch {
    // content script not available (chrome pages, pdf viewer, etc.)
  }

  await postTelemetry({
    domain,
    title: counts?.title || tab.title || "",
    scroll_count: counts?.scrollCount || 0,
    key_count: counts?.keyCount || 0,
  });
}

setInterval(tick, 1000);
