import asyncio
import json
import time
import uuid
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from typing import List

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from collectors.input_collector import InputCollector
from collectors.window_collector import WindowCollector
from collectors.browser_collector import BrowserCollector
from collectors.camera_collector import CameraCollector

from features.input_features import InputFeatureExtractor
from features.window_features import WindowFeatureExtractor
from features.browser_intent import BrowserIntentEngine

from context_engine.taxonomy import map_to_context
from context_engine.task_return import TaskReturnEngine

from fake_detection.patterns import detect_fake_focus
from focus_engine.score import compute_focus

from ml.feature_logger import FeatureLogger
from ml.feature_schema import FeatureRow


# =====================================================
# GLOBAL STATE
# =====================================================

SESSION_ID = str(uuid.uuid4())
TICK = 0

SESSION_RUNNING = True
WORK_CREDITS = 0.0
CREDITS_TARGET = 2.0 * 60 * 60  # 2 hours


# =====================================================
# COLLECTORS & ENGINES
# =====================================================

input_collector = InputCollector()
window_collector = WindowCollector()
browser_collector = BrowserCollector()
camera_collector = CameraCollector(camera_index=0, fps=10)

input_fx = InputFeatureExtractor()
window_fx = WindowFeatureExtractor()

browser_intent_engine = BrowserIntentEngine()
task_return_engine = TaskReturnEngine(return_window_sec=120)

feature_logger = FeatureLogger()


# =====================================================
# FASTAPI SETUP
# =====================================================

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:5174"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def startup():
    print("Starting collectors...")
    input_collector.start()
    camera_collector.start()


@app.on_event("shutdown")
def shutdown():
    print("Stopping collectors...")
    try:
        input_collector.stop()
        camera_collector.stop()
    except Exception as e:
        print("Shutdown error:", e)


# =====================================================
# MODELS
# =====================================================

@dataclass
class LiveState:
    ts: str

    focus_score: float
    time_speed: float
    work_credits: float
    credits_target: float
    reasons: List[str]

    active_app: str
    active_title: str
    active_is_browser: bool

    browser_domain: str
    browser_category: str
    doomscroll_prob: float

    primary_context: str
    current_context: str
    seconds_since_primary: float
    support_trips_5m: int
    successful_returns_5m: int
    drift_events_5m: int

    face_present: float
    gaze_on_screen: float
    head_motion: float
    blink_rate_60s: float
    yawn_prob: float


class BrowserEvent(BaseModel):
    domain: str
    title: str
    scroll_count: int = 0
    key_count: int = 0


# =====================================================
# HELPERS
# =====================================================

def score_to_speed(focus: float) -> float:
    return round(0.5 + focus, 2)


# =====================================================
# ROUTES
# =====================================================

@app.get("/health")
def health():
    return {"ok": True}


@app.post("/telemetry/browser")
def browser_telemetry(ev: BrowserEvent):
    browser_collector.update(
        ev.domain,
        ev.title,
        ev.scroll_count,
        ev.key_count,
    )
    return {"ok": True}


