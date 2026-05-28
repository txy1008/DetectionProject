import cv2
import csv
import os
import time
import base64
import numpy as np
from datetime import datetime
from ultralytics import YOLO

from config import CAPTURES_DIR, RESULTS_DIR, MODEL_PATH, TRACKER

print("正在加载 YOLOv8 模型，请稍候...")
model = YOLO(MODEL_PATH)
print("模型加载成功！")


# ── 会话 & 文件管理 ────────────────────────────────────────────────────────────

def get_session_name() -> str:
    """
    生成本次检测的会话名，格式：报告_YYYYMMDD_第N次
    例如：报告_20260526_第1次、报告_20260526_第2次
    """
    today = datetime.now().strftime("%Y%m%d")
    n = 1
    while os.path.exists(os.path.join(CAPTURES_DIR, f"报告_{today}_第{n}次")):
        n += 1
    return f"报告_{today}_第{n}次"


def ensure_class_folder(session_name: str, class_name: str) -> str:
    """
    确保 captures/会话名/类别/ 目录存在，返回该目录的完整路径
    例如：captures/报告_20260526_第1次/person/
    """
    folder = os.path.join(CAPTURES_DIR, session_name, class_name)
    os.makedirs(folder, exist_ok=True)
    return folder


def save_csv(session_name: str, records: list) -> str:
    """
    将检测记录保存为 results/会话名.csv
    CSV 列：ID, 类别, 时间, 存储路径
    返回 CSV 文件的完整路径
    """
    csv_path = os.path.join(RESULTS_DIR, f"{session_name}.csv")
    with open(csv_path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=["ID", "类别", "时间", "存储路径"])
        writer.writeheader()
        writer.writerows(records)
    return csv_path


def crop_and_save(img: np.ndarray, xyxy: list, class_name: str,
                  obj_id: int, class_seq: int, session_name: str) -> str:
    """
    从图像中裁剪目标区域并保存截图。
    文件名格式：{类别}_ID{id}_No{类内序号}_{时间HHMMSS}.jpg
    例如：person_ID1_No1_130044.jpg
    返回截图的完整本地路径（写入 CSV 存储路径列）。
    """
    x1, y1, x2, y2 = [int(v) for v in xyxy]
    crop = img[max(0, y1):max(0, y2), max(0, x1):max(0, x2)]

    t = datetime.now().strftime("%H%M%S")
    folder   = ensure_class_folder(session_name, class_name)
    filename = f"{class_name}_ID{obj_id}_No{class_seq}_{t}.jpg"
    full_path = os.path.join(folder, filename)
    cv2.imwrite(full_path, crop)
    return full_path


# ── 图片检测 ───────────────────────────────────────────────────────────────────

def process_image(img: np.ndarray, conf: float) -> dict:
    """
    对单张图片执行 YOLO 检测。
    - 每个检测目标裁剪保存到 captures/会话名/类别/
    - 生成 CSV 到 results/会话名.csv
    返回字典：session_name, object_count, objects, annotated_img, csv_path
    """
    session_name = get_session_name()
    os.makedirs(os.path.join(CAPTURES_DIR, session_name), exist_ok=True)

    results = model.predict(source=img, conf=conf, verbose=False)
    result  = results[0]

    class_counters  = {}   # 各类别在本次检测中的出现序号
    detected_objects = []
    records          = []

    for i, box in enumerate(result.boxes):
        obj_id     = i + 1
        cls_name   = model.names[int(box.cls[0])]
        confidence = float(box.conf[0])
        xyxy       = box.xyxy[0].tolist()

        class_counters[cls_name] = class_counters.get(cls_name, 0) + 1
        shot_path   = crop_and_save(img, xyxy, cls_name, obj_id,
                                    class_counters[cls_name], session_name)
        detect_time = datetime.now().strftime("%H:%M:%S")

        detected_objects.append({
            "id":         obj_id,
            "class_name": cls_name,
            "confidence": round(confidence, 3),
            "bbox":       [round(x, 1) for x in xyxy],
        })
        records.append({
            "ID":     obj_id,
            "类别":   cls_name,
            "时间":   detect_time,
            "存储路径": shot_path,
        })

    annotated_img = result.plot()
    csv_path      = save_csv(session_name, records)

    return {
        "session_name":  session_name,
        "object_count":  len(detected_objects),
        "objects":       detected_objects,
        "annotated_img": annotated_img,
        "csv_path":      csv_path,
        "records":       records,
    }


# ── 视频检测 ───────────────────────────────────────────────────────────────────

