# distance_check.py
import math
from PySide6.QtCore import QObject, Signal
import serial

def send_D_to_com3(var):
    ser = serial.Serial(port="COM3", baudrate=115200, timeout=1)
    ser.write(var.encode())   # convert string to bytes
    ser.close()

class DistanceChecker(QObject):
    alert_signal = Signal(str)

    def __init__(self):
        super().__init__()

    def check_and_alert(self, button_centers, mm_per_pixel, yolo_defects, 
                       expected_button_count, expected_distance, parent_window=None):
        """
        Check for defects based on:
        - Button count vs expected
        - Maximum distance between buttons vs expected (with ±5mm tolerance)
        - YOLO detected defects (defect1 = bend/round defect, defect2 = machine defect)
        
        Returns: dict with distances, alert message, and defect details
        """
        d12 = d23 = d31 = 0.0
        max_distance = 0.0
        alert_parts = []
        defect_details = []

        # === DISTANCE CALCULATION ===
        if mm_per_pixel is not None and len(button_centers) >= 2:
            centers = sorted(button_centers, key=lambda c: c[0])
            
            # Calculate all pairwise distances
            distances = []
            if len(centers) >= 2:
                p12 = math.sqrt((centers[1][0] - centers[0][0])**2 + 
                               (centers[1][1] - centers[0][1])**2)
                d12 = p12 * mm_per_pixel
                distances.append(d12)
            
            if len(centers) >= 3:
                p23 = math.sqrt((centers[2][0] - centers[1][0])**2 + 
                               (centers[2][1] - centers[1][1])**2)
                p31 = math.sqrt((centers[2][0] - centers[0][0])**2 + 
                               (centers[2][1] - centers[0][1])**2)
                d23 = p23 * mm_per_pixel
                d31 = p31 * mm_per_pixel
                distances.extend([d23, d31])
            
            # Find maximum distance
            if distances:
                max_distance = max(distances)

        # Format for CSV
        s12 = f"{d12:.1f}" if d12 > 0 else "0.0"
        s23 = f"{d23:.1f}" if d23 > 0 else "0.0"
        s31 = f"{d31:.1f}" if d31 > 0 else "0.0"

        # === BUTTON COUNT CHECK ===
        actual_button_count = len(button_centers)
        if actual_button_count != expected_button_count:
            msg = f"BUTTON COUNT MISMATCH: Expected {expected_button_count}, Found {actual_button_count}"
            alert_parts.append(msg)
            defect_details.append(msg)
            print(f"🔴 DEFECT DETECTED: {msg}")
            send_D_to_com3('D')

        # === MAXIMUM DISTANCE CHECK (with ±5mm tolerance) ===
        if max_distance > 0 and expected_distance > 0:
            tolerance = 5.0
            min_allowed = expected_distance - tolerance
            max_allowed = expected_distance + tolerance
            
            if not (min_allowed <= max_distance <= max_allowed):
                msg = f"DISTANCE OUT OF RANGE: Max={max_distance:.1f}mm (Expected: {expected_distance:.1f}mm ±5mm)"
                alert_parts.append(msg)
                defect_details.append(msg)
                print(f"🔴 DEFECT DETECTED: {msg}")
                send_D_to_com3('D')

        # === YOLO DEFECT DETECTION ===
        # yolo_defects is a list of tuples: (class_id, confidence)
        for defect_class, confidence in yolo_defects:
            if defect_class == 1:  # defect1
                msg = f"BEND PROUND DEFECT (conf: {confidence:.2f})"
                alert_parts.append(msg)
                defect_details.append(msg)
                print(f"🔴 DEFECT DETECTED: {msg}")
                send_D_to_com3('D')
            elif defect_class == 2:  # defect2
                msg = f"MACHINE DEFECT (conf: {confidence:.2f})"
                alert_parts.append(msg)
                defect_details.append(msg)
                print(f"🔴 DEFECT DETECTED: {msg}")
                send_D_to_com3('D')

        # === COMBINE ALERT MESSAGE ===
        alert_msg = " | ".join(alert_parts) if alert_parts else ""

        # === SEND ALERT TO GUI ===
        if alert_msg:
            #self.alert_signal.emit(alert_msg)

# At the end, return full info including formatted alert
            return {
                "d12": s12,
                "d23": s23,
                "d31": s31,
                "max_distance": f"{max_distance:.1f}",
                "alert": alert_msg,                    # ← this is key
                "defect_count": len(defect_details),
                "defect_details": defect_details,
                "has_defect": len(defect_details) > 0
            }

checker = DistanceChecker()


def check_button_distances(button_centers, mm_per_pixel, yolo_defects, 
                          expected_button_count, expected_distance, parent_window=None):
    """Wrapper function for backward compatibility"""
    return checker.check_and_alert(
        button_centers, 
        mm_per_pixel, 
        yolo_defects,
        expected_button_count,
        expected_distance,
        parent_window
    )