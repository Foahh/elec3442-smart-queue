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
- Conda environment `elec3442`

## Setup — Development Machine

```bash
conda activate elec3442
cd smart-queue-estimator
uv sync --group dev
```

## Setup — Raspberry Pi 

```bash
# System packages
sudo apt update && sudo apt upgrade -y
sudo apt install python3-pip git -y

# Install uv
curl -LsSf https://astral.sh/uv/install.sh | sh

# Clone and enter project
git clone https://github.com/Foahh/elec3442-smart-queue && cd smart-queue-estimator

# Install core dependencies
uv sync

# Install Pi-only camera/HAT packages
uv pip install -r requirements-pi.txt

# Install NCNN export dependencies
pip install ultralytics[export]
```

## Prepare Model (Required Before Running)

Download and export the PyTorch model to NCNN format:

> imgsz: Desired image size for the model input. Can be an integer for square images or a tuple (height, width) for specific dimensions. See [Ultralytics YOLO NCNN Export](https://docs.ultralytics.com/integrations/ncnn/#installation)

```bash
# Using the provided export script
python scripts/export_model.py

# Or with custom options
python scripts/export_model.py --model yolo26n.pt --imgsz 640

# Or via Ultralytics CLI directly
yolo export model=models/yolo26n.pt format=ncnn imgsz=640
```

This creates `models/yolo26n_ncnn_model/`. The estimator runtime always loads
this NCNN directory.

### Benchmarking

Reproduce Ultralytics benchmarks on your device:

```bash
# Benchmark all formats
python scripts/benchmark.py

# Benchmark NCNN only
python scripts/benchmark.py --format ncnn

# Custom dataset and image size
python scripts/benchmark.py --data coco128.yaml --imgsz 640

# Or via Ultralytics CLI
yolo benchmark model=models/yolo26n.pt data=coco128.yaml imgsz=640
```

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

Raspberry Pi (PiCamera2 + Sense HAT + NCNN):

```bash
# Run export_model.py once first if NCNN dir does not exist.
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

## Testing

```bash
uv run pytest
```

## API Endpoints

| Method | Endpoint | Description |
| --- | --- | --- |
| GET | `/api/v1/queue/status` | In-memory current queue status |
| GET | `/api/v1/queue/history` | Snapshot history over time window |
| WS | `/api/v1/queue/live` | Live status stream for connected clients |
| GET | `/api/v1/analytics/summary` | Aggregated analytics for configurable period |
| GET | `/api/v1/analytics/peak-hours` | Top 3 busiest hours in last 7 days |
