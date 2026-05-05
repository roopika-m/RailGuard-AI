
# 🚆 RailGuard AI — Railway Safety System

Real-time human & animal detection on a virtual railway track zone using YOLOv8 + OpenCV + pygame.

---

## Problem Statement

Railway tracks are vulnerable to accidents caused by humans or animals entering restricted zones. Existing monitoring systems are often manual or lack real-time alert capabilities.

RailGuard AI aims to provide an automated, real-time detection and alert system to improve railway safety and reduce potential accidents.

---

## How It Works

1. Captures live video stream from webcam or input video
2. Uses YOLOv8 model to detect humans and animals in real time
3. Checks whether detected objects fall inside a defined virtual track zone
4. Confirms detection across multiple frames to avoid false alerts
5. Triggers alert (visual + sound) and saves a snapshot when detection occurs

---

## ⚡ Quick Start

### 1. Prerequisites

- Python 3.8 or higher
- A working webcam (or an `.mp4` test video)

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

> YOLOv8 (`yolov8n.pt`, ~6 MB) is downloaded automatically on the first run.

### 3. Add alert sounds (optional but recommended)

Place these two files in the same folder as `railguard_ai.py`:

| File | Triggered when |
|------|---------------|
| `human_alert.mp3` | A person enters the track zone |
| `animal_alert.mp3` | An animal enters the track zone |

Free sources: [Pixabay](https://pixabay.com), [Freesound](https://freesound.org).

> If the files are missing the system still works — alerts display on screen, just silently.

### 4. Run

```bash
# Webcam (default)
python railguard_ai.py

# Specific webcam index
python railguard_ai.py --source 1

# Video file
python railguard_ai.py --source test_video.mp4
```

Press **Q** inside the window to quit.

---

## Output Screenshots

### Human Detection
![Human Detection] Human.jpg

### Animal Detection
![Animal Detection] cow.jpg,

### Alert Snapshot
![Alert Snapshot](images/alert_snapshot.png)



---

## 🖥️ What You'll See

```
┌──────────────────────────────────────────────────┐
│ ⚠  Human on Track!          FPS: 28.3 | RailGuard AI │
│                                                       │
│          ┌─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─┐                │
│          │   TRACK ZONE (gold box)  │                │
│          │   [person 87%]           │                │
│          │                          │                │
│          └─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─┘                │
└──────────────────────────────────────────────────┘
```

| Colour | Meaning |
|--------|---------|
| 🟡 Gold rectangle | Virtual track zone |
| 🔴 Red box | Human (person) detected |
| 🟢 Green box | Animal detected |

---

## ⚙️ Configuration (`railguard_ai.py` top section)

| Variable | Default | Description |
|----------|---------|-------------|
| `MODEL_NAME` | `yolov8n.pt` | Swap to `yolov8s.pt` for better accuracy |
| `CONFIDENCE_THRESHOLD` | `0.50` | Minimum detection confidence (0–1) |
| `ALERT_COOLDOWN` | `10 s` | Pause between repeated alerts |
| `MULTI_FRAME_CONFIRM` | `3 frames` | Frames before first alert fires |
| `ZONE` | `(0.25, 0.30, 0.75, 0.85)` | Track zone as fractions of frame |
| `ANIMAL_CLASSES` | `dog, cat, horse …` | Extend with any COCO class name |

### Adjusting the Track Zone

`ZONE = (left, top, right, bottom)` — values are fractions of frame width/height.

**Example:** `(0.3, 0.4, 0.7, 0.9)` → a narrower, lower zone.

---

## 📁 Output

| Path | Contents |
|------|----------|
| `snapshots/` | JPEG snapshots saved at the moment of each alert |

---

## 🧩 YOLO Model Options

| Model | Size | Speed | Accuracy |
|-------|------|-------|----------|
| `yolov8n.pt` | 6 MB | ⚡⚡⚡⚡ | ★★☆☆ |
| `yolov8s.pt` | 22 MB | ⚡⚡⚡ | ★★★☆ |
| `yolov8m.pt` | 52 MB | ⚡⚡ | ★★★★ |
| `yolov8l.pt` | 87 MB | ⚡ | ★★★★ |

Change `MODEL_NAME` at the top of `railguard_ai.py`.

---

## 🛠️ Troubleshooting

| Problem | Fix |
|---------|-----|
| `No module named 'ultralytics'` | `pip install ultralytics` |
| Webcam not opening | Try `--source 1` or `--source 2` |
| Low FPS | Use `yolov8n.pt`; reduce frame resolution |
| Sound not playing | Confirm `.mp3` files are in the same folder |
| `pygame.error` on init | Install pygame: `pip install pygame` |

---

## 📜 Detected Animal Classes (COCO)

`dog` · `cat` · `horse` · `sheep` · `cow` · `elephant` · `bear` · `zebra` · `giraffe` · `bird`

Add more from the [COCO class list](https://cocodataset.org/) by editing `ANIMAL_CLASSES` in the script.

---

## Future Scope

- Integrate Flask API for remote monitoring and control
- Build a web dashboard for real-time alerts and system status
- Support multiple camera feeds across railway stations
- Deploy on edge devices for real-world railway environments
- Improve detection accuracy using advanced models and dataset tuning

---

## About

**RailGuard AI** detects humans and animals on railway tracks in real time and triggers alerts to improve safety.

**Resources:** [README](#) · Activity · Stars · Forks

**Contributors:** [@roopika-m](https://github.com/roopika-m)

**Languages:** Python 100%
