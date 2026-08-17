# main.py
import sys
import os
import time
import json
import csv
import subprocess
from datetime import datetime
import cv2
import numpy as np
from ultralytics import YOLO
from PySide6.QtWidgets import (
    QApplication, QWidget, QLabel, QPushButton, QHBoxLayout,
    QVBoxLayout, QFrame, QStatusBar, QMessageBox, QGraphicsOpacityEffect
)
from PySide6.QtGui import QPixmap, QImage
from PySide6.QtCore import Qt, QThread, Signal, QPropertyAnimation, QEasingCurve, Slot

# ============================================================================
# <<< DISTANCE CHECK IMPORT >>>
# ============================================================================
from distance_check import checker
try:
    from distance_check import check_button_distances
except Exception as e:
    print(f"WARNING: Could not import distance_check.py ({e}). Distance validation disabled.")
    check_button_distances = None

# ============================================================================
# CONFIGURATION
# ============================================================================
MODEL_PATH = "best.pt"
CALIBRATION_FILE = 'calibration.json'
CSV_FILE = "detection_log.csv"
CLASS_CONFIDENCE = {0: 0.65, 1: 0.4}
PIXEL_CHANGE_THRESHOLD = 200000
FRAME_DIFF_THRESHOLD = 25
COOLDOWN_SECONDS = 0.3
CAPTURE_DELAY = 0.5
NMS_IOU_THRESHOLD = 0.45
CAMERA_INDEX = 0
FRAME_WIDTH = 1280
FRAME_HEIGHT = 720
CAPTURED_FOLDER = "captured_images"
DETECTED_FOLDER = "detected_images"

# DISPLAY SETTINGS
PREVIEW_PANEL_WIDTH = 400
PREVIEW_PANEL_HEIGHT = 480

# ============================================================================
# HELPER FUNCTIONS
# ============================================================================
def load_calibration(cal_file=CALIBRATION_FILE):
    if not os.path.exists(cal_file):
        print(f"Warning: Calibration file '{cal_file}' not found.")
        return None
    with open(cal_file, 'r') as f:
        cal = json.load(f)
    print(f"Loaded calibration: {cal['mm_per_pixel']:.4f} mm/pixel")
    return cal['mm_per_pixel']

