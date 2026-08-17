# color_defect_detector.py
import cv2
import numpy as np

# ==================== CONFIGURATION ====================
COLOR_DIFF_THRESHOLD = 70  # Threshold for plastic button color difference
HUE_WEIGHT = 0.8
SAT_WEIGHT = 1.0
VAL_WEIGHT = 0.5
# ======================================================


class ColorDefectDetector:
    def __init__(self):
        pass
    
    def detect_button_type_automatic(self, img, button_bboxes):
        """
        Analyze buttons to automatically determine if they're metallic or plastic.
        
        Key differences:
        - Metallic: High contrast, bright highlights, dark shadows, grayish tones
        - Plastic: Uniform color, minimal highlights
        """
        if not button_bboxes:
            return 'plastic'
        
        metrics_list = []
        
        for bbox in button_bboxes:
            x1, y1, x2, y2 = map(int, bbox[:4])
            button_roi = img[y1:y2, x1:x2]
            
            if button_roi.size == 0:
                continue
            
            # Convert to different color spaces
            gray_roi = cv2.cvtColor(button_roi, cv2.COLOR_BGR2GRAY)
            hsv_roi = cv2.cvtColor(button_roi, cv2.COLOR_BGR2HSV)
            
            # Calculate metrics
            metrics = {
                'brightness_range': np.max(gray_roi) - np.min(gray_roi),
                'brightness_var': np.var(gray_roi),
                'avg_saturation': np.mean(hsv_roi[:, :, 1]),
                'bright_pixel_ratio': np.sum(gray_roi > 200) / gray_roi.size,
                'dark_pixel_ratio': np.sum(gray_roi < 50) / gray_roi.size,
            }
            
            metrics_list.append(metrics)
        
        if not metrics_list:
            return 'plastic'
        
        # Average metrics across all buttons
        avg_metrics = {
            key: np.mean([m[key] for m in metrics_list])
            for key in metrics_list[0].keys()
        }
        
        # Decision logic
        metallic_score = 0
        
        if avg_metrics['brightness_range'] > 150:
            metallic_score += 3
        if avg_metrics['brightness_var'] > 1500:
            metallic_score += 2
        if avg_metrics['avg_saturation'] < 40:
            metallic_score += 2
        if avg_metrics['bright_pixel_ratio'] > 0.1:
            metallic_score += 2
        if avg_metrics['dark_pixel_ratio'] > 0.05:
            metallic_score += 1
        
        return 'metallic' if metallic_score >= 6 else 'plastic'
    
    def get_average_color(self, img, box):
        """Extract average color from a bounding box region"""
        x1, y1, x2, y2 = map(int, box[:4])
        roi = img[y1:y2, x1:x2]
        
        if roi.size == 0:
            return None
        
        # Convert to HSV for better color comparison
        hsv_roi = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)
        avg_color = np.mean(hsv_roi, axis=(0, 1))
        
        return avg_color
    
    def color_difference(self, color1, color2):
        """Calculate color difference in HSV space with adjustable weights"""
        if color1 is None or color2 is None:
            return 0
        
        # Hue difference (circular, 0-180 range)
        h_diff = min(abs(color1[0] - color2[0]), 180 - abs(color1[0] - color2[0]))
        
        # Saturation and Value differences (0-255 range)
        s_diff = abs(color1[1] - color2[1])
        v_diff = abs(color1[2] - color2[2])
        
        # Weighted combination
        total_diff = (h_diff * HUE_WEIGHT) + (s_diff * SAT_WEIGHT) + (v_diff * VAL_WEIGHT)
        
        return total_diff
    
    def get_local_cloth_color(self, img, button_box, margin=40):
        """
        Get cloth color from area surrounding the button (excluding the button itself)
        """
        bx1, by1, bx2, by2 = map(int, button_box[:4])
        h, w = img.shape[:2]
        
        # Expand the region around button
        x1 = max(0, bx1 - margin)
        y1 = max(0, by1 - margin)
        x2 = min(w, bx2 + margin)
        y2 = min(h, by2 + margin)
        
        # Get the surrounding region
        surrounding_region = img[y1:y2, x1:x2].copy()
        
        # Create mask to exclude button area
        mask = np.ones(surrounding_region.shape[:2], dtype=np.uint8) * 255
        
        # Calculate button position in the surrounding region
        btn_x1 = bx1 - x1
        btn_y1 = by1 - y1
        btn_x2 = bx2 - x1
        btn_y2 = by2 - y1
        
        # Mask out the button area
        mask[btn_y1:btn_y2, btn_x1:btn_x2] = 0
        
        # Convert to HSV
        hsv_region = cv2.cvtColor(surrounding_region, cv2.COLOR_BGR2HSV)
        
        # Calculate average color only from non-button areas
        cloth_pixels = hsv_region[mask > 0]
        
        if len(cloth_pixels) == 0:
            return None
        
        avg_color = np.mean(cloth_pixels, axis=0)
        return avg_color
    
    def detect_color_defects(self, img, button_bboxes, button_type='plastic'):
        """
        Detect color-based defects.
        - Metallic buttons: Always OK (no color check)
        - Plastic buttons: Check color match with cloth
        
        Returns: number of color defects found
        """
        if button_type == 'metallic':
            # All metallic buttons are automatically OK
            return 0
        
        # For plastic buttons, check color difference
        color_defects = 0
        
        for i, bbox in enumerate(button_bboxes, 1):
            button_color = self.get_average_color(img, bbox)
            local_cloth_color = self.get_local_cloth_color(img, bbox, margin=40)
            
            if button_color is None or local_cloth_color is None:
                continue
            
            # Calculate color difference
            diff = self.color_difference(local_cloth_color, button_color)
            
            # Determine if it's a defect
            if diff > COLOR_DIFF_THRESHOLD:
                color_defects += 1
                print(f"  Button {i}: Color defect detected (color_diff={diff:.1f})")
        
        return color_defects


# Global instance
color_detector = ColorDefectDetector()


def check_color_defects(frame, button_bboxes):
    """
    Main function to check for color-based defects.
    Called from main.py during detection.
    Automatically detects button type and checks for color defects.
    
    Args:
        frame: The captured image
        button_bboxes: List of button bounding boxes [(x1,y1,x2,y2), ...]
    
    Returns:
        number of color defects found
    """
    if not button_bboxes or len(button_bboxes) == 0:
        return 0
    
    # Auto-detect button type
    button_type = color_detector.detect_button_type_automatic(frame, button_bboxes)
    print(f"  Auto-detected button type: {button_type.upper()}")
    
    # Check for color defects
    color_defects = color_detector.detect_color_defects(frame, button_bboxes, button_type)
    
    return color_defects