# YOLO → NCNN export

Export Ultralytics YOLO weights to NCNN for the [smart-queue-estimator](../smart-queue-estimator/) runtime.

The estimator app uses **NumPy 2** (required by recent `opencv-python-headless`). **`ultralytics[export]` pins NumPy below 2.x**, so export must **not** use the same `uv` environment as the estimator. This directory is a dedicated export stack.

## Setup

From the repository root:

```bash
cd yolo-export
uv python install 3.12
uv sync
```

Use `uv run …` so this project’s virtual environment is used.

## Export to NCNN

> **imgsz:** Desired image size for the model input. Use an integer for square images or a tuple `(height, width)` for specific dimensions. See [Ultralytics YOLO NCNN export](https://docs.ultralytics.com/integrations/ncnn/#installation).

```bash
uv run yolo export model=yolo26n.pt format=ncnn
```

Copy the resulting folder into the estimator’s `models/` directory (e.g. `../smart-queue-estimator/models/yolo26n_ncnn_model/`).

## Optional checks

From **smart-queue-estimator** (runtime / NumPy 2 stack), after copying the NCNN folder:

```bash
cd ../smart-queue-estimator
uv run yolo predict model='models/yolo26n_ncnn_model' source='https://ultralytics.com/images/bus.jpg'
uv run yolo benchmark model=yolo26n.pt data=coco128.yaml imgsz=640
```
