# Smart Queue Length & Wait Time Estimator

Backend system for estimating queue length and wait time from camera feeds on Raspberry Pi or a development machine.

## Features

- YOLO26 (w/ NCNN model format) + ByteTrack person detection/tracking
- Configurable polygon queue zone filtering
- Real-time queue state and rolling wait-time estimation
- SQLite persistence via SQLModel
- FastAPI HTTP + WebSocket API
- Sense HAT display support with terminal fallback
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

**Raspberry Pi:** install `git` (and pip) if needed, then Pi-only camera/HAT wheels:

```bash
sudo apt update && sudo apt upgrade -y
sudo apt install python3-pip git -y
uv pip install -r requirements-pi.txt
```

Use `uv run …` for commands so the project environment is used (see **Running**).

## Prepare Model (Required Before Running)

Export the PyTorch model to NCNN format:

> imgsz: Desired image size for the model input. Can be an integer for square images or a tuple (height, width) for specific dimensions. See [Ultralytics YOLO NCNN Export](https://docs.ultralytics.com/integrations/ncnn/#installation)

```bash
# Export a YOLO26n PyTorch model to NCNN format
uv run yolo export model=yolo26n.pt format=ncnn # creates 'yolo26n_ncnn_model'

# Run inference with the exported model
uv run yolo predict model='yolo26n_ncnn_model' source='https://ultralytics.com/images/bus.jpg'

# Benchmark YOLO26n speed and accuracy on the COCO128 dataset for all export formats
uv run yolo benchmark model=yolo26n.pt data=coco128.yaml imgsz=640
```

This creates `models/yolo26n_ncnn_model/`. The estimator runtime always loads
this NCNN directory.

## Environment Configuration

Create `.env` in project root:

```env
QE_YOLO_MODEL=yolo26n.pt
QE_YOLO_CONFIDENCE=0.4
QE_YOLO_IOU=0.5
QE_YOLO_IMGSZ=640
QE_CAMERA_SOURCE=webcam
QE_CAMERA_INDEX=0
QE_CAMERA_WIDTH=1280
QE_CAMERA_HEIGHT=720
QE_CAMERA_FPS=10
QE_DISPLAY_BACKEND=terminal
QE_DATABASE_URL=sqlite:///data/queue.db
```

For Raspberry Pi deployment:

```env
QE_YOLO_MODEL=yolo26n.pt
QE_CAMERA_SOURCE=picamera
QE_CAMERA_WIDTH=1280
QE_CAMERA_HEIGHT=720
QE_CAMERA_FPS=10
QE_DISPLAY_BACKEND=sensehat
QE_DATABASE_URL=sqlite:///data/queue.db
```

## Running

Development machine (webcam + terminal display):

```bash
uv run queue-estimator
```

Development machine with Sense HAT emulation:

```bash
QE_DISPLAY_BACKEND=sensehat uv run queue-estimator
```

This uses `sense-emu` and opens the emulator UI on the host machine.

Raspberry Pi (PiCamera2 + Sense HAT + NCNN):

```bash
# Run yolo export once first if NCNN dir does not exist.
QE_CAMERA_SOURCE=picamera QE_DISPLAY_BACKEND=sensehat uv run queue-estimator
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
