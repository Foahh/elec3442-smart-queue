# elec3442-smart-queue

Queue length and wait-time estimation from camera feeds. The runnable application lives in **[pi](pi/)** — see that README for setup, configuration, and API details.

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

`pi/models/yolo26n_ncnn_model/`

### 3. Optional checks (estimator / NumPy 2 stack)

After copying the NCNN folder, from **pi** with `conda activate elec3442`:

```bash
cd pi
yolo predict model='models/yolo26n_ncnn_model' source='https://ultralytics.com/images/bus.jpg'
yolo benchmark model=yolo26n.pt data=coco128.yaml imgsz=640
```

## CrowdHuman workflow

The CrowdHuman pipeline is split into two standalone scripts:
- [download_dataset.py](/home/fn/elec3442-smart-queue/download_dataset.py) downloads CrowdHuman from Hugging Face and exports YOLO labels
- [finetune_yolo26.py](/home/fn/elec3442-smart-queue/finetune_yolo26.py) finetunes YOLO26 and optionally exports NCNN artifacts

Typical usage:

```bash
export HF_TOKEN=...
python download_dataset.py
python finetune_yolo26.py
```

Defaults:
- dataset root: `./datasets/crowdhuman_person` or `$DATASETS_DIR/crowdhuman_person`
- pretrained weights: `yolo26n.pt`
- training output: `results/crowdhuman_yolo26n/`