def process_video(input_path: str, conf: float) -> dict:
    """
    对视频进行多目标跟踪（BotSORT）。
    每个 track_id 首次出现时裁剪截图，保存到 captures/会话名/类别/。
    跟踪结果视频保存到 captures/会话名/tracked_*.mp4。
    生成 CSV 到 results/会话名.csv。
    返回字典：session_name, object_count, csv_path, output_filename
    """
    session_name    = get_session_name()
    session_cap_dir = os.path.join(CAPTURES_DIR, session_name)
    os.makedirs(session_cap_dir, exist_ok=True)

    output_filename = f"tracked_{int(time.time())}_{os.path.basename(input_path)}"
    output_path     = os.path.join(session_cap_dir, output_filename)

    cap    = cv2.VideoCapture(input_path)
    width  = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps    = int(cap.get(cv2.CAP_PROP_FPS)) or 25

    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out    = cv2.VideoWriter(output_path, fourcc, fps, (width, height))

    seen_ids       = {}   # track_id -> True，记录已处理过的目标
    class_counters = {}
    records        = []

    print("开始处理视频，请稍候...")
    while cap.isOpened():
        success, frame = cap.read()
        if not success:
            break

        results = model.track(frame, persist=True, tracker=TRACKER,
                               conf=conf, verbose=False)
        result  = results[0]
        out.write(result.plot())

        if result.boxes.id is not None:
            for box in result.boxes:
                track_id = int(box.id[0])
                if track_id not in seen_ids:
                    cls_name = model.names[int(box.cls[0])]
                    xyxy     = box.xyxy[0].tolist()

                    class_counters[cls_name] = class_counters.get(cls_name, 0) + 1
                    shot_path   = crop_and_save(frame, xyxy, cls_name, track_id,
                                                class_counters[cls_name], session_name)
                    detect_time = datetime.now().strftime("%H:%M:%S")

                    seen_ids[track_id] = True
                    records.append({
                        "ID":     track_id,
                        "类别":   cls_name,
                        "时间":   detect_time,
                        "存储路径": shot_path,
                    })

    cap.release()
    out.release()
    print("视频处理完成！")

    csv_path = save_csv(session_name, records)
    return {
        "session_name":   session_name,
        "object_count":   len(records),
        "csv_path":       csv_path,
        "output_filename": output_filename,
        "records":        records,
    }


# ── 摄像头单帧处理 ─────────────────────────────────────────────────────────────

def process_camera_frame(frame: np.ndarray, conf: float, session_name: str,
                          seen_ids: dict, class_counters: dict,
                          records: list, highlight_id: int = None) -> dict:
    """
    处理摄像头的单帧画面。
    seen_ids / class_counters / records 由调用方（WebSocket 处理函数）持有并传入，
    本函数会就地更新这三个对象（新目标会追加进去）。

    返回字典：objects, annotated_frame (base64 JPEG), total_unique, new_record
    """
    results = model.track(frame, persist=True, tracker=TRACKER,
                           conf=conf, verbose=False)
    result  = results[0]

    detected   = []
    new_record = False

    if result.boxes.id is not None:
        for box in result.boxes:
            track_id   = int(box.id[0])
            cls_name   = model.names[int(box.cls[0])]
            confidence = float(box.conf[0])

            if track_id not in seen_ids:
                xyxy = box.xyxy[0].tolist()
                class_counters[cls_name] = class_counters.get(cls_name, 0) + 1
                shot_path   = crop_and_save(frame, xyxy, cls_name, track_id,
                                            class_counters[cls_name], session_name)
                detect_time = datetime.now().strftime("%H:%M:%S")

                seen_ids[track_id] = True
                records.append({
                    "ID":     track_id,
                    "类别":   cls_name,
                    "时间":   detect_time,
                    "存储路径": shot_path,
                })
                new_record = True

            detected.append({
                "id":         track_id,
                "class_name": cls_name,
                "confidence": round(confidence, 3),
            })

    # 每出现新目标，立即更新 CSV
    if new_record:
        save_csv(session_name, records)

    # 将标注帧编码为 base64 JPEG 推送给前端
    if highlight_id is not None:
        annotated = frame.copy()
        if result.boxes.id is not None:
            for box in result.boxes:
                if int(box.id[0]) == highlight_id:
                    x1,y1,x2,y2 = [int(v) for v in box.xyxy[0].tolist()]
                    cls  = model.names[int(box.cls[0])]
                    cval = float(box.conf[0])
                    cv2.rectangle(annotated,(x1,y1),(x2,y2),(0,255,0),3)
                    cv2.putText(annotated,f"id:{highlight_id} {cls} {cval:.2f}",
                               (x1,max(y1-10,15)),cv2.FONT_HERSHEY_SIMPLEX,0.7,(0,255,0),2)
    else:
        annotated = result.plot()
    _, buf    = cv2.imencode('.jpg', annotated, [cv2.IMWRITE_JPEG_QUALITY, 70])
    encoded_frame = base64.b64encode(buf).decode('utf-8')

    return {
        "objects":         detected,
        "annotated_frame": encoded_frame,
        "total_unique":    len(seen_ids),
        "new_record":      new_record,
    }
