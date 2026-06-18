from ultralytics import YOLO
import os

# 强制锁定当前文件夹
os.chdir(os.path.dirname(os.path.abspath(__file__)))

if __name__ == '__main__':
    model = YOLO("runs/detect/runs/train/traffic_yolov8/weights/best3.pt")

    model.val(
        data="custom.yaml",
        split="test",
        imgsz=640,
        device=0,
        conf=0.25,
        batch=1
    )