def init_csv():
    if not os.path.exists(CSV_FILE):
        with open(CSV_FILE, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow([
                'Timestamp', 'Date', 'Image_Filename',
                'Num_Buttons', 'Num_Defects',
                'Dist_1to2_mm', 'Dist_2to3_mm', 'Dist_3to1_mm', 'Alert'
            ])

def log_to_csv(timestamp, date_str, image_filename,
               num_buttons, num_defects, button_centers, mm_per_pixel,
               d12='0.0', d23='0.0', d31='0.0', alert=''):
    with open(CSV_FILE, 'a', newline='') as f:
        writer = csv.writer(f)
        writer.writerow([
            timestamp, date_str, image_filename,
            num_buttons, num_defects,
            d12, d23, d31,
            alert
        ])

def create_output_folders():
    os.makedirs(CAPTURED_FOLDER, exist_ok=True)
    os.makedirs(DETECTED_FOLDER, exist_ok=True)
    return CAPTURED_FOLDER, DETECTED_FOLDER

def detect_motion(frame1, frame2, threshold_pixels, diff_threshold):
    gray1 = cv2.cvtColor(frame1, cv2.COLOR_BGR2GRAY)
    gray2 = cv2.cvtColor(frame2, cv2.COLOR_BGR2GRAY)
    gray1 = cv2.GaussianBlur(gray1, (21, 21), 0)
    gray2 = cv2.GaussianBlur(gray2, (21, 21), 0)
    diff = cv2.absdiff(gray1, gray2)
    _, thresh = cv2.threshold(diff, diff_threshold, 255, cv2.THRESH_BINARY)
    thresh = cv2.dilate(thresh, None, iterations=2)
    changed_pixels = np.sum(thresh == 255)
    return changed_pixels >= threshold_pixels, changed_pixels

def detect_circle_and_center(image, bbox):
    x1, y1, x2, y2 = map(int, bbox)
    roi = image[y1:y2, x1:x2].copy()
    if roi.size == 0:
        return (x1 + x2) // 2, (y1 + y2) // 2, None
    gray_roi = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
    blurred = cv2.GaussianBlur(gray_roi, (5, 5), 1.5)
    circles = cv2.HoughCircles(
        blurred, cv2.HOUGH_GRADIENT, dp=1, minDist=20,
        param1=50, param2=30, minRadius=5,
        maxRadius=max(roi.shape[0], roi.shape[1]) // 2
    )
    if circles is not None:
        circles = np.uint16(np.around(circles))
        circle = circles[0][0]
        cx, cy, radius = circle
        return (x1 + cx, y1 + cy), (cx, cy, radius)
    else:
        return (x1 + (x2 - x1) // 2, y1 + (y2 - y1) // 2), None

def calculate_button_distances(button_centers, mm_per_pixel):
    if mm_per_pixel is None or len(button_centers) < 2:
        return []
    distances = []
    for i in range(len(button_centers)):
        for j in range(i + 1, len(button_centers)):
            x1, y1 = button_centers[i]
            x2, y2 = button_centers[j]
            dx = float(x2) - float(x1)
            dy = float(y2) - float(y1)
            pixel_dist = np.sqrt(dx * dx + dy * dy)
            distances.append((i, j, pixel_dist * mm_per_pixel))
    return distances

def draw_distances_on_image(image, button_centers, distances):
    if not distances:
        return image
    for i, j, mm_dist in distances:
        cv2.line(image, button_centers[i], button_centers[j], (0, 0, 0), 2)
        mid = ((button_centers[i][0] + button_centers[j][0]) // 2,
               (button_centers[i][1] + button_centers[j][1]) // 2)
        cv2.putText(image, f"{mm_dist:.1f}mm", (mid[0], mid[1] - 10),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 0, 0), 2)
    return image

def process_detections(image, model, mm_per_pixel):
    processed = image.copy()
    results = model(processed, iou=NMS_IOU_THRESHOLD, verbose=False)[0].boxes
    button_detections = []
    defect_detections = []
    for box in results:
        conf = float(box.conf[0])
        cls = int(box.cls[0])
        if conf >= CLASS_CONFIDENCE.get(cls, 0.5):
            bbox = box.xyxy[0].cpu().numpy().astype(int)
            if cls == 0:
                button_detections.append(bbox)
            else:
                defect_detections.append((bbox, conf))
    button_centers = []
    for idx, (x1, y1, x2, y2) in enumerate(button_detections):
        color = (0, 255, 0)
        cv2.rectangle(processed, (x1, y1), (x2, y2), color, 2)
        label = f"button {idx+1}"
        cv2.putText(
            processed, label, (x1, y1 - 10),
            cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2
        )
        center, _ = detect_circle_and_center(processed, [x1, y1, x2, y2])
        center = (int(center[0]), int(center[1]))
        cv2.circle(processed, center, 8, (0, 0, 255), -1)
        button_centers.append(center)
    for idx, (bbox, conf) in enumerate(defect_detections):
        x1, y1, x2, y2 = bbox
        cv2.rectangle(processed, (x1, y1), (x2, y2), (0, 0, 255), 2)
        cv2.putText(processed, f"defect {conf:.2f}", (x1, y1 - 10),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)
    distances = calculate_button_distances(button_centers, mm_per_pixel)
    processed = draw_distances_on_image(processed, button_centers, distances)
    stats = {
        'buttons': len(button_detections),
        'defects': len(defect_detections),
        'button_centers': button_centers,
        'distances': distances
    }
    return processed, stats

def save_images(orig, proc, cap_folder, det_folder):
    ts = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    cap_path = os.path.join(cap_folder, f"original_{ts}.jpg")
    det_path = os.path.join(det_folder, f"detected_{ts}.jpg")
    cv2.imwrite(cap_path, orig)
    cv2.imwrite(det_path, proc)
    return f"original_{ts}.jpg", f"detected_{ts}.jpg"

def draw_waiting_indicator(frame, time_remaining):
    overlay = frame.copy()
    h, w = frame.shape[:2]
    banner_h = 70
    y = h - banner_h - 30
    cv2.rectangle(overlay, (20, y), (w - 20, y + banner_h), (0, 140, 255), -1)
    text = f"Motion Detected - Capturing in {time_remaining:.1f}s"
    text_size = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, 1.3, 4)[0]
    text_x = (w - text_size[0]) // 2
    cv2.putText(overlay, text, (text_x, y + 45),
                cv2.FONT_HERSHEY_SIMPLEX, 1.3, (255, 255, 255), 4)
    result = cv2.addWeighted(frame, 0.25, overlay, 0.75, 0)
    return result

def cv_to_qpixmap(frame):
    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    h, w, ch = rgb.shape
    return QPixmap.fromImage(QImage(rgb.data, w, h, ch * w, QImage.Format_RGB888))

# ============================================================================
# DETECTION WORKER THREAD
# ============================================================================
class DetectionWorker(QThread):
    stream_frame = Signal(object)
    detection_frame = Signal(object)
    capture_count_changed = Signal(int)
    status_changed = Signal(str)

    def __init__(self, cap, model, mm_per_pixel):
        super().__init__()
        self.cap = cap
        self.model = model
        self.mm_per_pixel = mm_per_pixel
        self._running = True

    def stop(self):
        self._running = False

    def run(self):
        print("Camera loop started.")
        prev = None
        last_cap = 0
        count = 0
        waiting = False
        motion_time = None
        cap_folder, det_folder = create_output_folders()

        while self._running:
            ret, frame = self.cap.read()
            if not ret:
                self.msleep(10)
                continue

            now = time.time()
            display = frame.copy()

            if prev is not None and not waiting:
                moved, _ = detect_motion(prev, frame, PIXEL_CHANGE_THRESHOLD, FRAME_DIFF_THRESHOLD)
                if moved and (now - last_cap) >= COOLDOWN_SECONDS:
                    motion_time = now
                    waiting = True

            if waiting and motion_time:
                elapsed = now - motion_time
                if elapsed < CAPTURE_DELAY:
                    display = draw_waiting_indicator(display, CAPTURE_DELAY - elapsed)
                else:
                    count += 1
                    ts = datetime.now().strftime("%H:%M:%S")
                    processed, stats = process_detections(frame, self.model, self.mm_per_pixel)
                    cap_file, det_file = save_images(frame, processed, cap_folder, det_folder)
                    
                    # CLEAR PREVIOUS ALERT
                    self.parent().current_alert_text = ""

                    # DISTANCE + DEFECT ALERT
                    dist_info = {"d12": "0.0", "d23": "0.0", "d31": "0.0", "alert": ""}
                    if check_button_distances and stats['buttons'] == 3:
                        dist_info = check_button_distances(
                            stats['button_centers'],
                            self.mm_per_pixel,
                            self.parent()
                        )
                        # Inject defect count
                        
                        checker.check_and_alert(
                            stats['button_centers'],
                            self.mm_per_pixel,
                            stats['defects'],
                            self.parent()
                        )

                    log_to_csv(
                        ts,
                        datetime.now().strftime("%Y-%m-%d"),
                        cap_file,
                        stats['buttons'],
                        stats['defects'],
                        stats['button_centers'],
                        self.mm_per_pixel,
                        d12=dist_info["d12"],
                        d23=dist_info["d23"],
                        d31=dist_info["d31"],
                        alert=dist_info["alert"]
                    )

                    print(f"[{ts}] Captured #{count} | Buttons: {stats['buttons']} | Defects: {stats['defects']}")
                    self.detection_frame.emit(processed.copy())
                    last_cap = now
                    waiting = False
                    motion_time = None

            status_text = "WAITING" if waiting else "MONITORING"
            cv2.putText(display, status_text, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 140, 255), 3)
            cv2.putText(display, f"Captures: {count}", (10, 70), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)
            self.stream_frame.emit(display)
            prev = frame.copy()
            self.msleep(33)

        print("Camera loop stopped.")

