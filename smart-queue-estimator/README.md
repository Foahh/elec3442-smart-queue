# Smart Queue Length & Wait Time Estimator (Backend)

Backend-only system for estimating queue length and wait time from camera feeds on Raspberry Pi or a development machine.

## Features

- YOLO26 + ByteTrack person detection/tracking
- First-class NCNN model support for Raspberry Pi 5 (4.5x faster than PyTorch)
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
uv sync --extra dev
```

## Setup — Raspberry Pi 5 (without Docker)

Tested on Raspberry Pi OS Bookworm (Debian 12), 64-bit Lite.

```bash
# System packages
sudo apt update && sudo apt upgrade -y
sudo apt install python3-pip git -y

# Install uv
curl -LsSf https://astral.sh/uv/install.sh | sh

# Clone and enter project
git clone <your-repo-url> && cd smart-queue-estimator

# Install with Pi extras
uv sync --extra pi

# Install NCNN export dependencies (one-time, on Pi or dev machine)
pip install ultralytics[export]
```

### Pi 5 Best Practices

| Practice | Detail |
| --- | --- |
| **Use an NVMe SSD** | SD cards wear out under 24/7 writes. Use a PCIe NVMe adapter (e.g. Pimoroni NVMe Base). |
| **Flash Raspberry Pi OS Lite** | Skip the desktop environment to free ~400 MB RAM for inference. |
| **Overclock cautiously** | CPU up to 2.9 GHz, GPU to 1.0 GHz via `/boot/firmware/config.txt`. Requires active cooling. Reduce by 100 MHz if unstable. |
| **Active cooling** | The official Pi 5 Active Cooler or a heatsink+fan is required under sustained YOLO inference workloads. |
| **Use NCNN format** | NCNN is ~4.5x faster than PyTorch on Pi 5 ARM CPU (68 ms vs 302 ms per frame at 640px). |
| **Prefer yolo26n** | The nano variant is the only practical choice for real-time use on Pi 5. |

## Model Format Selection

This project supports two model formats:

| Format | Config value | When to use |
| --- | --- | --- |
| **PyTorch** (`.pt`) | `QE_YOLO_MODEL_FORMAT=pt` (default) | Development, GPU machines, quick prototyping |
| **NCNN** | `QE_YOLO_MODEL_FORMAT=ncnn` | Raspberry Pi 5 deployment (recommended) |

### NCNN Export Workflow

Export the PyTorch model to NCNN format (run once, on Pi or dev machine):

```bash
# Using the provided export script
python scripts/export_model.py

# Or with custom options
python scripts/export_model.py --model yolo26n.pt --imgsz 640

# Or via Ultralytics CLI directly
yolo export model=models/yolo26n.pt format=ncnn imgsz=640
```

This creates `models/yolo26n_ncnn_model/`. Then switch the runtime:

```bash
# In .env
QE_YOLO_MODEL_FORMAT=ncnn
```

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

Expected Pi 5 results for yolo26n (from Ultralytics docs):

| Format | Inference (ms/frame) | mAP50-95 |
| --- | --- | --- |
| PyTorch | 302 | 0.480 |
| NCNN | 68 | 0.481 |
| ONNX | 130 | 0.476 |

## Environment Configuration

Create `.env` in project root:

```env
QE_YOLO_MODEL=yolo26n.pt
QE_YOLO_MODEL_FORMAT=pt
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

For Raspberry Pi 5 deployment:

```env
QE_YOLO_MODEL=yolo26n.pt
QE_YOLO_MODEL_FORMAT=ncnn
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
QE_CAMERA_SOURCE=picamera QE_DISPLAY_BACKEND=sensehat QE_YOLO_MODEL_FORMAT=ncnn uv run queue-estimator
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

## Python Version Compatibility Note

This project pins Python 3.14. On Raspberry Pi OS Bookworm the system Python
is 3.11. Use `uv` which manages its own Python toolchain, or install 3.14 via
`pyenv`. If dependency issues arise on Pi, Python 3.11–3.13 are safe fallback
targets — adjust `.python-version` and `requires-python` in `pyproject.toml`.
