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

- Python 3.13
- [uv](https://docs.astral.sh/uv/getting-started/installation/)

## Setup

```bash
git clone https://github.com/Foahh/elec3442-smart-queue
cd elec3442-smart-queue/pi

uv sync
```

This creates `.venv`, installs dependencies from `pyproject.toml`, and registers the `smart-queue` console script. Use `uv run smart-queue` or activate `.venv` and run `smart-queue` directly. After pulling dependency changes, run `uv sync` again.

### Raspberry Pi runtime (inference-only, NCNN)

This project is designed so the Raspberry Pi runs **inference only** using the
exported NCNN model directory at **`../models/yolo26n_ncnn_model/`** (repository root, sibling of `pi/`). Do YOLO export on a
development machine, then copy that directory onto the Pi.

Install PiCamera2 and Sense HAT into the same environment:

```bash
rm -rf .venv
uv venv --system-site-packages
uv sync --extra pi
```

Then run commands with `uv run` (see **Running**).

## Prepare Model (Required Before Running)

Follow **[Download and export YOLO → NCNN](../README.md#download-and-export-yolo--ncnn)** in the repository root README, then copy the generated `yolo26n_ncnn_model` folder into **`../models/`** at the repository root. The estimator runtime always loads that NCNN directory.

## Environment Configuration

Create `.env` in project root:

```env
QE_YOLO_MODEL=yolo26n.pt
QE_YOLO_CONFIDENCE=0.4
QE_YOLO_IOU=0.5
QE_YOLO_IMGSZ=640
QE_CAMERA_SOURCE=picamera
QE_CAMERA_INDEX=0
QE_CAMERA_VIDEO_PATH=
QE_CAMERA_WIDTH=1280
QE_CAMERA_HEIGHT=720
QE_CAMERA_FPS=10
QE_DATABASE_URL=sqlite:///data/queue.db
```

### Preview stream

| Variable | Description |
| --- | --- |
| `QE_PREVIEW_ENABLED` | Enable/disable preview frame encoding (default `true`). |
| `QE_PREVIEW_FPS` | Max preview encode FPS (default `5`). |
| `QE_PREVIEW_WIDTH` | Preview JPEG width (default `640`). |
| `QE_PREVIEW_HEIGHT` | Preview JPEG height (default `480`). |
| `QE_PREVIEW_JPEG_QUALITY` | JPEG quality \(0-100\) (default `70`). |

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

### Hub sync (web dashboard)

When `QE_HUB_URL` is non-empty, a background thread **pushes** local queue status to the web app and **pulls** peer sites for cross-site views.

| Variable | Description |
| --- | --- |
| `QE_HUB_URL` | Base URL of the deployed web project (e.g. `https://your-app.example.com`). Trailing slashes are fine. |
| `QE_HUB_API_KEY` | Shared secret; must match the web env **`API_KEY`** (sent as `X-Api-Key` on ingest). |
| `QE_SITE_ID` | Stable id for this edge node (stored and shown in the hub). |
| `QE_SITE_DISPLAY_NAME` | Human-readable site label. |
| `QE_SITE_LATITUDE` | Optional; included in ingest if set. |
| `QE_SITE_LONGITUDE` | Optional; included in ingest if set. |
| `QE_HUB_PUSH_INTERVAL` | Seconds between successful pushes (default `2.5`). Backoff increases on errors. |
| `QE_HUB_PULL_INTERVAL` | Seconds between successful pulls of `/api/sites` (default `2.5`). |

Endpoints (relative to `QE_HUB_URL`): **POST** `/api/ingest` (JSON body + `X-Api-Key`), **GET** `/api/sites` (public listing for the dashboard). If `QE_HUB_URL` is unset or empty, hub sync stays off.

Example fragment:

```env
QE_HUB_URL=https://queue-dashboard.example.com
QE_HUB_API_KEY=your-shared-secret
QE_SITE_ID=pi-lab-01
QE_SITE_DISPLAY_NAME=Lab queue camera
```

## Running

Development machine (video file):

```bash
QE_CAMERA_SOURCE=video QE_CAMERA_VIDEO_PATH=../video/queue_sample.mp4 \
uv run smart-queue
```

Raspberry Pi (PiCamera2 + Sense HAT + NCNN):

```bash
# If NCNN dir is missing, export per ../README.md then copy into ../models/.
QE_CAMERA_SOURCE=picamera uv run smart-queue
```

The edge node is headless by default. It keeps processing frames, storing local
history, and pushing snapshots to the web app when `QE_HUB_URL` is configured.
It also exposes a minimal local preview stream on `QE_API_HOST:QE_API_PORT`.

Sense HAT output requires Raspberry Pi packages (`uv sync --extra pi`).

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
