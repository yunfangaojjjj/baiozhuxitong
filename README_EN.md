English | [中文](README.md)

# YOLOE + SAM Auto-Labeling System

A desktop image annotation tool (PyQt6) built on [Ultralytics YOLOE](https://docs.ultralytics.com/) and [SAM 2](https://docs.ultralytics.com/models/sam-2/). It supports fully automatic YOLOE prediction, visual-prompt batch labeling, and interactive SAM polygon annotation, with export to YOLO detection / segmentation / pose labels.

## Features

**Auto-labeling**
- One-click prediction of boxes, segmentation masks or keypoints with a YOLOE model
- Visual Prompt: box a target as a prompt and YOLOE finds similar objects across the image; after caching the VPE, run "similar-label auto-labeling" over an entire folder

**AI interactive segmentation**
- SAM / SAM 2 / MobileSAM powered AI polygon: left-click adds foreground points, right-click adds background points, with a live mask preview
- Masks are simplified into polygons (Douglas-Peucker + maximum vertex count); on confirmation they become Seg annotations and are saved automatically
- Supports SAM 2, SAM 2.1 and MobileSAM weights; image features are cached, so extra clicks only run the mask decoder

**Batch inference**
- Run any YOLO detection, segmentation or pose model over a folder and write same-name YOLO labels
- Adjustable confidence and IoU thresholds, confirmation before overwriting existing labels, `classes.txt` updated after completion

**Editing and export**
- Draw, move, resize and nudge boxes with the arrow keys; delete / clear / edit class and confidence
- Render boxes, pose skeletons (with per-class radial connection rules) and segmentation polygons on the same canvas
- Export single images or batches to YOLO detection / pose / seg format

**Datasets and formats**
- Split images and labels into train / val / test; unlabeled images go to `blank`; generates the YOLO directory layout
- Convert Labelme JSON ↔ YOLO-seg TXT and YOLO detection TXT ↔ generic JSON

## Requirements

- Python 3.8+
- PyTorch (a CUDA build is recommended for NVIDIA GPUs)
- ultralytics (with YOLOE / SAM 2 support)

## Installation

```bash
pip install -r requirements.txt
```

`requirements.txt` includes: PyQt6, numpy, opencv-python, pillow, torch, torchvision, ultralytics, pyyaml.

## Model weights

Model weights are large and **not included in this repository** (`models/` and `*.pt` are gitignored). Prepare them yourself:

| Purpose | Location | Notes |
| --- | --- | --- |
| YOLOE auto-labeling / visual prompts | Any path | Select the YOLOE weights (`.pt`) in "Model Settings"; see the [YOLOE docs](https://docs.ultralytics.com/models/yoloe/) |
| Batch model labeling | Any path | Select YOLO detection / segmentation / pose weights in the "Batch Model Labeling" panel |
| AI Polygon (SAM) | `models/sam2_t.pt` | Default path of `Config.AI_POLYGON_CONFIG['default_weights_path']` |

SAM weights:

- `sam2_t.pt` (~75 MB) is recommended; both positive and negative point prompts work well.
- Official filenames (e.g. `sam2_hiera_tiny.pt`, `sam2.1_hiera_tiny.pt`) are automatically copied to the ultralytics standard name before loading.
- `sam2.1_t.pt` and MobileSAM are faster on CPU but have **weak response to negative points**; the program falls back to flood-fill removal of background points.
- To use the original MobileSAM weights, run `python convert_sam.py` first to convert them to ultralytics format (requires `models/mobile_sam_original.bak`).

## Quick start

```bash
python app.py
```

1. Select YOLOE weights in "Model Settings" on the left and click "Load Model".
2. Open a data folder from the file tree or "File → Open Folder"; matching `.txt` labels are loaded automatically.
3. Click "Auto Label" or "AI Polygon" to start annotating; press `Ctrl+S` to save.

## Usage

### 1. Auto-labeling

After loading a model, click "Auto Label" to predict the current image. Results are written as boxes, masks or keypoints depending on the model task. The model classes are written to `classes.txt` in the current folder.

### 2. Visual-prompt labeling (same-class batch)

1. Click "Start Drawing Visual Prompts", box a target in the image and enter a class tag.
2. Click "Stop Drawing" to cache the VPE.
3. Click "Similar-Label Auto Labeling" to label similar objects across all images in the folder.

### 3. AI Polygon (interactive SAM segmentation)

Click "AI Polygon" in the toolbar or press `Ctrl+P` (loads `models/sam2_t.pt` automatically on first use):

| Action | Effect |
| --- | --- |
| Left click | Add a foreground point (green) |
| Right click | Add a background point (red) to exclude a region |
| `Backspace` | Undo the last point |
| `Enter` | Confirm the preview, choose a class and create a Seg annotation (saved automatically) |
| `Esc` | Exit AI Polygon mode |

After confirmation the points are cleared but the mode stays active, so you can annotate objects continuously.

### 4. Batch model labeling

In the "Batch Model Labeling" panel on the right, select YOLO weights and click "Load Model", then set confidence / IoU and click "Batch Label":

- Runs inference over every image in the current folder and writes same-name `.txt` labels;
- Detection / segmentation / pose models produce the corresponding YOLO line formats;
- If non-empty labels already exist, you are asked before they are overwritten;
- Model classes are written to `classes.txt` in the current folder afterwards.

### 5. Manual editing

Press `W` to toggle manual annotation mode and drag to draw a new box. A selected box can be moved / resized by its handles, nudged 1 pixel with the arrow keys, and removed with `Delete`.

### 6. Save and export

- `Ctrl+S` saves annotations (same directory and basename as the image by default);
- `Ctrl+E` exports the current annotation to a chosen directory;
- "File → Batch Export" (`Ctrl+Shift+E`) exports the current folder in one go.

### 7. Organize dataset

Set the output directory and the train / val / test ratios (they must sum to 1), then click "Organize Dataset". The result is an `images|labels/{train,val,test}` layout; unlabeled images go to `blank`.

### 8. Format conversion

"Tools → YOLO Format Conversion (TXT ↔ JSON)" supports Labelme JSON ↔ YOLO-seg TXT and YOLO detection TXT ↔ generic JSON.

## Keyboard shortcuts

| Shortcut | Action |
| --- | --- |
| `A` / `D` | Previous / next image |
| `Space` | Save current image and go to the next one |
| `Ctrl+O` / `Ctrl+Shift+O` | Open image / open folder |
| `Ctrl+S` / `Ctrl+E` | Save annotations / export annotations |
| `Ctrl+Shift+E` | Batch export |
| `Ctrl+P` | Enter / exit AI Polygon |
| `W` | Toggle manual annotation mode |
| `Delete` | Delete the selected annotation |
| `←` `→` `↑` `↓` | Nudge the selected annotation (1 px) |
| Mouse wheel | Zoom |
| `Ctrl++` / `Ctrl+-` / `Ctrl+0` | Zoom in / out / reset |
| `Ctrl+Q` | Quit |

## Configuration

All tunable parameters live in the `Config` class in [`config.py`](config.py):

- `MODEL_CONFIG`: YOLOE weights path, confidence / IoU thresholds, inference device
- `AI_POLYGON_CONFIG`: default SAM weights path, prompt point colors, polygon simplification tolerance, maximum vertices, minimum area
- `ANNOTATION_CONFIG`: colors and line widths for boxes, text, keypoints, skeletons and segmentation
- `POSE_CONFIG`: keypoint names, COCO skeleton connections, per-class radial connection rules
- `GUI_CONFIG`: window title, size, zoom range
- `EXPORT_CONFIG`: export directory, whether to export confidence

## Project structure

```
auto-labeling-system/
├── app.py                      # Main window, events, batch labeling, dataset organization
├── config.py                   # Global configuration
├── requirements.txt            # Dependencies
├── auto_label.spec             # PyInstaller build spec
├── convert_sam.py              # Convert original MobileSAM weights to ultralytics format
├── modules/
│   ├── model_loader.py         # YOLOE loading and prediction (incl. visual prompts)
│   ├── sam_loader.py           # SAM loading, point-prompt segmentation, mask→polygon
│   ├── ai_polygon_editor.py    # AI Polygon interaction state machine
│   ├── batch_labeler.py        # YOLO batch inference and label writing
│   ├── label_engine.py         # Auto-labeling, visual-prompt batch labeling, label loading
│   ├── annotation_display.py   # Annotation rendering (boxes / skeletons / polygons)
│   ├── manual_editor.py        # Manual drawing / moving / resizing
│   ├── label_exporter.py       # YOLO label export and parsing
│   ├── image_browser.py        # Image browsing and view control
│   ├── class_manager.py        # Class management (classes.txt)
│   ├── dataset_organizer.py    # Dataset splitting and copying
│   ├── format_converter.py     # Labelme ↔ YOLO conversion
│   ├── ui_builder.py           # Panels / menus / toolbar
│   └── styles.py               # Dark theme
└── test_*.py / *_test_*.py     # Self-test scripts (pose display, AI polygon, negative points, ...)
```

## Notes

- **Class IDs are positional**: each line of `classes.txt` is a class name and its line number is the class ID. Adding / renaming a class appends or replaces in place (no reordering), but **deleting a middle class shifts the IDs of all following classes**, which can change the meaning of already exported labels. Check the order before doing it.
- **Label files default to the same directory and basename as the image** (`xxx.jpg` ↔ `xxx.txt`); "Save Image to Folder" copies only the image, not the label.
- A single label file may mix detection / Pose / Seg lines; the parser handles each line by its shape.
- Visual-prompt same-class batch labeling requires one successful visual-prompt auto-labeling run first (to cache the VPE).
- Confirming an AI Polygon annotation triggers auto-save and writes directly to the current image's label file.
- Without a GPU, SAM / YOLOE inference is noticeably slower; set the device to `cpu` in `config.py`.

## License

[MIT](LICENSE)
