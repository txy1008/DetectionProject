import cv2
import os
import numpy as np
import mysql.connector
import pandas as pd
from datetime import datetime
from ultralytics import YOLO

import config
from ui.alert_manager import AlertManager


class DetectionProcessor:
    def __init__(self):
        self.model = YOLO(config.MODEL_PATH)
        self.confirmed_ids = set()
        self.id_buffer = {}
        self.session_records = []

        self.save_count = 0
        self.counters = {"car": 0, "bicycle": 0, "person": 0}
        self.db_connected = True

        self.db_config = config.DB_CONFIG
        self.class_mapping = config.CLASS_MAPPING
        self.target_classes = config.TARGET_CLASSES
        self.session_name = ""
        self.session_path = ""

        # 越线计数相关
        self.track_history = {}   # {id: [(cx, cy), ...]}
        self.line_y = None        # 检测线 Y 坐标
        self.crossed_ids = set()  # 已越线的 ID
        self.line_counts = {"up": 0, "down": 0}  # 上行/下行计数

        # 热力图数据
        self.heatmap_data = None

        # 速度估计相关 (像素/帧)
        self.speed_estimates = {}  # {id: speed_px_per_frame}
        self.fps_estimate = 15    # 默认 FPS——处理帧率

        # 告警管理器
        self.alert_manager = AlertManager()

    def start_session(self):
        """初始化新场次"""
        today = datetime.now().strftime("%Y%m%d")
        os.makedirs(config.RESULTS_DIR, exist_ok=True)
        os.makedirs(config.CAPTURES_DIR, exist_ok=True)

        existing_reports = [f for f in os.listdir(config.RESULTS_DIR)
                            if f.startswith(f"报告_{today}") and f.endswith(".csv")]
        run_index = len(existing_reports) + 1

        self.session_name = f"报告_{today}_第{run_index}次"
        self.session_path = os.path.abspath(f"{config.CAPTURES_DIR}/{self.session_name}")
        os.makedirs(self.session_path, exist_ok=True)

        self.confirmed_ids.clear()
        self.id_buffer.clear()
        self.session_records = []
        self.save_count = 0
        self.counters = {"car": 0, "bicycle": 0, "person": 0}
        self.line_counts = {"up": 0, "down": 0}
        self.crossed_ids.clear()
        self.track_history.clear()
        self.heatmap_data = None
        self.speed_estimates.clear()
        self.db_connected = True
        return self.session_name

    def process_frame(self, frame, is_image=False):
        """处理图像或视频帧"""
        h, w = frame.shape[:2]

        # 初始化热力图数据
        if self.heatmap_data is None:
            self.heatmap_data = np.zeros((h, w), dtype=np.float32)

        # 设置越线检测线位置
        if self.line_y is None:
            self.line_y = int(h * config.LINE_POSITION_RATIO)

        if is_image:
            results = self.model(frame, classes=self.target_classes, conf=config.CONF_IMAGE, verbose=False)
        else:
            results = self.model.track(frame, persist=True, classes=self.target_classes,
                                       conf=config.CONF_VIDEO, iou=config.IOU_THRESHOLD,
                                       tracker="bytetrack.yaml", verbose=False)

        annotated_frame = frame.copy()
        new_records = []

        # 绘制越线检测线
        if not is_image:
            cv2.line(annotated_frame, (0, self.line_y), (w, self.line_y), (0, 0, 255), 2)
            cv2.putText(annotated_frame, f"UP:{self.line_counts['up']} DOWN:{self.line_counts['down']}",
                        (10, self.line_y - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)

        if results[0].boxes is not None:
            boxes = results[0].boxes.xyxy.cpu().numpy()
            clss = results[0].boxes.cls.cpu().numpy().astype(int)
            confs = results[0].boxes.conf.cpu().numpy()

            if not is_image and results[0].boxes.id is not None:
                ids = results[0].boxes.id.cpu().numpy().astype(int)
            else:
                ids = [None] * len(boxes)

            for box, raw_id, cls, conf in zip(boxes, ids, clss, confs):
                obj_name = self.class_mapping.get(cls, "unknown")
                display_id = raw_id if raw_id is not None else "IMG"

                # 计算目标中心点
                cx = int((box[0] + box[2]) / 2)
                cy = int((box[1] + box[3]) / 2)

                # 更新热力图
                self.heatmap_data[max(0, int(box[1])):min(h, int(box[3])),
                                  max(0, int(box[0])):min(w, int(box[2]))] += 1

                # 越线检测（视频模式）
                if not is_image and raw_id is not None:
                    if raw_id not in self.track_history:
                        self.track_history[raw_id] = []
                    self.track_history[raw_id].append((cx, cy))

                    if len(self.track_history[raw_id]) >= 2 and raw_id not in self.crossed_ids:
                        prev_y = self.track_history[raw_id][-2][1]
                        curr_y = cy
                        if prev_y < self.line_y <= curr_y:
                            self.line_counts["down"] += 1
                            self.crossed_ids.add(raw_id)
                        elif prev_y > self.line_y >= curr_y:
                            self.line_counts["up"] += 1
                            self.crossed_ids.add(raw_id)

                    # 速度估计：取最近 5 帧的平均位移
                    hist = self.track_history[raw_id]
                    if len(hist) >= 5:
                        dx = hist[-1][0] - hist[-5][0]
                        dy = hist[-1][1] - hist[-5][1]
                        dist = (dx ** 2 + dy ** 2) ** 0.5
                        speed_pf = dist / 5  # 像素/帧
                        self.speed_estimates[raw_id] = speed_pf

                should_save = False
                if is_image:
                    should_save = True
                else:
                    if raw_id is not None:
                        self.id_buffer[raw_id] = self.id_buffer.get(raw_id, 0) + 1
                        if self.id_buffer[raw_id] >= config.STABLE_FRAMES and raw_id not in self.confirmed_ids:
                            self.confirmed_ids.add(raw_id)
                            should_save = True

                if should_save:
                    self.save_count += 1
                    if obj_name in self.counters:
                        self.counters[obj_name] += 1
                    record = self.save_data(frame, box, display_id, obj_name, conf, self.save_count)
                    new_records.append(record)

                # 绘制检测框
                color_map = {"person": (0, 255, 0), "car": (255, 128, 0), "bicycle": (255, 200, 0)}
                color = color_map.get(obj_name, (128, 128, 128))
                cv2.rectangle(annotated_frame, (int(box[0]), int(box[1])), (int(box[2]), int(box[3])), color, 2)
                label = f"{obj_name} ID:{display_id} {conf:.2f}"
                # 显示速度估计
                if raw_id is not None and raw_id in self.speed_estimates:
                    spd = self.speed_estimates[raw_id]
                    label += f" v:{spd:.1f}px/f"
                cv2.putText(annotated_frame, label, (int(box[0]), int(box[1] - 10)),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)

            # 区域入侵检测
            if config.ALERT_ENABLED:
                class_names = [self.class_mapping.get(c, "unknown") for c in clss]
                self.alert_manager.check_intrusion(boxes, class_names)

        # 绘制告警区域
        annotated_frame = self.alert_manager.draw_zones(annotated_frame)

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
        except Exception as e:
            self.db_connected = False
            print(f"[数据库] 写入失败: {e}")

        rec = {"ID": display_id, "类别": obj_name, "时间": now.strftime("%H:%M:%S"), "存储路径": full_path}
        self.session_records.append(rec)
        pd.DataFrame(self.session_records).to_csv(
            f"{config.RESULTS_DIR}/{self.session_name}.csv", index=False, encoding='utf-8-sig')

        return {"id": display_id, "type": obj_name, "time": rec["时间"], "img": img_name}

    def get_stats(self):
        """返回当前场次的实时统计数据"""
        return {
            **self.counters,
            "line_up": self.line_counts["up"],
            "line_down": self.line_counts["down"]
        }

    def get_summary(self):
        """返回场次结束时的统计摘要"""
        total = sum(self.counters.values())
        return {
            "session": self.session_name,
            "total": total,
            "car": self.counters["car"],
            "bicycle": self.counters["bicycle"],
            "person": self.counters["person"],
            "line_up": self.line_counts["up"],
            "line_down": self.line_counts["down"],
            "db_status": "已连接" if self.db_connected else "未连接(仅CSV)"
        }

    def get_heatmap_overlay(self, frame):
        """生成热力图叠加层"""
        if self.heatmap_data is None:
            return frame
        heatmap_norm = cv2.normalize(self.heatmap_data, None, 0, 255, cv2.NORM_MINMAX)
        heatmap_color = cv2.applyColorMap(heatmap_norm.astype(np.uint8), cv2.COLORMAP_JET)
        overlay = cv2.addWeighted(frame, 0.6, heatmap_color, 0.4, 0)
        return overlay