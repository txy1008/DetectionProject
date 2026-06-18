from ultralytics import YOLO
import cv2

# 加载模型
model = YOLO("runs/detect/runs/train/traffic_yolov8/weights/best3.pt")

img_path = "test0.png"
img = cv2.imread(img_path)

# 推理：降低置信度 + 开启NMS，解决漏检和重复框
#results = model(img, conf=0.15, iou=0.3)
results = model(img, conf=0.1, iou=0.2)

count = {"person": 0, "car": 0, "bicycle": 0}
for box in results[0].boxes:
    cls_id = int(box.cls[0].item())
    if cls_id == 0:
        count["person"] += 1
    elif cls_id == 1:
        count["car"] += 1
    elif cls_id == 2:
        count["bicycle"] += 1

img_draw = results[0].plot()
cv2.putText(img_draw, f"Person: {count['person']}", (20, 50), cv2.FONT_HERSHEY_SIMPLEX, 1.5, (0, 0, 255), 3)
cv2.putText(img_draw, f"Car: {count['car']}", (20, 100), cv2.FONT_HERSHEY_SIMPLEX, 1.5, (0, 0, 255), 3)
cv2.putText(img_draw, f"Bicycle: {count['bicycle']}", (20, 150), cv2.FONT_HERSHEY_SIMPLEX, 1.5, (0, 0, 255), 3)

cv2.imshow("result", img_draw)
cv2.waitKey(0)
cv2.destroyAllWindows()
cv2.imwrite("result_image.jpg", img_draw)

print("✅ 计数完成！")
print(f"行人: {count['person']}, 汽车: {count['car']}, 非机动车: {count['bicycle']}")