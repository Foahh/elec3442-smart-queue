# elec3442-smart-queue

Queue length and wait-time estimation from camera feeds. The runnable application lives in **[smart-queue-estimator](smart-queue-estimator/)** — see that README for setup, configuration, and API details.

## Download and export YOLO → NCNN

The estimator loads an **NCNN** export for inference. Ultralytics’ export stack pulls in **`ultralytics[export]`**, which pins **NumPy below 2.x**, while **smart-queue-estimator** uses **NumPy 2** (needed by current OpenCV wheels). Use a **separate conda environment** only for exporting; do not install export extras into `elec3442`.

### 1. Create an export-only environment

From the repository root:

```bash
conda create -n elec3442-export python=3.12 -y
conda activate elec3442-export
pip install "ultralytics[export]"
```

### 2. Obtain weights and export

Download a YOLO `.pt` checkpoint (for example `yolo26n.pt` from [Ultralytics](https://docs.ultralytics.com/) / the CLI will fetch models it knows about). Then:

```bash
yolo export model=yolo26n.pt format=ncnn
```

**`imgsz`:** Use an integer for square input or `(height, width)` for explicit dimensions. See [Ultralytics NCNN export](https://docs.ultralytics.com/integrations/ncnn/#installation).

Copy the generated folder into the estimator’s `models/` directory, for example:

`smart-queue-estimator/models/yolo26n_ncnn_model/`

### 3. Optional checks (estimator / NumPy 2 stack)

After copying the NCNN folder, from **smart-queue-estimator** with `conda activate elec3442`:

```bash
cd smart-queue-estimator
yolo predict model='models/yolo26n_ncnn_model' source='https://ultralytics.com/images/bus.jpg'
yolo benchmark model=yolo26n.pt data=coco128.yaml imgsz=640
```
