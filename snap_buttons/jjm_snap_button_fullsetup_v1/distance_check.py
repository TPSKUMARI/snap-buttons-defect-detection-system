# distance_check.py
import math
from PySide6.QtCore import QObject, Signal


class DistanceChecker(QObject):
    alert_signal = Signal(str)

    def __init__(self):
        super().__init__()

    def check_and_alert(self, button_centers, mm_per_pixel, num_defects=0, parent_window=None):
        d12 = d23 = d31 = 0.0
        alert_msg = ""

        # === DISTANCE CALCULATION ===
        if mm_per_pixel is not None and len(button_centers) == 3:
            centers = sorted(button_centers, key=lambda c: c[0])
            p12 = math.sqrt((centers[1][0] - centers[0][0])**2 + (centers[1][1] - centers[0][1])**2)
            p23 = math.sqrt((centers[2][0] - centers[1][0])**2 + (centers[2][1] - centers[1][1])**2)
            p31 = math.sqrt((centers[2][0] - centers[0][0])**2 + (centers[2][1] - centers[0][1])**2)

            d12 = p12 * mm_per_pixel
            d23 = p23 * mm_per_pixel
            d31 = p31 * mm_per_pixel

            # Format for CSV — ALWAYS
            s12 = f"{d12:.1f}"
            s23 = f"{d23:.1f}"
            s31 = f"{d31:.1f}"

            # DISTANCE ALERT: only if ≤ 30 mm and NOT in 17–23 mm
            dist_parts = []
            if d12 <= 30.0 and not (17.0 <= d12 <= 23.0):
                dist_parts.append(f"1-2: {d12:.1f}mm")
            if d23 <= 30.0 and not (17.0 <= d23 <= 23.0):
                dist_parts.append(f"2-3: {d23:.1f}mm")
            if d31 <= 30.0 and not (17.0 <= d31 <= 23.0):
                dist_parts.append(f"3-1: {d31:.1f}mm")

            if dist_parts:
                alert_msg = "DISTANCE OUT: " + " | ".join(dist_parts)

        else:
            s12 = s23 = s31 = "0.0"

        # === DEFECT ALERT: ALWAYS IF ANY DEFECT ===
        if num_defects > 0:
            defect_msg = f"DEFECT DETECTED ({num_defects})"
            if alert_msg:
                alert_msg += " | " + defect_msg
            else:
                alert_msg = defect_msg

        # === SEND ALERT TO GUI ===
        if alert_msg:
            self.alert_signal.emit(alert_msg)

        return {
            "d12": s12,
            "d23": s23,
            "d31": s31,
            "alert": alert_msg
        }


checker = DistanceChecker()


def check_button_distances(button_centers, mm_per_pixel, parent_window=None):
    return checker.check_and_alert(button_centers, mm_per_pixel, 0, parent_window)