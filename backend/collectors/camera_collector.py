import time
import threading
from dataclasses import dataclass
from collections import deque
from typing import Optional

import cv2
import numpy as np
import mediapipe as mp


@dataclass
class CameraSnapshot:
    face_present: float        # 0..1
    gaze_on_screen: float      # 0..1 (proxy)
    head_motion: float         # 0..1 (proxy)
    blink_rate_60s: float      # blinks per 60s window
    yawn_prob: float           # 0..1 (proxy)


def _l2(a, b) -> float:
    return float(np.linalg.norm(np.array(a) - np.array(b)))


def _clamp(x: float, lo=0.0, hi=1.0) -> float:
    return max(lo, min(hi, x))


class CameraCollector:
    """
    Runs webcam capture in a background thread.
    Uses MediaPipe FaceMesh to compute:
      - face_present
      - gaze_on_screen (simple head-center proxy for v1)
      - head_motion (landmark movement proxy)
      - blink_rate_60s (EAR-based blink count in last 60s)
      - yawn_prob (mouth opening ratio proxy)
    """

    def __init__(self, camera_index: int = 0, fps: int = 10):
        self.camera_index = camera_index
        self.target_fps = fps

        self._lock = threading.Lock()
        self._running = False
        self._thread: Optional[threading.Thread] = None

        # last computed snapshot
        self._snap = CameraSnapshot(
            face_present=0.0,
            gaze_on_screen=0.0,
            head_motion=0.0,
            blink_rate_60s=0.0,
            yawn_prob=0.0,
        )

        # internal state
        self._prev_nose = None
        self._blink_closed = False
        self._blink_times = deque()  # timestamps of blinks (rolling 60s)

        # MediaPipe
        self._mp_face_mesh = mp.solutions.face_mesh.FaceMesh(
            static_image_mode=False,
            max_num_faces=1,
            refine_landmarks=True,     # enables iris landmarks too
            min_detection_confidence=0.5,
            min_tracking_confidence=0.5,
        )

        self._cap = None

    def start(self):
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def stop(self):
        self._running = False
        if self._thread:
            self._thread.join(timeout=2)

    def snapshot(self) -> CameraSnapshot:
        with self._lock:
            return self._snap

    def _run(self):
        # Use CAP_DSHOW on Windows to avoid long camera open delays sometimes
        self._cap = cv2.VideoCapture(self.camera_index, cv2.CAP_DSHOW)
        if not self._cap.isOpened():
            # keep running but output zeros
            while self._running:
                time.sleep(1)
            return

        frame_interval = 1.0 / max(1, self.target_fps)

        while self._running:
            t0 = time.time()
            ok, frame = self._cap.read()
            if not ok or frame is None:
                time.sleep(frame_interval)
                continue

            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            result = self._mp_face_mesh.process(rgb)

            now = time.time()
            face_present = 1.0 if result.multi_face_landmarks else 0.0

            gaze_on_screen = 0.0
            head_motion = 0.0
            yawn_prob = 0.0

            if face_present:
                lm = result.multi_face_landmarks[0].landmark

                # Helper: landmark -> (x,y)
                def p(i):
                    return (lm[i].x, lm[i].y)

                # --- Head motion proxy (nose movement normalized) ---
                nose = p(1)  # near nose tip
                left_eye_outer = p(33)
                right_eye_outer = p(263)
                inter_ocular = max(1e-6, _l2(left_eye_outer, right_eye_outer))

                if self._prev_nose is not None:
                    move = _l2(nose, self._prev_nose) / inter_ocular
                    head_motion = _clamp(move * 5.0)  # scale factor for 0..1
                self._prev_nose = nose

                # --- Gaze-on-screen proxy (head centered) ---
                # This is NOT true eye gaze; it's a strong v1 proxy:
                # if face is centered and stable, likely looking at screen.
                eye_mid = (
                    (left_eye_outer[0] + right_eye_outer[0]) / 2.0,
                    (left_eye_outer[1] + right_eye_outer[1]) / 2.0,
                )
                nose_offset = abs(nose[0] - eye_mid[0]) / (inter_ocular + 1e-6)
                gaze_on_screen = _clamp(1.0 - nose_offset * 2.0)

                # --- Blink detection (EAR) ---
                # MediaPipe FaceMesh eye landmarks (common subset)
                left = [33, 160, 158, 133, 153, 144]
                right = [362, 385, 387, 263, 373, 380]

                def ear(idx):
                    p1 = p(idx[0]); p2 = p(idx[1]); p3 = p(idx[2])
                    p4 = p(idx[3]); p5 = p(idx[4]); p6 = p(idx[5])
                    return (_l2(p2, p6) + _l2(p3, p5)) / (2.0 * max(1e-6, _l2(p1, p4)))

                ear_l = ear(left)
                ear_r = ear(right)
                ear_avg = (ear_l + ear_r) / 2.0

                BLINK_THR = 0.21
                if ear_avg < BLINK_THR:
                    if not self._blink_closed:
                        self._blink_closed = True
                else:
                    if self._blink_closed:
                        self._blink_closed = False
                        self._blink_times.append(now)

                # prune blink times to last 60s
                cutoff = now - 60.0
                while self._blink_times and self._blink_times[0] < cutoff:
                    self._blink_times.popleft()

                blink_rate_60s = float(len(self._blink_times))

                # --- Yawn proxy (mouth opening ratio) ---
                # upper lip (13), lower lip (14), mouth corners (78, 308)
                mar = _l2(p(13), p(14)) / max(1e-6, _l2(p(78), p(308)))
                # map ratio to probability
                yawn_prob = _clamp((mar - 0.03) / 0.05)

            else:
                # no face => reset some state
                self._prev_nose = None
                self._blink_closed = False
                # Keep blink history (optional). You can also clear it:
                # self._blink_times.clear()

                blink_rate_60s = float(len(self._blink_times))

            with self._lock:
                self._snap = CameraSnapshot(
                    face_present=face_present,
                    gaze_on_screen=gaze_on_screen,
                    head_motion=head_motion,
                    blink_rate_60s=blink_rate_60s,
                    yawn_prob=yawn_prob,
                )

            elapsed = time.time() - t0
            sleep_for = max(0.0, frame_interval - elapsed)
            time.sleep(sleep_for)

        if self._cap:
            self._cap.release()
