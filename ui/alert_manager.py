import cv2
import numpy as np
import winsound
from datetime import datetime

import config


class AlertManager:
    """区域入侵告警管理器"""

    def __init__(self):
        self.alert_zones = []       # [(x1, y1, x2, y2), ...]
        self.alert_log = []         # 告警历史记录
        self.is_alerting = False
        self.last_alert_time = None
        self.cooldown_seconds = 3   # 告警冷却时间，避免疯狂报警

    def add_zone(self, x1, y1, x2, y2):
        """添加一个告警区域"""
        self.alert_zones.append((min(x1, x2), min(y1, y2), max(x1, x2), max(y1, y2)))

    def clear_zones(self):
        """清空所有告警区域"""
        self.alert_zones.clear()
        self.is_alerting = False

    def check_intrusion(self, boxes, class_names):
        """检查是否有目标进入告警区域"""
        if not self.alert_zones:
            return []

        intrusions = []
        for box, name in zip(boxes, class_names):
            cx = int((box[0] + box[2]) / 2)
            cy = int((box[1] + box[3]) / 2)
            for zone in self.alert_zones:
                if zone[0] <= cx <= zone[2] and zone[1] <= cy <= zone[3]:
                    intrusions.append({"type": name, "x": cx, "y": cy})

        if intrusions:
            now = datetime.now()
            if (self.last_alert_time is None or
                    (now - self.last_alert_time).total_seconds() > self.cooldown_seconds):
                self.is_alerting = True
                self.last_alert_time = now
                alert_record = {
                    "time": now.strftime("%H:%M:%S"),
                    "count": len(intrusions),
                    "types": [i["type"] for i in intrusions]
                }
                self.alert_log.append(alert_record)

                # 播放告警声音
                if config.ALERT_SOUND:
                    try:
                        winsound.Beep(1000, 200)
                    except Exception:
                        pass
        else:
            self.is_alerting = False

        return intrusions

    def draw_zones(self, frame):
        """在画面上绘制告警区域"""
        for zone in self.alert_zones:
            color = (0, 0, 255) if self.is_alerting else (0, 255, 255)
            cv2.rectangle(frame, (zone[0], zone[1]), (zone[2], zone[3]), color, 2)
            label = "⚠ ALERT ZONE" if self.is_alerting else "ALERT ZONE"
            cv2.putText(frame, label, (zone[0], zone[1] - 8),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)
        return frame
