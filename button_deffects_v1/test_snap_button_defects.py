from ultralytics import YOLO
from pathlib import Path

# Load your model
model = YOLO(r'C:\Users\samai\Desktop\button_deffects\best.pt')

# Run inference on folder
results = model.predict(
    source=r'C:\Users\samai\Desktop\button_deffects\test - Copy',
    save=True,              # Save images with detections
    save_txt=True,          # Save results as .txt files
    save_conf=True,         # Save confidences in labels
    conf=0.2,              # Confidence threshold
    iou=0.45,               # NMS IoU threshold
    project='runs/detect',  # Save directory
    name='test',            # Experiment name
)

# Print results for each image
for result in results:
    print(f"\nImage: {result.path}")
    print(f"Detections: {len(result.boxes)}")
    for box in result.boxes:
        cls = int(box.cls[0])
        conf = float(box.conf[0])
        print(f"  Class: {model.names[cls]}, Confidence: {conf:.2f}")