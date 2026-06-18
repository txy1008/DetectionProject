from ultralytics import YOLO

if __name__ == '__main__':
    model = YOLO("weights/yolov8s.pt")

    model.train(
        data="custom.yaml",
        epochs=200,    
        imgsz=640,
        batch=8,     
        device=0,
        workers=0,            # Windows系统必须设0，防止多进程报错
        project="runs/train",
        name="traffic_yolov8",
        exist_ok=True,
        amp=False,            # 关闭混合精度，减少显存占用
        patience=50,

        # 余弦退火学习率
        cos_lr=True,
        lr0=0.01,
        lrf=0.01,

        # 完整数据增强组合
        mosaic=1.0,
        mixup=0.1,
        copy_paste=0.1,
        hsv_h=0.015,
        hsv_s=0.7,
        hsv_v=0.4,
        degrees=10.0,
        perspective=0.001,
        flipud=0.2,
        fliplr=0.5,
        scale=0.5,
        shear=2.0,
        translate=0.1
    )