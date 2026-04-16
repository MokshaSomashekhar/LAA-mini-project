"""
Gesture-Based Drawing System
=============================

Install:
    pip install opencv-python mediapipe numpy

Run:
    python gesture_draw.py

Gestures:
    Index finger only   -> Draw (current mode)
    Two fingers up      -> Erase
    4-5 fingers open    -> Pause / lift pen
    Thumb only          -> Cycle draw mode (Free > Line > Rect > Circle)
    Pinch               -> Pick color from top palette
    Q = quit | C = clear | B = brush size
"""

import cv2
import numpy as np
import math
import time
import urllib.request
import os

import mediapipe as mp
from mediapipe.tasks import python
from mediapipe.tasks.python import vision

HAND_CONNECTIONS = [
    (0,1),(1,2),(2,3),(3,4),
    (0,5),(5,6),(6,7),(7,8),
    (5,9),(9,10),(10,11),(11,12),
    (9,13),(13,14),(14,15),(15,16),
    (13,17),(17,18),(18,19),(19,20),
    (0,17)
]

MODEL_PATH = "hand_landmarker.task"
MODEL_URL  = "https://storage.googleapis.com/mediapipe-models/hand_landmarker/hand_landmarker/float16/1/hand_landmarker.task"

def ensure_model():
    if not os.path.exists(MODEL_PATH):
        print("Downloading hand landmark model (~6 MB)...")
        urllib.request.urlretrieve(MODEL_URL, MODEL_PATH)
        print("Model downloaded.")

WINDOW     = "Gesture Draw  [Q=quit | C=clear | B=brush size]"
CAM_W, CAM_H = 1280, 720
BRUSH_SIZES  = [4, 10, 20]
COLORS = [
    ("Red",    (60,  60,  220)),
    ("Orange", (30,  140, 255)),
    ("Yellow", (20,  220, 220)),
    ("Green",  (60,  200, 80)),
    ("Cyan",   (220, 180, 40)),
    ("Blue",   (220, 80,  40)),
    ("Purple", (200, 60,  180)),
    ("White",  (240, 240, 240)),
]
MODES    = ["FREE", "LINE", "RECT", "CIRCLE"]
ERASER_R = 30

class DrawState:
    def __init__(self):
        self.canvas      = None
        self.color_idx   = 5
        self.size_idx    = 1
        self.mode_idx    = 0
        self.drawing     = False
        self.last_pt     = None
        self.start_pt    = None
        self.snap_canvas = None
        self.gesture     = "PAUSE"
        self.last_mode_ts = 0
        self.thumb_held  = False

    @property
    def color(self): return COLORS[self.color_idx][1]
    @property
    def size(self):  return BRUSH_SIZES[self.size_idx]
    @property
    def mode(self):  return MODES[self.mode_idx]

def dist(a, b):
    return math.hypot(a[0]-b[0], a[1]-b[1])

def lm_px(landmarks, idx, w, h):
    p = landmarks[idx]
    return int(p.x * w), int(p.y * h)

def fingers_up(landmarks, w, h):
    tips = [4, 8, 12, 16, 20]
    pips = [3, 6, 10, 14, 18]
    up = []
    tx, _ = lm_px(landmarks, 4, w, h)
    t3x, _ = lm_px(landmarks, 3, w, h)
    up.append(tx < t3x)
    for i in range(1, 5):
        tip = lm_px(landmarks, tips[i], w, h)
        pip = lm_px(landmarks, pips[i], w, h)
        up.append(tip[1] < pip[1])
    return up

def detect_gesture(landmarks, w, h):
    up = fingers_up(landmarks, w, h)
    thumb, idx, mid, ring, pinky = up
    if not thumb and idx and not mid and not ring and not pinky:
        return "DRAW"
    if not thumb and idx and mid and not ring and not pinky:
        return "ERASE"
    if sum(up) >= 4:
        return "PAUSE"
    if thumb and not idx and not mid and not ring and not pinky:
        return "MODE"
    tip4 = lm_px(landmarks, 4, w, h)
    tip8 = lm_px(landmarks, 8, w, h)
    if dist(tip4, tip8) < 45:
        return "PINCH"
    return "PAUSE"

