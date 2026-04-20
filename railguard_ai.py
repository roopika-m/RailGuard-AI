"""
╔══════════════════════════════════════════════════╗
║           RailGuard AI - Railway Safety System          ║
║   Real-time Human & Animal Detection on Track Zone      ║
╚══════════════════════════════════════════════════╝

Author  : RailGuard AI
Version : 1.1.0  (winsound edition — no pygame required)
Requires: Python 3.8+, ultralytics, opencv-python

Run:
    python railguard_ai.py
    python railguard_ai.py --source 0          # webcam (default)
    python railguard_ai.py --source video.mp4  # video file
"""

import cv2
import winsound          # ✅ Built-in on Windows — no install needed
import threading         # Play beeps in background so video doesn't freeze
import time
import os
import argparse
from datetime import datetime
from ultralytics import YOLO
import pyttsx3

# ─────────────────────────────────────────────
#  CONFIGURATION  (edit freely)
# ─────────────────────────────────────────────

# YOLO model — 'yolov8n.pt' downloads automatically on first run (~6 MB)
# Upgrade to 'yolov8s.pt' or 'yolov8m.pt' for better accuracy
MODEL_NAME = "yolov8n.pt"

# Minimum confidence to accept a detection (0–1)
CONFIDENCE_THRESHOLD = 0.50

# Cooldown between alerts for the same category (seconds)
ALERT_COOLDOWN = 10

# Number of consecutive frames an object must appear before triggering an alert
MULTI_FRAME_CONFIRM = 3

# Track zone as fractions of frame size  (left, top, right, bottom)
# 0.0 = leftmost/topmost edge, 1.0 = rightmost/bottommost edge
ZONE = (0.25, 0.30, 0.75, 0.85)

# Snapshot folder
SNAPSHOT_DIR = "snapshots"

# YOLO class names that count as "animal"
ANIMAL_CLASSES = {"dog", "cat", "horse", "sheep", "cow", "elephant",
                  "bear", "zebra", "giraffe", "bird"}

# Drawing colours  (BGR)
COLOR_HUMAN   = (0,   0,   220)   # Red
COLOR_ANIMAL  = (0,   200,  0)    # Green
COLOR_ZONE    = (0,   215, 255)   # Gold
COLOR_ALERT   = (0,   0,   255)   # Red text

# ─────────────────────────────────────────────
#  SOUND MANAGER  (winsound — Windows built-in)
# ─────────────────────────────────────────────


class SoundManager:
    """
    Plays system beeps (winsound) + offline voice alerts (pyttsx3).
    Both run in background threads — video loop is never blocked.
    A single lock prevents overlapping audio.
    """

    BEEP_PROFILES = {
        "human":  (1500, 600),
        "animal": ( 800, 600),
    }

    VOICE_MESSAGES = {
        "human":  "Warning. Human detected on track.",
        "animal": "Warning. Animal detected on track.",
    }

    def __init__(self):
        self._lock = threading.Lock()

        # Initialise pyttsx3 engine once — reused across calls
        self._tts = pyttsx3.init()
        self._tts.setProperty("rate", 160)    # words per minute
        self._tts.setProperty("volume", 1.0)  # 0.0 – 1.0

        print("[Sound] winsound (beep) + pyttsx3 (voice) ready.")
        print(f"[Sound] human  → {self.BEEP_PROFILES['human'][0]} Hz | '{self.VOICE_MESSAGES['human']}'")
        print(f"[Sound] animal → {self.BEEP_PROFILES['animal'][0]} Hz | '{self.VOICE_MESSAGES['animal']}'")

    def play(self, key: str):
        """
        Fire beep + voice for the given category key.
        Skipped silently if audio is already playing.
        """
        if self._lock.locked():
            return

        beep_profile  = self.BEEP_PROFILES.get(key)
        voice_message = self.VOICE_MESSAGES.get(key)

        if beep_profile is None or voice_message is None:
            return

        freq, duration = beep_profile

        def _alert():
            with self._lock:
                # Beep first (short), then voice
                winsound.Beep(freq, duration)
                self._tts.say(voice_message)
                self._tts.runAndWait()

        t = threading.Thread(target=_alert, daemon=True)
        t.start()

