import asyncio
import json
import random
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from typing import List

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from collectors.input_collector import InputCollector
from collectors.window_collector import WindowCollector

from features.input_features import InputFeatureExtractor
from features.window_features import WindowFeatureExtractor
from fake_detection.patterns import detect_fake_focus
from focus_engine.score import compute_focus
from collectors.browser_collector import BrowserCollector
from pydantic import BaseModel

input_fx = InputFeatureExtractor()
window_fx = WindowFeatureExtractor()

input_collector = InputCollector()
window_collector = WindowCollector()
browser_collector = BrowserCollector()
input_collector.start()
app = FastAPI()

# For Vue dev server (Vite).
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:5174"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@dataclass
class LiveState:
    ts: str
    focus_score: float          # 0..1
    time_speed: float           # e.g., 0.5..1.5
    work_credits: float         # accumulates
    credits_target: float       # needed to earn a break
    reasons: List[str]          # explainable feedback


def score_to_speed(focus: float) -> float:
    if focus >= 0.80:
        return 1.40
    if focus >= 0.60:
        return 1.15
    if focus >= 0.40:
        return 1.00
    if focus >= 0.20:
        return 0.80
    return 0.60


def reasons_from_focus(focus: float) -> List[str]:
    if focus >= 0.80:
        return ["High focus: time speeds up", "Keep consistent activity"]
    if focus >= 0.60:
        return ["Good focus: slight boost", "Avoid app switching"]
    if focus >= 0.40:
        return ["Neutral: normal pace", "Try longer focus streaks"]
    if focus >= 0.20:
        return ["Low focus: time slowed", "Reduce distractions"]
    return ["Very low focus: heavy slowdown", "Take 30s to reset and refocus"]


# Simple in-memory session state (v1)
SESSION_RUNNING = True
WORK_CREDITS = 0.0
CREDITS_TARGET = 2.0 * 60 * 60  # 2 hours worth of "credits" in seconds (conceptual)


@app.get("/health")
def health():
    return {"ok": True, "service": "earn-break-backend"}


@app.websocket("/ws")
async def ws_endpoint(ws: WebSocket):
    global WORK_CREDITS, SESSION_RUNNING

    await ws.accept()

    try:
        while True:
            inp = input_collector.snapshot_and_reset()
            win = window_collector.snapshot()


            input_fx.update(inp)
            window_fx.update(win)

            input_f = input_fx.extract()
            window_f = window_fx.extract()

            fake_reasons = detect_fake_focus(input_f, window_f)
            focus, reasons = compute_focus(input_f, window_f, fake_reasons)
            speed = score_to_speed(focus)

            # Credits accumulate faster/slower based on speed
            # Every tick is 1 second of wall clock; credits earned = speed seconds
            if SESSION_RUNNING:
                WORK_CREDITS += speed

            state = LiveState(
                ts=datetime.now(timezone.utc).isoformat(),
                focus_score=round(focus, 3),
                time_speed=round(speed, 2),
                work_credits=round(WORK_CREDITS, 1),
                credits_target=float(CREDITS_TARGET),
                reasons=reasons_from_focus(focus),
            )

            await ws.send_text(json.dumps(asdict(state)))
            await asyncio.sleep(1)


    except WebSocketDisconnect:
        return



class BrowserEvent(BaseModel):
    domain: str
    title: str
    scroll_count: int = 0
    key_count: int = 0

@app.post("/telemetry/browser")
def browser_telemetry(ev: BrowserEvent):
    browser_collector.update(ev.domain, ev.title, ev.scroll_count, ev.key_count)
    return {"ok": True}