@app.websocket("/ws")
async def ws_endpoint(ws: WebSocket):
    global WORK_CREDITS, TICK

    await ws.accept()

    try:
        while True:
            TICK += 1

            # -------------------------
            # Collect signals
            # -------------------------
            inp = input_collector.snapshot_and_reset()
            win = window_collector.snapshot()

            input_fx.update(inp)
            window_fx.update(win)

            input_f = input_fx.extract()
            window_f = window_fx.extract()

            # -------------------------
            # Browser intent (gated)
            # -------------------------
            browser_snap = browser_collector.snapshot()
            if win.is_browser:
                browser_intent_engine.update(browser_snap)
                browser_intent = browser_intent_engine.infer(browser_snap)
            else:
                browser_intent = browser_intent_engine.neutral()

            # -------------------------
            # Context
            # -------------------------
            semantic_ctx = map_to_context(
                app=win.app,
                window_title=win.title,
                browser_category=browser_intent.category,
                is_browser=win.is_browser,
            )

            task_return_engine.update(semantic_ctx)
            ctx_state = task_return_engine.snapshot()

            cam = camera_collector.snapshot()

            # -------------------------
            # Focus scoring
            # -------------------------
            fake_reasons = detect_fake_focus(input_f, window_f)

            focus, reasons = compute_focus(
                input_f,
                window_f,
                fake_reasons,
                browser_intent,
                ctx_state,
                cam,
            )

            speed = score_to_speed(focus)
            if SESSION_RUNNING:
                WORK_CREDITS += speed

            # -------------------------
            # Anchor logic
            # -------------------------
            is_on_primary = ctx_state.current == ctx_state.primary

            just_returned = (
                is_on_primary
                and ctx_state.seconds_since_primary < 2.0
                and ctx_state.support_trips_5m > 0
            )

            just_left_primary = (
                not is_on_primary
                and ctx_state.seconds_since_primary < 2.0
            )

            anchor_type = "unknown"
            print(ctx_state.seconds_on_primary)
            print("!!!")
            if (
                is_on_primary
                and ctx_state.seconds_on_primary  >= 120
                and browser_intent.doomscroll_prob < 0.2
                and cam.gaze_on_screen > 0.7
                and cam.head_motion < 0.1
            ):
                anchor_type = "focus"

            # A) Doomscrolling unfocus (eyes ON screen)
            elif (
                browser_intent.doomscroll_prob >= 0.7
                and ctx_state.seconds_since_primary > 60
            ):
                anchor_type = "unfocus_hard"

            # B) Disengaged unfocus (eyes OFF screen)
            elif (
                cam.gaze_on_screen < 0.3
                and cam.face_present < 0.5
                and ctx_state.seconds_since_primary > 60
            ):
                anchor_type = "unfocus_hard"

            # -------------------------
            # ML logging
            # -------------------------
            try:
                feature_logger.log(
                    FeatureRow(
                        schema_version=FeatureLogger.SCHEMA_VERSION,
                        session_id=SESSION_ID,
                        tick=TICK,
                        ts=time.time(),

                        keys_per_min=input_f.keys_per_min,
                        mouse_dist_per_min=input_f.mouse_dist_per_min,
                        idle_ratio=input_f.idle_ratio,

                        primary_context=ctx_state.primary,
                        current_context=ctx_state.current,
                        seconds_since_primary=ctx_state.seconds_since_primary,

                        is_on_primary=is_on_primary,
                        just_returned=just_returned,
                        just_left_primary=just_left_primary,

                        app_switch_rate=window_f.app_switch_rate,

                        browser_category=browser_intent.category,
                        doomscroll_prob=browser_intent.doomscroll_prob,

                        face_present=cam.face_present,
                        gaze_on_screen=cam.gaze_on_screen,
                        head_motion=cam.head_motion,
                        blink_rate_60s=cam.blink_rate_60s,
                        yawn_prob=cam.yawn_prob,

                        focus_score=focus,
                        anchor_type=anchor_type,
                    )
                )
            except Exception as e:
                print("Feature log error:", e)

            # -------------------------
            # UI state
            # -------------------------
            state = LiveState(
                ts=datetime.now(timezone.utc).isoformat(),

                focus_score=round(focus, 3),
                time_speed=round(speed, 2),
                work_credits=round(WORK_CREDITS, 1),
                credits_target=float(CREDITS_TARGET),
                reasons=reasons,

                active_app=win.app,
                active_title=win.title,
                active_is_browser=win.is_browser,

                browser_domain=browser_intent.domain,
                browser_category=browser_intent.category,
                doomscroll_prob=round(browser_intent.doomscroll_prob, 2),

                primary_context=ctx_state.primary,
                current_context=ctx_state.current,
                seconds_since_primary=round(ctx_state.seconds_since_primary, 1),
                support_trips_5m=ctx_state.support_trips_5m,
                successful_returns_5m=ctx_state.successful_returns_5m,
                drift_events_5m=ctx_state.drift_events_5m,

                face_present=round(cam.face_present, 2),
                gaze_on_screen=round(cam.gaze_on_screen, 2),
                head_motion=round(cam.head_motion, 2),
                blink_rate_60s=round(cam.blink_rate_60s, 1),
                yawn_prob=round(cam.yawn_prob, 2),
            )

            await ws.send_text(json.dumps(asdict(state)))
            await asyncio.sleep(1)

    except WebSocketDisconnect:
        return