# ============================================================================
# GUI COMPONENTS
# ============================================================================
class StatusIndicator(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)
        self.dot = QFrame()
        self.dot.setFixedSize(16, 16)
        self.dot.setStyleSheet("border-radius: 8px; background-color: #FF5252;")
        self.opacity_effect = QGraphicsOpacityEffect(self.dot)
        self.dot.setGraphicsEffect(self.opacity_effect)
        self.anim = QPropertyAnimation(self.opacity_effect, b"opacity", self)
        self.anim.setDuration(900)
        self.anim.setStartValue(0.35)
        self.anim.setEndValue(1.0)
        self.anim.setEasingCurve(QEasingCurve.InOutQuad)
        self.anim.setLoopCount(-1)
        self.label = QLabel("Status: Stopped")
        self.label.setStyleSheet("color: #FF5252; font-weight: bold; font-size: 18px;")
        layout.addWidget(self.dot)
        layout.addWidget(self.label)

    def set_running(self):
        self.dot.setStyleSheet("background-color: #4CAF50; border-radius: 8px;")
        self.label.setText("Status: Running")
        self.label.setStyleSheet("color: #4CAF50; font-weight: bold; font-size: 18px;")
        self.anim.start()

    def set_stopped(self):
        self.dot.setStyleSheet("background-color: #FF5252; border-radius: 8px;")
        self.label.setText("Status: Stopped")
        self.label.setStyleSheet("color: #FF5252; font-weight: bold; font-size: 18px;")
        self.anim.stop()
        self.opacity_effect.setOpacity(1.0)

