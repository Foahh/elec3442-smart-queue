# Smart Queue Length & Wait Time Estimator

Backend system for estimating queue length and wait time from camera feeds on Raspberry Pi or a development machine.

## Features

- YOLO26 (w/ NCNN model format) + ByteTrack person detection/tracking
- Configurable polygon queue zone filtering
- Real-time queue state and rolling wait-time estimation
- SQLite persistence via SQLModel
- FastAPI HTTP + WebSocket API
- Sense HAT display output
- Structured logging with Loguru

## Requirements

- Python 3.14 (pinned by `.python-version`)
- `uv` package manager

## Setup

Install [`uv`](https://docs.astral.sh/uv/getting-started/installation/) if you do not have it yet.

```bash
git clone https://github.com/Foahh/elec3442-smart-queue
cd elec3442-smart-queue/smart-queue-estimator

uv python install 3.14
uv sync
```

**Raspberry Pi dependency group:**

```bash
sudo apt update && sudo apt upgrade -y
sudo apt install python3-pip git -y
uv sync --group pi
```

Use `uv run …` for commands so the project environment is used (see **Running**).

## Prepare Model (Required Before Running)

Follow **[yolo-export/README.md](../yolo-export/README.md)**, then copy the generated `yolo26n_ncnn_model` folder into this project’s `models/` directory. The estimator runtime always loads that NCNN directory.

## Environment Configuration

Create `.env` in project root:

```env
QE_YOLO_MODEL=yolo26n.pt
QE_YOLO_CONFIDENCE=0.4
QE_YOLO_IOU=0.5
QE_YOLO_IMGSZ=640
QE_CAMERA_SOURCE=webcam
QE_CAMERA_INDEX=0
QE_CAMERA_VIDEO_PATH=
QE_CAMERA_WIDTH=1280
QE_CAMERA_HEIGHT=720
QE_CAMERA_FPS=10
QE_DATABASE_URL=sqlite:///data/queue.db
```

Use local video file as input (development/testing):

```env
QE_CAMERA_SOURCE=video
QE_CAMERA_VIDEO_PATH=D:/path/to/queue_sample.mp4
QE_DATABASE_URL=sqlite:///data/queue.db
```

For Raspberry Pi deployment:

```env
QE_YOLO_MODEL=yolo26n.pt
QE_CAMERA_SOURCE=picamera
QE_CAMERA_WIDTH=1280
QE_CAMERA_HEIGHT=720
QE_CAMERA_FPS=10
QE_DATABASE_URL=sqlite:///data/queue.db
```

## Running

Development machine (webcam):

```bash
uv run queue-estimator
```

Raspberry Pi (PiCamera2 + Sense HAT + NCNN):

```bash
# Run yolo export once first if NCNN dir does not exist.
QE_CAMERA_SOURCE=picamera uv run queue-estimator
```

Sense HAT output requires Raspberry Pi dependencies:

```bash
uv sync --group pi
```

### Camera Test (Pi)

Verify the camera works before starting the estimator:

```bash
# Quick 5-second preview (requires display or VNC)
rpicam-hello

# Headless capture test
rpicam-still -o test.jpg && echo "Camera OK"
```

## API Endpoints

| Method | Endpoint | Description |
| --- | --- | --- |
| GET | `/api/v1/queue/status` | In-memory current queue status |
| GET | `/api/v1/queue/history` | Snapshot history over time window |
| WS | `/api/v1/queue/live` | Live status stream for connected clients |
| GET | `/api/v1/analytics/summary` | Aggregated analytics for configurable period |
| GET | `/api/v1/analytics/peak-hours` | Top 3 busiest hours in last 7 days |
