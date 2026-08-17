# main.py - COMPLETE IMPROVED VERSION
import sys
import serial
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
    QVBoxLayout, QFrame, QStatusBar, QMessageBox, QGraphicsOpacityEffect,
    QComboBox
)
from PySide6.QtGui import QPixmap, QImage, QIcon
from PySide6.QtCore import Qt, QThread, Signal, QPropertyAnimation, QEasingCurve, Slot

# ============================================================================
# IMPORTS
# ============================================================================
from distance_check import checker
try:
    from distance_check import check_button_distances
except Exception as e:
    print(f"WARNING: Could not import distance_check.py ({e}). Distance validation disabled.")
    check_button_distances = None

try:
    from color_defect_detector import check_color_defects
except Exception as e:
    print(f"WARNING: Could not import color_defect_detector.py ({e}). Color defect detection disabled.")
    check_color_defects = None

from style_settings import StyleSettingsDialog

# ============================================================================
# CONFIGURATION
# ============================================================================
MODEL_PATH = "best.pt"
CALIBRATION_FILE = 'calibration.json'
CSV_FILE = "detection_log.csv"
CLASS_CONFIDENCE = {0: 0.6, 1: 0.85, 2: 0.85}
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
PREVIEW_PANEL_WIDTH = 400
PREVIEW_PANEL_HEIGHT = 480

# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def send_D_to_com3(var):
    try:
        ser = serial.Serial(port="COM3", baudrate=115200, timeout=1)
        ser.write(var.encode())
        ser.close()
    except Exception as e:
        print(f"Serial communication error: {e}")

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
                'Num_Buttons', 'Expected_Buttons', 'Button_Count_OK',
                'Max_Distance_mm', 'Expected_Distance_mm', 'Distance_OK',
                'YOLO_Defects', 'Color_Defects', 'Total_Defects', 'Alert'
            ])

