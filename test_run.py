import cv2
from ultralytics import YOLO

# 1. 加载一个官方预训练模型（它会自动下载）
model = YOLO("yolov8n.pt")

# 2. 打开视频文件（如果你有视频）或者 摄像头（把下面路径换成 0）
# video_path = "test.mp4" # 替换成你的视频路径
cap = cv2.VideoCapture(0) # 0 代表笔记本自带摄像头

while cap.isOpened():
    success, frame = cap.read()
    if success:
        # 3. 对当前帧进行检测
        # classes=[0, 2, 7] 分别代表：人、小汽车、卡车
        results = model.track(frame, persist=True, classes=[0, 2, 7])

        # 4. 在画面上绘制检测结果
        annotated_frame = results[0].plot()

        # 5. 显示画面
        cv2.imshow("YOLOv8 Detection", annotated_frame)

        # 按 'q' 退出
        if cv2.waitKey(1) & 0xFF == ord("q"):
            break
    else:
        break

cap.release()
cv2.destroyAllWindows()