# ─────────────────────────────────────────────
#  ALERT TRACKER  (cooldown + multi-frame confirm)
# ─────────────────────────────────────────────

class AlertTracker:
    """Manages per-category cooldowns and consecutive-frame confirmation."""

    def __init__(self):
        self._last_alert: dict[str, float] = {}   # category → timestamp
        self._frame_count: dict[str, int]  = {}   # category → consecutive frames

    def register(self, category: str) -> bool:
        """
        Call once per frame for each detected category.
        Returns True when an alert should fire.
        """
        now = time.time()
        self._frame_count[category] = self._frame_count.get(category, 0) + 1

        # Not yet confirmed over enough frames
        if self._frame_count[category] < MULTI_FRAME_CONFIRM:
            return False

        # Still in cooldown window
        last = self._last_alert.get(category, 0)
        if now - last < ALERT_COOLDOWN:
            return False

        # ✅ Fire alert
        self._last_alert[category] = now
        return True

    def reset(self, category: str):
        """Call when the category disappears from the zone."""
        self._frame_count[category] = 0

# ─────────────────────────────────────────────
#  HELPERS
# ─────────────────────────────────────────────

def get_zone_px(frame_w: int, frame_h: int) -> tuple[int, int, int, int]:
    """Convert fractional zone to pixel coordinates."""
    x1 = int(ZONE[0] * frame_w)
    y1 = int(ZONE[1] * frame_h)
    x2 = int(ZONE[2] * frame_w)
    y2 = int(ZONE[3] * frame_h)
    return x1, y1, x2, y2


def box_in_zone(bx1, by1, bx2, by2, zx1, zy1, zx2, zy2) -> bool:
    """Return True if the detected box overlaps the track zone."""
    return not (bx2 < zx1 or bx1 > zx2 or by2 < zy1 or by1 > zy2)


def draw_zone(frame, zx1, zy1, zx2, zy2):
    """Draw a semi-transparent filled rectangle for the track zone."""
    overlay = frame.copy()
    cv2.rectangle(overlay, (zx1, zy1), (zx2, zy2), COLOR_ZONE, -1)
    cv2.addWeighted(overlay, 0.12, frame, 0.88, 0, frame)   # subtle fill
    cv2.rectangle(frame, (zx1, zy1), (zx2, zy2), COLOR_ZONE, 2)

    label = "TRACK ZONE"
    cv2.putText(frame, label, (zx1 + 6, zy1 - 8),
                cv2.FONT_HERSHEY_SIMPLEX, 0.55, COLOR_ZONE, 2)


def draw_box(frame, x1, y1, x2, y2, label: str, conf: float, color: tuple):
    """Draw bounding box with label + confidence score."""
    cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)

    text  = f"{label}  {conf:.0%}"
    (tw, th), _ = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, 0.55, 2)
    cv2.rectangle(frame, (x1, y1 - th - 8), (x1 + tw + 6, y1), color, -1)
    cv2.putText(frame, text, (x1 + 3, y1 - 5),
                cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 255, 255), 2)


def draw_alert(frame, message: str):
    """Overlay a prominent alert banner at the top of the frame."""
    h, w = frame.shape[:2]

    overlay = frame.copy()
    cv2.rectangle(overlay, (0, 0), (w, 56), (0, 0, 0), -1)
    cv2.addWeighted(overlay, 0.65, frame, 0.35, 0, frame)

    (tw, th), _ = cv2.getTextSize(message, cv2.FONT_HERSHEY_DUPLEX, 1.0, 2)
    tx = (w - tw) // 2
    cv2.putText(frame, message, (tx, 40),
                cv2.FONT_HERSHEY_DUPLEX, 1.0, COLOR_ALERT, 2)


def save_snapshot(frame):
    """Save a timestamped JPEG snapshot of the alert frame."""
    os.makedirs(SNAPSHOT_DIR, exist_ok=True)
    ts   = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    path = os.path.join(SNAPSHOT_DIR, f"alert_{ts}.jpg")
    cv2.imwrite(path, frame)
    print(f"[Snapshot] Saved → {path}")