def draw_free(canvas, pt, last, color, size):
    if last:
        cv2.line(canvas, last, pt, color, size, cv2.LINE_AA)
    else:
        cv2.circle(canvas, pt, max(size//2, 1), color, -1, cv2.LINE_AA)

def draw_shape(canvas, mode, start, end, color, size):
    if mode == "LINE":
        cv2.line(canvas, start, end, color, size, cv2.LINE_AA)
    elif mode == "RECT":
        cv2.rectangle(canvas, start, end, color, size)
    elif mode == "CIRCLE":
        r = int(dist(start, end))
        if r > 0:
            cv2.circle(canvas, start, r, color, size, cv2.LINE_AA)

def draw_ui(frame, s):
    h, w = frame.shape[:2]
    cv2.rectangle(frame, (0, 0), (w, 56), (18, 18, 30), -1)
    cv2.line(frame, (0, 56), (w, 56), (40, 40, 70), 1)
    for i, (name, bgr) in enumerate(COLORS):
        cx = 16 + i * 50
        if i == s.color_idx:
            cv2.circle(frame, (cx, 28), 17, (200, 200, 255), 2)
        cv2.circle(frame, (cx, 28), 13, bgr, -1)
    for i, m in enumerate(MODES):
        x = 440 + i * 95
        col = (140, 140, 255) if i == s.mode_idx else (60, 60, 90)
        cv2.putText(frame, m, (x, 34), cv2.FONT_HERSHEY_SIMPLEX, 0.46, col, 1, cv2.LINE_AA)
    for i, sz in enumerate(BRUSH_SIZES):
        cx = 840 + i * 55
        col = (140, 140, 255) if i == s.size_idx else (60, 60, 90)
        cv2.circle(frame, (cx, 28), sz//2+2, col, -1)
    gcol = {"DRAW":(80,220,80),"ERASE":(60,60,230),"PAUSE":(60,200,220),
            "MODE":(200,150,60),"PINCH":(200,80,220),"NO HAND":(80,80,80)}
    col = gcol.get(s.gesture, (120,120,120))
    cv2.putText(frame, f"[ {s.gesture} ]", (w-210, 34),
                cv2.FONT_HERSHEY_SIMPLEX, 0.55, col, 1, cv2.LINE_AA)
    cv2.rectangle(frame, (0, h-30), (w, h), (18, 18, 30), -1)
    cv2.putText(frame, "Index=DRAW  2fingers=ERASE  Open=PAUSE  Thumb=MODE  Q=quit  C=clear  B=size",
                (10, h-10), cv2.FONT_HERSHEY_SIMPLEX, 0.38, (70, 70, 100), 1, cv2.LINE_AA)

def draw_cursor(frame, pt, gesture, color, size):
    if pt is None: return
    gcol = {"DRAW":(80,220,80),"ERASE":(60,60,230),"PAUSE":(60,200,220),"MODE":(200,150,60)}
    ring = gcol.get(gesture, (160,160,160))
    if gesture == "ERASE":
        cv2.circle(frame, pt, ERASER_R, ring, 2, cv2.LINE_AA)
    else:
        cv2.circle(frame, pt, size//2+5, ring, 2, cv2.LINE_AA)
        cv2.circle(frame, pt, 3, color, -1, cv2.LINE_AA)

def draw_skeleton(frame, landmarks, w, h):
    for a, b in HAND_CONNECTIONS:
        pa = lm_px(landmarks, a, w, h)
        pb = lm_px(landmarks, b, w, h)
        cv2.line(frame, pa, pb, (60, 60, 110), 1, cv2.LINE_AA)
    for i in range(21):
        p = lm_px(landmarks, i, w, h)
        r = 5 if i in [4,8,12,16,20] else 3
        cv2.circle(frame, p, r, (100, 100, 200), -1, cv2.LINE_AA)

def main():
    ensure_model()

    base_opts = python.BaseOptions(model_asset_path=MODEL_PATH)
    opts = vision.HandLandmarkerOptions(
        base_options=base_opts,
        num_hands=1,
        min_hand_detection_confidence=0.6,
        min_hand_presence_confidence=0.6,
        min_tracking_confidence=0.5,
        running_mode=vision.RunningMode.VIDEO,
    )
    detector = vision.HandLandmarker.create_from_options(opts)

    cap = cv2.VideoCapture(0)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH,  CAM_W)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, CAM_H)
    cap.set(cv2.CAP_PROP_FPS, 30)

    cv2.namedWindow(WINDOW, cv2.WINDOW_NORMAL)
    cv2.resizeWindow(WINDOW, CAM_W, CAM_H)

    s = DrawState()
    ts_ms = 0

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        frame = cv2.flip(frame, 1)
        h, w = frame.shape[:2]

        if s.canvas is None:
            s.canvas = np.zeros((h, w, 3), dtype=np.uint8)

        ts_ms += 33

        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
        result = detector.detect_for_video(mp_image, ts_ms)

        tip_pt = None

        if result.hand_landmarks:
            landmarks = result.hand_landmarks[0]
            draw_skeleton(frame, landmarks, w, h)

            gesture = detect_gesture(landmarks, w, h)
            s.gesture = gesture
            tip_pt = lm_px(landmarks, 8, w, h)
            now = time.time()

            if gesture == "MODE":
                if not s.thumb_held and now - s.last_mode_ts > 0.6:
                    s.mode_idx = (s.mode_idx + 1) % len(MODES)
                    s.last_mode_ts = now
                s.thumb_held = True
                s.drawing = False; s.last_pt = None; s.snap_canvas = None

            elif gesture == "ERASE":
                s.thumb_held = False
                cv2.circle(s.canvas, tip_pt, ERASER_R, (0,0,0), -1)
                s.drawing = False; s.last_pt = None; s.snap_canvas = None

            elif gesture == "DRAW":
                s.thumb_held = False
                if not s.drawing:
                    s.drawing  = True
                    s.start_pt = tip_pt
                    s.last_pt  = tip_pt
                    if s.mode != "FREE":
                        s.snap_canvas = s.canvas.copy()
                else:
                    if s.mode == "FREE":
                        draw_free(s.canvas, tip_pt, s.last_pt, s.color, s.size)
                        s.last_pt = tip_pt
                    else:
                        preview = s.snap_canvas.copy()
                        draw_shape(preview, s.mode, s.start_pt, tip_pt, s.color, s.size)
                        s.canvas[:] = preview

            elif gesture == "PINCH":
                s.thumb_held = False
                px = tip_pt[0]
                for i in range(len(COLORS)):
                    cx = 16 + i * 50
                    if abs(px - cx) < 25:
                        s.color_idx = i
                        break
                s.drawing = False; s.last_pt = None; s.snap_canvas = None

            else:
                s.thumb_held = False
                if s.drawing and s.mode != "FREE":
                    s.snap_canvas = None
                s.drawing = False; s.last_pt = None

        else:
            s.gesture = "NO HAND"
            s.drawing = False; s.last_pt = None; s.snap_canvas = None

        gray = cv2.cvtColor(s.canvas, cv2.COLOR_BGR2GRAY)
        _, mask = cv2.threshold(gray, 1, 255, cv2.THRESH_BINARY)
        bg = cv2.bitwise_and(frame, frame, mask=cv2.bitwise_not(mask))
        output = cv2.add(bg, s.canvas)

        draw_ui(output, s)
        draw_cursor(output, tip_pt, s.gesture, s.color, s.size)

        cv2.imshow(WINDOW, output)

        key = cv2.waitKey(1) & 0xFF
        if key == ord('q'):
            break
        elif key == ord('c'):
            s.canvas[:] = 0
            s.drawing = False; s.last_pt = None; s.snap_canvas = None
        elif key == ord('b'):
            s.size_idx = (s.size_idx + 1) % len(BRUSH_SIZES)

    cap.release()
    detector.close()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()