class RoundedPanel(QFrame):
    def __init__(self):
        super().__init__()
        self.setStyleSheet("background-color: #121A2C; border: 2px solid #1F2A40; border-radius: 18px;")
        self.setMinimumSize(640, 480)

class MainWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("YOLOv8 Button & Defect Detection")
        self.resize(900, 600)
        self.worker = None
        self.cap = None
        self.model = None
        self.mm_per_pixel = None
        self.current_alert_text = ""  # Store alert text
        self._build_ui()
        self.setStyleSheet(self.stylesheet())
        
                # Connect the signal from distance_check
        from distance_check import checker
        checker.alert_signal.connect(self.show_distance_alert_on_image)

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(10)

        # CONTROL BAR
        ctrl = QHBoxLayout()
        ctrl.setSpacing(12)
        self.start_btn = QPushButton("Start Detection")
        self.stop_btn = QPushButton("Stop Detection")
        self.calibration_btn = QPushButton("Calibration")
        self.stop_btn.setEnabled(False)
        self.status_ind = StatusIndicator()
        self.start_btn.clicked.connect(self.start_detection)
        self.stop_btn.clicked.connect(self.stop_detection)
        self.calibration_btn.clicked.connect(self.run_calibration)
        ctrl_row1 = QHBoxLayout()
        ctrl_row1.setSpacing(10)
        ctrl_row1.addWidget(self.start_btn)
        ctrl_row1.addWidget(self.stop_btn)
        ctrl_row1.addWidget(self.calibration_btn)

        ctrl_row2 = QHBoxLayout()
        ctrl_row2.addWidget(self.status_ind)
        ctrl_row2.addStretch()

        layout.addLayout(ctrl_row1)
        layout.addLayout(ctrl_row2)


        # PANELS
        panels = QHBoxLayout()
        panels.setSpacing(12)

        self.stream_panel = RoundedPanel()
        self.stream_panel.setMinimumSize(360, 260)
        self.stream_lbl = QLabel("Camera Stream")
        self.stream_lbl.setAlignment(Qt.AlignCenter)
        self.stream_lbl.setScaledContents(True)
        QVBoxLayout(self.stream_panel).addWidget(self.stream_lbl)

        self.detect_panel = RoundedPanel()
        self.detect_panel.setMinimumSize(360, 260)
        self.detect_lbl = QLabel("Detection Result")
        self.detect_lbl.setAlignment(Qt.AlignCenter)
        self.detect_lbl.setScaledContents(True)
        QVBoxLayout(self.detect_panel).addWidget(self.detect_lbl)

        panels.addWidget(self.stream_panel, 1)
        panels.addWidget(self.detect_panel, 1)

        # STATUS BAR
        self.status_bar = QStatusBar()
        self.status_bar.showMessage("Ready")

        layout.addLayout(ctrl)
        layout.addLayout(panels)
        layout.addWidget(self.status_bar)

    # def stylesheet(self):
    #     return """
    #     QWidget { background-color: #0A0F1F; color: #E6E9EF; font-size: 16px; }
    #     QPushButton { background-color: #3A5A9C; color: white; border: 1px solid #1F2A40; padding: 10px 20px; border-radius: 8px; }
    #     QPushButton:hover { background-color: #4C6FB5; }
    #     QStatusBar { background-color: #121A2C; border-top: 1px solid #1F2A40; color: #9EB5D6; }
    #     """

    def stylesheet(self):
        return """
            QWidget { background-color: #0A0F1F; color: #E6E9EF; font-size: 18px; }
            
            QPushButton { 
                background-color: #3A5A9C; 
                color: white; 
                border: 2px solid #1F2A40; 
                padding: 18px 28px;           /* BIGGER PADDING */
                border-radius: 15px; 
                font-size: 22px;              /* BIG TEXT */
                font-weight: bold;
                min-height: 80px;            /* TALL BUTTON */
                min-width: 200px;             /* WIDE BUTTON */
            }
            
            QPushButton:hover { 
                background-color: #4C6FB5; 
            }
            
            QPushButton:pressed { 
                background-color: #2E4A80; 
            }
            
            QStatusBar { 
                background-color: #121A2C; 
                border-top: 1px solid #1F2A40; 
                color: #9EB5D6; 
                font-size: 22px; 
            }
            """

    def run_calibration(self):
        try:
            if os.path.exists("calibration.py"):
                subprocess.Popen([sys.executable, "calibration.py"])
                self.status_bar.showMessage("Calibration process started")
            else:
                QMessageBox.warning(self, "Warning", "calibration.py file not found!")
                self.status_bar.showMessage("Calibration file not found")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to run calibration: {str(e)}")
            self.status_bar.showMessage("Calibration failed")

    @Slot(str)
    def show_distance_alert_on_image(self, text):
        """Receive alert from worker and store it"""
        self.current_alert_text = text

    def draw_alert_on_frame(self, frame):
        """Draw red banner if alert exists"""
        if not self.current_alert_text:
            return frame

        overlay = frame.copy()
        h, w = frame.shape[:2]
        banner_h = 60
        y = h - banner_h - 20

        # Red background
        cv2.rectangle(overlay, (10, y), (w - 10, y + banner_h), (0, 0, 255), -1)

        # White bold text
        font_scale = 0.9
        thickness = 3
        text_size = cv2.getTextSize(self.current_alert_text, cv2.FONT_HERSHEY_SIMPLEX, font_scale, thickness)[0]
        text_x = (w - text_size[0]) // 2
        text_y = y + 40

        cv2.putText(overlay, self.current_alert_text, (text_x, text_y),
                    cv2.FONT_HERSHEY_SIMPLEX, font_scale, (255, 255, 255), thickness)

        # Blend
        result = cv2.addWeighted(frame, 0.3, overlay, 0.7, 0)
        return result

    def start_detection(self):
        if self.worker and self.worker.isRunning():
            return

        self.mm_per_pixel = load_calibration()
        if not os.path.exists(MODEL_PATH):
            QMessageBox.critical(self, "Error", f"Model not found: {MODEL_PATH}")
            return

        self.model = YOLO(MODEL_PATH)
        self.cap = cv2.VideoCapture(CAMERA_INDEX)
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, FRAME_WIDTH)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, FRAME_HEIGHT)
        if not self.cap.isOpened():
            QMessageBox.critical(self, "Error", "Cannot open camera")
            return

        init_csv()
        self.worker = DetectionWorker(self.cap, self.model, self.mm_per_pixel)
        self.worker.setParent(self)

        self.worker.stream_frame.connect(
            lambda f: self.stream_lbl.setPixmap(cv_to_qpixmap(f))
        )
        # ALERT DRAWN ON IMAGE
        self.worker.detection_frame.connect(
            lambda f: self.detect_lbl.setPixmap(cv_to_qpixmap(self.draw_alert_on_frame(f)))
        )
        self.worker.capture_count_changed.connect(
            lambda c: self.status_bar.showMessage(f"Detection running – Captures: {c}")
        )
        self.worker.status_changed.connect(
            lambda s: self.status_ind.set_running() if s == "Running" else self.status_ind.set_stopped()
        )

        self.worker.start()
        self.start_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        self.status_ind.set_running()
        self.status_bar.showMessage("Detection running")

    def stop_detection(self):
        if self.worker:
            self.worker.stop()
            self.worker.wait()
        if self.cap:
            self.cap.release()
            self.cap = None
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.status_ind.set_stopped()
        self.current_alert_text = ""  # Clear alert
        self.status_bar.showMessage("Detection stopped")


if __name__ == "__main__":

    os.environ["QT_ENABLE_HIGHDPI_SCALING"] = "1"
    os.environ["QT_AUTO_SCREEN_SCALE_FACTOR"] = "1"

    app = QApplication(sys.argv)
    win = MainWindow()
    #win.show()                  # Shows the window with its designed size (from Qt Designer or setSize)
    #win.resize(800, 480)
    win.showFullScreen()
    sys.exit(app.exec())
