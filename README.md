# Snap Button Defect Detection System

This project is a camera-based inspection system for checking snap buttons on a product surface. It helps detect whether the buttons are present, correctly placed, and free from defects.

## Project idea

The system uses:
- OpenCV for image processing
- YOLO model for defect detection
- button counting and distance checks
- color defect analysis
- CSV logging for inspection results
- a desktop app interface for live monitoring

The goal is to automatically inspect snap buttons and flag bad products before they continue in production.

## Main features

- Detects button positions in the captured image
- Counts the number of buttons
- Measures the distance between buttons
- Detects visual defects using a trained YOLO model
- Checks color-related defects
- Shows alert messages when a defect is found
- Saves inspection data in a log file

## Project structure

- `jjm_snap_button_fullsetup_v2/` - main application folder
  - `main.py` - main inspection program
  - `start.py` - launches the app
  - `calibration.py` - camera calibration and measurement setup
  - `distance_check.py` - button spacing validation
  - `color_defect_detector.py` - color defect detection logic
  - `best.pt` - trained YOLO model
  - `calibration.json` - saved calibration values
  - `detection_log.csv` - inspection log records
- `snap_buttons/jjm_snap_button_fullsetup_v1/` - earlier version of the system
- `button_deffects_v1/` - test / sample defect detection files

## How it works

1. Camera captures the product image.
2. The system detects the buttons in the frame.
3. It checks the button count and distance between them.
4. A YOLO model detects defect classes.
5. Color-based defects are also checked.
6. Results are saved and shown as pass/fail alerts.

## Requirements

Python environment with the dependencies listed in the project requirements file.

Typical libraries used:
- OpenCV
- NumPy
- PySide6
- Ultralytics
- Torch

## Run the project

From the main project folder:

```bash
cd jjm_snap_button_fullsetup_v2
pip install -r requirements.txt
python start.py
```

Or run directly:

```bash
python main.py
```

## Notes

This project is a simple inspection system focused on quality control for snap buttons. It is useful for production checking, visual defect detection, and quick machine-assisted validation.

## License

This project is for internal / local project use unless otherwise specified by the owner.
