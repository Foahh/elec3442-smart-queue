# Smart Queue Length & Wait Time Estimator

Backend system for estimating queue length and wait time from camera feeds on Raspberry Pi or a development machine.

## Features

- YOLO26 (w/ NCNN model format) + ByteTrack person detection/tracking
- Configurable polygon queue zone filtering
- Real-time queue state and rolling wait-time estimation
- SQLite persistence via SQLModel
- Hub push/pull sync with the web project
- Lightweight local HTTP preview stream
- Sense HAT display output
- Structured logging with Loguru

## Requirements

- Python 3.14 (see `environment.yml`)
- [Conda](https://docs.conda.io/projects/conda/en/stable/user-guide/install/index.html)

## Setup

```bash
git clone https://github.com/Foahh/elec3442-smart-queue
cd elec3442-smart-queue/pi

conda env create -f environment.yml
conda activate elec3442
```

The last pip line in `environment.yml` (`-e .`) installs this repo and registers the `queue-estimator` command. If you see `command not found`, run `pip install -e .` from this directory (or `conda env update -f environment.yml --prune` after pulling changes).

### Raspberry Pi runtime (inference-only, NCNN)

This project is designed so the Raspberry Pi runs **inference only** using the
exported NCNN model directory (`models/yolo26n_ncnn_model/`). Do YOLO export on a
development machine, then copy that directory onto the Pi.

Install Pi runtime dependencies (PiCamera2 + Sense HAT) into the active environment:

```bash
conda activate elec3442
pip install -r requirements.txt
```

After `conda activate elec3442`, run commands in that environment (see **Running**).

## Prepare Model (Required Before Running)

Follow **[Download and export YOLO → NCNN](../README.md#download-and-export-yolo--ncnn)** in the repository root README, then copy the generated `yolo26n_ncnn_model` folder into this project’s `models/` directory. The estimator runtime always loads that NCNN directory.

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
QE_CAMERA_VIDEO_PATH=../video/queue_sample.mp4
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
conda activate elec3442
queue-estimator
```

Raspberry Pi (PiCamera2 + Sense HAT + NCNN):

```bash
# If NCNN dir is missing, export per ../README.md then copy models/.
QE_CAMERA_SOURCE=picamera queue-estimator
```

The edge node is headless by default. It keeps processing frames, storing local
history, and pushing snapshots to the web app when `QE_HUB_URL` is configured.
It also exposes a minimal local preview stream on `QE_API_HOST:QE_API_PORT`.

Sense HAT output requires Raspberry Pi packages:

```bash
pip install -r requirements.txt
```

### Camera Test (Pi)

Verify the camera works before starting the estimator:

```bash
# Quick 5-second preview (requires display or VNC)
rpicam-hello

# Headless capture test
rpicam-still -o test.jpg && echo "Camera OK"
```

## Preview Endpoint

The node always starts a minimal local preview server on `QE_API_HOST:QE_API_PORT`.

| Method | Endpoint | Description |
| --- | --- | --- |
| GET | `/preview` | MJPEG video preview stream |