def draw_hud(frame, fps: float):
    """Draw a small HUD in the top-right corner with FPS."""
    h, w = frame.shape[:2]
    txt = f"FPS: {fps:5.1f}  |  RailGuard AI"
    cv2.putText(frame, txt, (w - 310, 24),
                cv2.FONT_HERSHEY_SIMPLEX, 0.55, (200, 200, 200), 1)

# ─────────────────────────────────────────────
#  MAIN LOOP
# ─────────────────────────────────────────────

def main(source):
    print("\n╔══════════════════════════════════╗")
    print("║       RailGuard AI Starting       ║")
    print("╚══════════════════════════════════╝\n")

    print(f"[Model] Loading {MODEL_NAME} ...")
    model = YOLO(MODEL_NAME)
    print("[Model] Ready.\n")

    sound   = SoundManager()
    tracker = AlertTracker()

    cap = cv2.VideoCapture(int(source) if source.isdigit() else source)
    if not cap.isOpened():
        print(f"[Error] Cannot open source: {source}")
        return

    prev_time = time.time()
    frame_idx = 0

    print("\n[Stream] Running — press  Q  to quit.\n")

    while True:
        ret, frame = cap.read()
        if not ret:
            print("[Stream] End of stream.")
            break

        frame_idx += 1
        h, w = frame.shape[:2]

        # ── Zone in pixels ──────────────────────────────
        zx1, zy1, zx2, zy2 = get_zone_px(w, h)
        draw_zone(frame, zx1, zy1, zx2, zy2)

        # ── YOLO inference ──────────────────────────────
        results = model(frame, verbose=False)[0]

        active_categories: set[str] = set()
        alert_messages:    list[str] = []

        for det in results.boxes:
            conf = float(det.conf[0])
            if conf < CONFIDENCE_THRESHOLD:
                continue

            class_id   = int(det.cls[0])
            class_name = model.names[class_id].lower()

            if class_name == "person":
                category = "human"
                color    = COLOR_HUMAN
            elif class_name in ANIMAL_CLASSES:
                category = "animal"
                color    = COLOR_ANIMAL
            else:
                continue

            x1, y1, x2, y2 = map(int, det.xyxy[0])

            # ── Zone check ──────────────────────────────
            in_zone = box_in_zone(x1, y1, x2, y2, zx1, zy1, zx2, zy2)
            if in_zone:
                active_categories.add(category)

            draw_box(frame, x1, y1, x2, y2, class_name, conf, color)

        # ── Alert logic ─────────────────────────────────
        for cat in ("human", "animal"):
            if cat in active_categories:
                should_alert = tracker.register(cat)
                if should_alert:
                    msg = "⚠  Human on Track!" if cat == "human" else "⚠  Animal on Track!"
                    alert_messages.append(msg)
                    sound.play(cat)          # winsound.Beep on background thread
                    save_snapshot(frame)
                    print(f"[ALERT] {msg}  (frame {frame_idx})")
            else:
                tracker.reset(cat)

        # Show alert banner while object is in zone
        for cat in active_categories:
            msg = "⚠  Human on Track!" if cat == "human" else "⚠  Animal on Track!"
            draw_alert(frame, msg)
            break  # one banner at a time; human takes priority

        # ── HUD ─────────────────────────────────────────
        now  = time.time()
        fps  = 1.0 / max(now - prev_time, 1e-6)
        prev_time = now
        draw_hud(frame, fps)

        # ── Display ─────────────────────────────────────
        cv2.imshow("RailGuard AI", frame)
        if cv2.waitKey(1) & 0xFF == ord("q"):
            print("[Stream] Quit requested.")
            break

    cap.release()
    cv2.destroyAllWindows()
    print("[Done] RailGuard AI stopped.")


# ─────────────────────────────────────────────
#  ENTRY POINT
# ─────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="RailGuard AI — Railway Safety System")
    parser.add_argument(
        "--source", default="0",
        help="Video source: '0' for webcam, or path to a video file (default: 0)"
    )
    args = parser.parse_args()
    main(args.source)
