import argparse
from ultralytics import YOLO
import cv2
import os

def parse_args():
    parser = argparse.ArgumentParser(description="YOLOv8 交通目标检测-视频推理")
    parser.add_argument("--model-path", type=str, default="runs/detect/runs/train/traffic_yolov8/weights/best3.pt")
    parser.add_argument("--video-path", type=str, required=True, help="测试视频路径")
    parser.add_argument("--conf", type=float, default=0.25, help="置信度阈值")
    parser.add_argument("--iou", type=float, default=0.45, help="NMS IoU阈值")
    parser.add_argument("--save-path", type=str, default="infer_video_result.mp4", help="结果视频保存路径")
    return parser.parse_args()

def infer_video(model, video_path, conf, iou, save_path):
    # 打开视频
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise FileNotFoundError(f"视频文件无法打开：{video_path}")
    
    # 获取视频参数
    fps = int(cap.get(cv2.CAP_PROP_FPS))
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    out = cv2.VideoWriter(save_path, fourcc, fps, (width, height))
    
    print(f"📽️ 开始处理视频：{video_path} (FPS: {fps}, 分辨率: {width}x{height})")
    frame_idx = 0
    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break
        
        # 推理
        results = model(frame, conf=conf, iou=iou)
        
        # 计数
        count = {"person": 0, "car": 0, "bicycle": 0}
        for box in results[0].boxes:
            cls_id = int(box.cls[0].item())
            if cls_id == 0:
                count["person"] += 1
            elif cls_id == 1:
                count["car"] += 1
            elif cls_id == 2:
                count["bicycle"] += 1
        
        # 可视化
        frame_draw = results[0].plot()
        cv2.putText(frame_draw, f"Frame: {frame_idx}", (20, 50), 
                    cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
        cv2.putText(frame_draw, f"Person: {count['person']}", (20, 80), 
                    cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
        cv2.putText(frame_draw, f"Car: {count['car']}", (20, 110), 
                    cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
        cv2.putText(frame_draw, f"Bicycle: {count['bicycle']}", (20, 140), 
                    cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
        
        # 写入帧
        out.write(frame_draw)
        frame_idx += 1
        
        # 实时显示（可选）
        cv2.imshow("Video Infer", frame_draw)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break
    
    # 释放资源
    cap.release()
    out.release()
    cv2.destroyAllWindows()
    print(f"✅ 视频推理完成！结果保存至：{save_path} (总帧数：{frame_idx})")

if __name__ == "__main__":
    args = parse_args()
    model = YOLO(args.model_path)
    infer_video(model, args.video_path, args.conf, args.iou, args.save_path)