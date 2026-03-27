# Smart Queue Length & Wait Time Estimator (Backend)

Backend-only system for estimating queue length and wait time from camera feeds on Raspberry Pi or a development machine.

## Features

- YOLO + ByteTrack person detection/tracking
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

## Setup

```bash
conda activate elec3442
cd smart-queue-estimator
uv sync --extra dev
```

For Raspberry Pi hardware dependencies:

```bash
uv sync --extra pi
```

## Environment Configuration

Create `.env` in project root:

```env
QE_YOLO_MODEL=yolo26n.pt
QE_YOLO_CONFIDENCE=0.4
QE_YOLO_IOU=0.5
QE_CAMERA_SOURCE=webcam
QE_CAMERA_INDEX=0
QE_CAMERA_WIDTH=1280
QE_CAMERA_HEIGHT=720
QE_CAMERA_FPS=10
QE_DISPLAY_BACKEND=terminal
QE_DATABASE_URL=sqlite:///data/queue.db
```

## Running

Development machine (webcam + terminal display):

```bash
uv run queue-estimator
```

Raspberry Pi (PiCamera2 + Sense HAT):

```bash
QE_CAMERA_SOURCE=picamera QE_DISPLAY_BACKEND=sensehat uv run queue-estimator
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

