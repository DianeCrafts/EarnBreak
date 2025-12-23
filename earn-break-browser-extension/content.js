let scrollCount = 0;
let keyCount = 0;

window.addEventListener("scroll", () => { scrollCount++; }, { passive: true });
window.addEventListener("keydown", () => { keyCount++; });

chrome.runtime.onMessage.addListener((msg, sender, sendResponse) => {
  if (msg?.type === "EARN_BREAK_GET_COUNTS") {
    sendResponse({ scrollCount, keyCount, title: document.title });
  }
});
