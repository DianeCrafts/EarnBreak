import asyncio
import json
import time
import uuid
from dataclasses import dataclass, asdict
from datetime import datetime, timezone

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from context_engine.taxonomy import is_primary_context
# ===============================
# Collectors (raw signals)
# ===============================

from collectors.input_collector import InputCollector
from collectors.window_collector import WindowCollector  # OS window
from collectors.browser_collector import BrowserCollector
from collectors.camera_collector import CameraCollector

# ===============================
# Feature extractors (per-tick)
# ===============================

from features.input_features import InputFeatureExtractor
from features.window_features import WindowFeatureExtractor
from features.browser_intent import BrowserIntentEngine

# ===============================
# Context
# ===============================

from context_engine.taxonomy import map_to_context

# ===============================
# Time-window pipeline (NEW)
# ===============================

from features.time_window_aggregator import TimeWindowAggregator
from ml.time_window_logger import TimeWindowLogger
from ml.time_window_schema import TimeWindowFeatureRow


# =====================================================
# GLOBAL STATE
# =====================================================

SESSION_ID = str(uuid.uuid4())
SESSION_START_TS = time.time()
LAST_BREAK_TS = SESSION_START_TS

TIME_WINDOW_SEC = 60

# =====================================================
# COLLECTORS & ENGINES
# =====================================================

input_collector = InputCollector()
os_window_collector = WindowCollector()
browser_collector = BrowserCollector()
camera_collector = CameraCollector(camera_index=0, fps=10)

input_fx = InputFeatureExtractor()
os_window_fx = WindowFeatureExtractor()

browser_intent_engine = BrowserIntentEngine()

time_window_agg = TimeWindowAggregator(TIME_WINDOW_SEC)
time_window_logger = TimeWindowLogger()

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
    input_collector.stop()
    camera_collector.stop()


# =====================================================
# MODELS
# =====================================================

@dataclass
class LiveState:
    ts: str

    active_app: str
    active_title: str
    active_is_browser: bool

    browser_domain: str
    browser_category: str
    doomscroll_prob: float

    face_present: float
    gaze_on_screen: float
    head_motion: float


class BrowserEvent(BaseModel):
    domain: str
    title: str
    scroll_count: int = 0
    key_count: int = 0


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
    await ws.accept()

    try:
        while True:
            # -------------------------
            # Collect raw snapshots
            # -------------------------

            inp = input_collector.snapshot_and_reset()
            os_win = os_window_collector.snapshot()

            input_fx.update(inp)
            os_window_fx.update(os_win)

            input_f = input_fx.extract()
            os_window_f = os_window_fx.extract()

            # -------------------------
            # Browser intent (only if browser)
            # -------------------------

            browser_snap = browser_collector.snapshot()
            if os_win.is_browser:
                browser_intent_engine.update(browser_snap)
                browser_intent = browser_intent_engine.infer(browser_snap)
            else:
                browser_intent = browser_intent_engine.neutral()

            print(browser_intent.doomscroll_prob)

            # -------------------------
            # Context (semantic only)
            # -------------------------

            semantic_ctx = map_to_context(
                app=os_win.app,
                window_title=os_win.title,
                browser_category=browser_intent.category,
                is_browser=os_win.is_browser,
            )

            is_on_primary = semantic_ctx == "primary"
            

            is_on_primary = is_primary_context(semantic_ctx)
            # -------------------------
            # Camera
            # -------------------------

            cam = camera_collector.snapshot()

            # -------------------------
            # Add sample to TIME WINDOW
            # -------------------------
            time_window_agg.add_sample(
                input_f=input_f,
                window_f=os_window_f,
                browser_intent=browser_intent,
                ctx_state=None,
                cam=cam,
                is_browser=os_win.is_browser,
                is_on_primary=is_on_primary,
                app_changed=os_win.app_changed,
                ts=time.time(),
            )

            # -------------------------
            # If TIME WINDOW is complete → ask for label
            # -------------------------

            if time_window_agg.is_complete():
                features = time_window_agg.aggregate(
                    session_start_ts=SESSION_START_TS,
                    last_break_ts=LAST_BREAK_TS,
                )

                # Ask frontend for label
                await ws.send_text(
                    json.dumps(
                        {
                            "type": "label_request",
                            "features": features,
                        }
                    )
                )

                label_msg = await ws.receive_json()
                label = label_msg["label"]

                time_window_logger.log(
                    TimeWindowFeatureRow(
                        **features,
                        label=label,
                    )
                )

                time_window_agg.reset()

            # -------------------------
            # Lightweight live UI state
            # -------------------------

            live_state = LiveState(
                ts=datetime.now(timezone.utc).isoformat(),

                active_app=os_win.app,
                active_title=os_win.title,
                active_is_browser=os_win.is_browser,

                browser_domain=browser_intent.domain,
                browser_category=browser_intent.category,
                doomscroll_prob=round(browser_intent.doomscroll_prob, 2),

                face_present=round(cam.face_present, 2),
                gaze_on_screen=round(cam.gaze_on_screen, 2),
                head_motion=round(cam.head_motion, 2),
            )

            await ws.send_text(
                json.dumps(
                    {
                        "type": "live_state",
                        "data": asdict(live_state),
                    }
                )
            )

            await asyncio.sleep(1)

    except WebSocketDisconnect:
        print("WebSocket disconnected")
        return
