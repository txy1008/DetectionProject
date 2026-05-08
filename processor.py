import cv2
import os
import mysql.connector
import pandas as pd
from datetime import datetime
from ultralytics import YOLO


class DetectionProcessor:
    def __init__(self, model_path="models/yolov8n.pt"):
        self.model = YOLO(model_path)
        self.confirmed_ids = set()
        self.id_buffer = {}
        self.session_records = []

        # 记录本次任务总共保存了多少张图，用于防止文件名重复
        self.save_count = 0

        self.db_config = {
            'host': 'localhost',
            'user': 'root',
            'password': 'Txy20041008',
            'database': 'traffic_system_db'
        }

        # 类别映射
        self.class_mapping = {
            0: "person", 1: "bicycle", 3: "bicycle",
            2: "car", 5: "car", 7: "car"
        }
        self.target_classes = list(self.class_mapping.keys())
        self.session_name = ""
        self.session_path = ""

    def start_session(self):
        """初始化新场次"""
        today = datetime.now().strftime("%Y%m%d")
        os.makedirs("results", exist_ok=True)
        os.makedirs("captures", exist_ok=True)

        existing_reports = [f for f in os.listdir("results")
                            if f.startswith(f"报告_{today}") and f.endswith(".csv")]
        run_index = len(existing_reports) + 1

        self.session_name = f"报告_{today}_第{run_index}次"
        self.session_path = os.path.abspath(f"captures/{self.session_name}")
        os.makedirs(self.session_path, exist_ok=True)

        self.confirmed_ids.clear()
        self.id_buffer.clear()
        self.session_records = []
        self.save_count = 0  # 重置计数器
        return self.session_name

    def process_frame(self, frame, is_image=False):
        """处理图像或视频帧"""
        if is_image:
            results = self.model(frame, classes=self.target_classes, conf=0.4, verbose=False)
        else:
            results = self.model.track(frame, persist=True, classes=self.target_classes,
                                       conf=0.6, iou=0.5,
                                       tracker="bytetrack.yaml", verbose=False)

        annotated_frame = frame.copy()
        new_records = []

        if results[0].boxes is not None:
            boxes = results[0].boxes.xyxy.cpu().numpy()
            clss = results[0].boxes.cls.cpu().numpy().astype(int)
            confs = results[0].boxes.conf.cpu().numpy()

            # 视频模式下获取 ID，单图模式 ID 为 None
            if not is_image and results[0].boxes.id is not None:
                ids = results[0].boxes.id.cpu().numpy().astype(int)
            else:
                ids = [None] * len(boxes)

            for box, raw_id, cls, conf in zip(boxes, ids, clss, confs):
                obj_name = self.class_mapping.get(cls, "unknown")
                display_id = raw_id if raw_id is not None else "IMG"

                should_save = False
                if is_image:
                    should_save = True
                else:
                    if raw_id is not None:
                        self.id_buffer[raw_id] = self.id_buffer.get(raw_id, 0) + 1
                        if self.id_buffer[raw_id] >= 5 and raw_id not in self.confirmed_ids:
                            self.confirmed_ids.add(raw_id)
                            should_save = True

                if should_save:
                    # 关键修改：每保存一张图，计数器加1
                    self.save_count += 1
                    record = self.save_data(frame, box, display_id, obj_name, conf, self.save_count)
                    new_records.append(record)

                color = (0, 255, 0) if obj_name == "person" else (255, 128, 0)
                cv2.rectangle(annotated_frame, (int(box[0]), int(box[1])), (int(box[2]), int(box[3])), color, 2)
                cv2.putText(annotated_frame, f"{obj_name} ID:{display_id}", (int(box[0]), int(box[1] - 10)),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)

        return annotated_frame, new_records

    def save_data(self, frame, box, display_id, obj_name, conf, seq_num):
        """保存截图并存库"""
        cat_dir = os.path.join(self.session_path, obj_name)
        os.makedirs(cat_dir, exist_ok=True)

        now = datetime.now()
        # 关键修改：文件名中加入 seq_num 序号，防止单秒内多个目标互相覆盖
        img_name = f"{obj_name}_ID{display_id}_No{seq_num}_{now.strftime('%H%M%S')}.jpg"
        full_path = os.path.abspath(os.path.join(cat_dir, img_name))

        x1, y1, x2, y2 = map(int, box)
        crop = frame[max(0, y1):y2, max(0, x1):x2]
        cv2.imwrite(full_path, crop)

        try:
            conn = mysql.connector.connect(**self.db_config)
            cursor = conn.cursor()
            sql = "INSERT INTO detections (session_id, obj_id, category, img_name, img_path, confidence, detect_time) VALUES (%s, %s, %s, %s, %s, %s, %s)"
            db_id = int(display_id) if isinstance(display_id, int) else 0
            cursor.execute(sql, (self.session_name, db_id, obj_name, img_name, full_path, float(conf), now))
            conn.commit()
            cursor.close()
            conn.close()
        except:
            pass

        rec = {"ID": display_id, "类别": obj_name, "时间": now.strftime("%H:%M:%S"), "存储路径": full_path}
        self.session_records.append(rec)
        pd.DataFrame(self.session_records).to_csv(f"results/{self.session_name}.csv", index=False, encoding='utf-8-sig')

        return {"id": display_id, "type": obj_name, "time": rec["时间"], "img": img_name}