def log_to_csv(timestamp, date_str, image_filename,
               num_buttons, expected_buttons, max_distance, expected_distance,
               yolo_defect_count, color_defect_count, total_defects, alert=''):
    button_count_ok = "YES" if num_buttons == expected_buttons else "NO"
    
    distance_ok = "N/A"
    if max_distance > 0 and expected_distance > 0:
        tolerance = 3.0
        min_allowed = expected_distance - tolerance
        max_allowed = expected_distance + tolerance
        distance_ok = "YES" if (min_allowed <= max_distance <= max_allowed) else "NO"
    
    with open(CSV_FILE, 'a', newline='') as f:
        writer = csv.writer(f)
        writer.writerow([
            timestamp, date_str, image_filename,
            num_buttons, expected_buttons, button_count_ok,
            f"{max_distance:.1f}", f"{expected_distance:.1f}", distance_ok,
            yolo_defect_count, color_defect_count, total_defects, alert
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

def calculate_max_button_distance(button_centers, mm_per_pixel):
    """Calculate the maximum distance between any two buttons"""
    if mm_per_pixel is None or len(button_centers) < 2:
        return 0.0
    
    max_dist = 0.0
    for i in range(len(button_centers)):
        for j in range(i + 1, len(button_centers)):
            x1, y1 = button_centers[i]
            x2, y2 = button_centers[j]
            dx = float(x2) - float(x1)
            dy = float(y2) - float(y1)
            pixel_dist = np.sqrt(dx * dx + dy * dy)
            mm_dist = pixel_dist * mm_per_pixel
            if mm_dist > max_dist:
                max_dist = mm_dist
    
    return max_dist

def draw_max_distance_on_image(image, button_centers, max_distance, mm_per_pixel):
    """Draw only the maximum distance line on the image"""
    if len(button_centers) < 2 or mm_per_pixel is None:
        return image
    
    max_dist = 0.0
    max_pair = None
    
    for i in range(len(button_centers)):
        for j in range(i + 1, len(button_centers)):
            x1, y1 = button_centers[i]
            x2, y2 = button_centers[j]
            dx = float(x2) - float(x1)
            dy = float(y2) - float(y1)
            pixel_dist = np.sqrt(dx * dx + dy * dy)
            mm_dist = pixel_dist * mm_per_pixel
            
            if mm_dist > max_dist:
                max_dist = mm_dist
                max_pair = (i, j)
    
    if max_pair:
        i, j = max_pair
        cv2.line(image, button_centers[i], button_centers[j], (0, 0, 0), 2)
        mid = ((button_centers[i][0] + button_centers[j][0]) // 2,
               (button_centers[i][1] + button_centers[j][1]) // 2)
        cv2.putText(image, f"{max_distance:.1f}mm", (mid[0], mid[1] - 10),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 0, 0), 2)
    
    return image

def process_detections(image, model, mm_per_pixel):
    """Process YOLO detections and extract button centers"""
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
            elif cls == 1:
                defect_detections.append((bbox, conf, 1, "BEND PROUND"))
            elif cls == 2:
                defect_detections.append((bbox, conf, 2, "MACHINE"))

    # Draw buttons and get centers
    button_centers = []
    for idx, (x1, y1, x2, y2) in enumerate(button_detections):
        color = (0, 255, 0)
        cv2.rectangle(processed, (x1, y1), (x2, y2), color, 2)
        label = f"button {idx+1}"
        cv2.putText(processed, label, (x1, y1 - 10),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)
        center, _ = detect_circle_and_center(processed, [x1, y1, x2, y2])
        center = (int(center[0]), int(center[1]))
        cv2.circle(processed, center, 8, (0, 0, 255), -1)
        button_centers.append(center)
    
    # Draw defects
    for idx, (bbox, conf, defect_class, defect_name) in enumerate(defect_detections):
        x1, y1, x2, y2 = bbox
        cv2.rectangle(processed, (x1, y1), (x2, y2), (0, 0, 255), 2)
        cv2.putText(processed, f"{defect_name} {conf:.2f}", (x1, y1 - 10),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)
    
    # Calculate maximum distance
    max_distance = calculate_max_button_distance(button_centers, mm_per_pixel)
    processed = draw_max_distance_on_image(processed, button_centers, max_distance, mm_per_pixel)
    
    # Prepare YOLO defects list
    yolo_defects = [(d[2], d[1]) for d in defect_detections]
    
    stats = {
        'buttons': len(button_detections),
        'button_bboxes': button_detections,
        'defects': defect_detections,
        'yolo_defects': yolo_defects,
        'button_centers': button_centers,
        'max_distance': max_distance
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
# DETECTION WORKER THREAD - IMPROVED ALGORITHM
# ============================================================================
class DetectionWorker(QThread):
    stream_frame = Signal(object)
    detection_frame = Signal(object)
    capture_count_changed = Signal(int)
    status_changed = Signal(str)

    def __init__(self, cap, model, mm_per_pixel, expected_button_count, expected_distance):
        super().__init__()
        self.cap = cap
        self.model = model
        self.mm_per_pixel = mm_per_pixel
        self.expected_button_count = expected_button_count
        self.expected_distance = expected_distance
        self._running = True

    def stop(self):
        self._running = False

    def run(self):
        print("\n" + "="*80)
        print("🚀 DETECTION SYSTEM STARTED")
        print("="*80)
        print(f"📊 Expected Button Count: {self.expected_button_count}")
        print(f"📏 Expected Distance: {self.expected_distance} mm (±5mm tolerance)")
        print("="*80 + "\n")
        
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

            # Motion detection
            if prev is not None and not waiting:
                moved, _ = detect_motion(prev, frame, PIXEL_CHANGE_THRESHOLD, FRAME_DIFF_THRESHOLD)
                if moved and (now - last_cap) >= COOLDOWN_SECONDS:
                    motion_time = now
                    waiting = True

            # Capture and process
            if waiting and motion_time:
                elapsed = now - motion_time
                if elapsed < CAPTURE_DELAY:
                    display = draw_waiting_indicator(display, CAPTURE_DELAY - elapsed)
                else:
                    count += 1
                    ts = datetime.now().strftime("%H:%M:%S")
                    
                    # Run YOLO detection
                    processed, stats = process_detections(frame, self.model, self.mm_per_pixel)
                    cap_file, det_file = save_images(frame, processed, cap_folder, det_folder)

                    print("\n" + "="*80)
                    print(f"📸 CAPTURE #{count} at {ts}")
                    print("="*80)
                    
                    # ═══════════════════════════════════════════════════════════
                    # DETECTION ALGORITHM - CLEAR ORDER
                    # ═══════════════════════════════════════════════════════════
                    
                    # Initialize defect tracking
                    all_defects = []
                    defect_summary = {
                        'button_count_defect': False,
                        'yolo_defects': [],
                        'distance_defect': False,
                        'color_defects': 0
                    }
                    
                    # STEP 1: Check if at least one button detected
                    if stats['buttons'] == 0:
                        print("⚠️  NO BUTTONS DETECTED - Skipping all checks")
                        self.detection_frame.emit(processed)
                        last_cap = now
                        waiting = False
                        motion_time = None
                        continue
                    
                    print(f"✓ Buttons detected: {stats['buttons']}")
                    
                    # STEP 2: YOLO-based defects (defect1, defect2)
                    print("\n--- STEP 1: YOLO Defect Detection ---")
                    if stats['yolo_defects']:
                        for defect_class, confidence in stats['yolo_defects']:
                            if defect_class == 1:
                                msg = f"BEND PROUND DEFECT (conf: {confidence:.2f})"
                                all_defects.append(msg)
                                defect_summary['yolo_defects'].append(msg)
                                print(f"  🔴 {msg}")
                            elif defect_class == 2:
                                msg = f"MACHINE DEFECT (conf: {confidence:.2f})"
                                all_defects.append(msg)
                                defect_summary['yolo_defects'].append(msg)
                                print(f"  🔴 {msg}")
                    else:
                        print("  ✓ No YOLO defects detected")
                    
                    # STEP 3: Button Count Check
                    print("\n--- STEP 2: Button Count Verification ---")
                    if stats['buttons'] != self.expected_button_count:
                        msg = f"BUTTON COUNT MISMATCH: Expected {self.expected_button_count}, Found {stats['buttons']}"
                        all_defects.append(msg)
                        defect_summary['button_count_defect'] = True
                        print(f"  🔴 {msg}")
                    else:
                        print(f"  ✓ Button count OK: {stats['buttons']}/{self.expected_button_count}")
                    
                    # STEP 4: Distance Check (only if 2+ buttons)
                    print("\n--- STEP 3: Distance Verification ---")
                    if len(stats['button_centers']) >= 2:
                        max_dist = stats['max_distance']
                        tolerance = 5.0
                        min_allowed = self.expected_distance - tolerance
                        max_allowed = self.expected_distance + tolerance
                        
                        print(f"  Max distance: {max_dist:.1f}mm")
                        print(f"  Expected range: {min_allowed:.1f}mm - {max_allowed:.1f}mm")
                        
                        if not (min_allowed <= max_dist <= max_allowed):
                            msg = f"DISTANCE OUT OF RANGE: {max_dist:.1f}mm (Expected: {self.expected_distance:.1f}mm ±5mm)"
                            all_defects.append(msg)
                            defect_summary['distance_defect'] = True
                            print(f"  🔴 {msg}")
                        else:
                            print(f"  ✓ Distance OK")
                    else:
                        print("  ⚠️  Not enough buttons for distance check")
                    
                    # STEP 5: Color Defect Check
                    print("\n--- STEP 4: Color Defect Detection ---")
                    color_defects = 0
                    if check_color_defects:
                        try:
                            color_defects = check_color_defects(frame, stats['button_bboxes'])
                            if color_defects > 0:
                                msg = f"COLOR DEFECT ×{color_defects}"
                                all_defects.append(msg)
                                defect_summary['color_defects'] = color_defects
                                print(f"  🔴 {msg}")
                            else:
                                print("  ✓ No color defects detected")
                        except Exception as e:
                            print(f"  ⚠️  Color check error: {e}")
                    else:
                        print("  ⚠️  Color detection disabled")
                    
                    # ═══════════════════════════════════════════════════════════
                    # FINAL RESULT COMPILATION
                    # ═══════════════════════════════════════════════════════════
                    
                    print("\n" + "="*80)
                    print("📋 DETECTION SUMMARY")
                    print("="*80)
                    
                    total_defects = len(all_defects)
                    
                    if total_defects == 0:
                        print("✅ PASS - No defects detected")
                        final_alert = ""
                    else:
                        print(f"❌ FAIL - {total_defects} defect(s) detected:")
                        for i, defect in enumerate(all_defects, 1):
                            print(f"   {i}. {defect}")
                        final_alert = " | ".join(all_defects)
                        
                        # Send signal to PLC/Arduino
                        send_D_to_com3('D')
                    
                    print("="*80 + "\n")
                    
                    # Update GUI with alert
                    self.parent().current_alert_text = final_alert
                    final_image = self.parent().draw_alert_on_frame(processed)
                    self.detection_frame.emit(final_image)
                    
                    # Log to CSV
                    log_to_csv(
                        ts,
                        datetime.now().strftime("%Y-%m-%d"),
                        cap_file,
                        stats['buttons'],
                        self.expected_button_count,
                        stats['max_distance'],
                        self.expected_distance,
                        len(stats['yolo_defects']),
                        color_defects,
                        total_defects,
                        alert=final_alert
                    )
                    
                    last_cap = now
                    waiting = False
                    motion_time = None

            # Display status
            status_text = "WAITING" if waiting else "MONITORING"
            cv2.putText(display, status_text, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 140, 255), 3)
            cv2.putText(display, f"Captures: {count}", (10, 70), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)
            self.stream_frame.emit(display)
            prev = frame.copy()
            self.msleep(33)

        print("\n🛑 Detection system stopped.\n")

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
        self.current_alert_text = ""
        self.selected_style_data = None
        self._build_ui()
        self.setStyleSheet(self.stylesheet())
        self.load_styles_to_dropdown()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(10)

        # Control Row 1
        ctrl_row1 = QHBoxLayout()
        ctrl_row1.setSpacing(12)
        self.start_btn = QPushButton("Start Detection")
        self.stop_btn = QPushButton("Stop Detection")
        self.calibration_btn = QPushButton("Calibration")
        self.stop_btn.setEnabled(False)
        
        self.start_btn.clicked.connect(self.start_detection)
        self.stop_btn.clicked.connect(self.stop_detection)
        self.calibration_btn.clicked.connect(self.run_calibration)
        
        ctrl_row1.addWidget(self.start_btn)
        ctrl_row1.addWidget(self.stop_btn)
        ctrl_row1.addWidget(self.calibration_btn)

        # Control Row 2
        ctrl_row2 = QHBoxLayout()
        ctrl_row2.setSpacing(15)
        
        self.status_ind = StatusIndicator()
        ctrl_row2.addWidget(self.status_ind)
        ctrl_row2.addSpacing(30)
        
        style_label = QLabel("Style:")
        style_label.setStyleSheet("color: #E6E9EF; font-size: 18px; font-weight: bold;")
        ctrl_row2.addWidget(style_label)
        
        self.style_dropdown = QComboBox()
        self.style_dropdown.setMinimumWidth(200)
        self.style_dropdown.setMinimumHeight(50)
        self.style_dropdown.currentTextChanged.connect(self.on_style_changed)
        ctrl_row2.addWidget(self.style_dropdown)
        
        self.settings_btn = QPushButton("⚙")
        self.settings_btn.setFixedSize(300, 250)
        self.settings_btn.setStyleSheet("""
            QPushButton {
                background-color: #3A5A9C;
                color: white;
                border: 2px solid #1F2A40;
                border-radius: 22px;
                font-size: 20px;
                font-weight: bold;
            }
            QPushButton:hover { background-color: #4C6FB5; }
            QPushButton:pressed { background-color: #2E4A80; }
        """)
        self.settings_btn.clicked.connect(self.open_settings)
        ctrl_row2.addWidget(self.settings_btn)
        ctrl_row2.addStretch()

        layout.addLayout(ctrl_row1)
        layout.addLayout(ctrl_row2)

        # Panels
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

        # Status Bar
        self.status_bar = QStatusBar()
        self.status_bar.showMessage("Ready - Please select a style")

        layout.addLayout(panels)
        layout.addWidget(self.status_bar)

    def stylesheet(self):
        return """
            QWidget { 
                background-color: #0A0F1F; 
                color: #E6E9EF; 
                font-size: 18px; 
            }
            
            QPushButton { 
                background-color: #3A5A9C; 
                color: white; 
                border: 2px solid #1F2A40; 
                padding: 18px 28px;
                border-radius: 15px; 
                font-size: 22px;
                font-weight: bold;
                min-height: 80px;
                min-width: 200px;
            }
            
            QPushButton:hover { background-color: #4C6FB5; }
            QPushButton:pressed { background-color: #2E4A80; }
            
            QComboBox {
                background-color: #121A2C;
                color: #E6E9EF;
                border: 2px solid #1F2A40;
                border-radius: 10px;
                padding: 10px;
                font-size: 18px;
                min-height: 50px;
            }
            
            QComboBox:hover { border: 2px solid #3A5A9C; }
            
            QComboBox::drop-down {
                border: none;
                width: 30px;
            }
            
            QComboBox::down-arrow {
                image: none;
                border-left: 5px solid transparent;
                border-right: 5px solid transparent;
                border-top: 8px solid #E6E9EF;
                margin-right: 10px;
            }
            
            QComboBox QAbstractItemView {
                background-color: #121A2C;
                color: #E6E9EF;
                selection-background-color: #3A5A9C;
                border: 2px solid #1F2A40;
                padding: 5px;
            }
            
            QStatusBar { 
                background-color: #121A2C; 
                border-top: 1px solid #1F2A40; 
                color: #9EB5D6; 
                font-size: 22px; 
            }
        """

    def load_styles_to_dropdown(self):
        """Load saved styles into the dropdown"""
        self.style_dropdown.clear()
        style_names = StyleSettingsDialog.get_style_names()
        if style_names:
            self.style_dropdown.addItems(style_names)
            if len(style_names) > 0:
                self.on_style_changed(style_names[0])
        else:
            self.style_dropdown.addItem("No styles available")
            self.status_bar.showMessage("No styles found - Please create a style first")

    def on_style_changed(self, style_name):
        """Handle style selection change"""
        if style_name and style_name != "No styles available":
            style_data = StyleSettingsDialog.get_style_data(style_name)
            if style_data:
                self.selected_style_data = style_data
                button_count = style_data.get('button_count', 3)
                button_distance = style_data.get('button_distance', 20.0)
                self.status_bar.showMessage(
                    f"✓ Style Selected: {style_name} | Buttons: {button_count} | Distance: {button_distance}mm"
                )
                print(f"\n📋 Style Changed: {style_name}")
                print(f"   • Expected Buttons: {button_count}")
                print(f"   • Expected Distance: {button_distance}mm")
    
    def open_settings(self):
        """Open the style settings dialog"""
        dialog = StyleSettingsDialog(self)
        if dialog.exec():
            self.load_styles_to_dropdown()

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

    def draw_alert_on_frame(self, frame):
        """Draw red banner with defect alerts - NO BLINKING"""
        if not self.current_alert_text:
            return frame

        overlay = frame.copy()
        h, w = frame.shape[:2]
        
        # Split alerts into multiple lines
        alert_parts = self.current_alert_text.split(" | ")
        
        font = cv2.FONT_HERSHEY_SIMPLEX
        font_scale = 1
        thickness = 3
        line_spacing = 40
        padding = 20
        
        num_lines = len(alert_parts)
        banner_h = (num_lines * line_spacing) + (padding * 2)
        y = h - banner_h - 20
        
        # Red background
        cv2.rectangle(overlay, (10, y), (w - 10, y + banner_h), (0, 0, 255), -1)

        # Draw each line
        current_y = y + padding + 18
        for text_line in alert_parts:
            text_size = cv2.getTextSize(text_line, font, font_scale, thickness)[0]
            text_x = (w - text_size[0]) // 2
            cv2.putText(overlay, text_line, (text_x, current_y),
                       font, font_scale, (255, 255, 255), thickness)
            current_y += line_spacing
        
        # Blend (solid, no blinking)
        result = cv2.addWeighted(frame, 0.3, overlay, 0.7, 0)
        return result

    def start_detection(self):
        if self.worker and self.worker.isRunning():
            return
        
        if not self.selected_style_data:
            QMessageBox.warning(
                self, 
                "No Style Selected", 
                "Please select a style from the dropdown before starting detection!"
            )
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
        expected_button_count = self.selected_style_data.get('button_count', 3)
        expected_distance = self.selected_style_data.get('button_distance', 20.0)
        
        self.worker = DetectionWorker(
            self.cap, 
            self.model, 
            self.mm_per_pixel,
            expected_button_count,
            expected_distance
        )
        self.worker.setParent(self)

        self.worker.stream_frame.connect(
            lambda f: self.stream_lbl.setPixmap(cv_to_qpixmap(f))
        )
        self.worker.detection_frame.connect(
            lambda f: self.detect_lbl.setPixmap(cv_to_qpixmap(f))
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
        style_name = self.style_dropdown.currentText()
        self.status_bar.showMessage(
            f"Detection running | Style: {style_name} | Buttons: {expected_button_count} | Distance: {expected_distance}mm"
        )

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
        self.current_alert_text = ""
        if self.selected_style_data:
            style_name = self.style_dropdown.currentText()
            button_count = self.selected_style_data.get('button_count', 3)
            button_distance = self.selected_style_data.get('button_distance', 20.0)
            self.status_bar.showMessage(
                f"Detection stopped | Style: {style_name} | Buttons: {button_count} | Distance: {button_distance}mm"
            )
        else:
            self.status_bar.showMessage("Detection stopped")


if __name__ == "__main__":
    os.environ["QT_ENABLE_HIGHDPI_SCALING"] = "1"
    os.environ["QT_AUTO_SCREEN_SCALE_FACTOR"] = "1"

    app = QApplication(sys.argv)
    win = MainWindow()
    win.showFullScreen()
    sys.exit(app.exec())



