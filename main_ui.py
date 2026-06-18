import sys
import cv2
import numpy as np
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QHBoxLayout,
                               QVBoxLayout, QPushButton, QLabel, QTextEdit,
                               QFileDialog, QTableWidget, QTableWidgetItem,
                               QHeaderView, QGroupBox, QGridLayout)
from PySide6.QtCore import Qt, QThread, Signal, Slot
from PySide6.QtGui import QImage, QPixmap
from processor import DetectionProcessor


# 视频处理子线程
class VideoThread(QThread):
    change_pixmap_signal = Signal(np.ndarray)
    new_record_signal = Signal(list)
    stats_signal = Signal(dict)
    finished_signal = Signal()

    def __init__(self, source=0):
        super().__init__()
        self.source = source
        self.running = True
        self.processor = DetectionProcessor()

    def run(self):
        self.processor.start_session()
        cap = cv2.VideoCapture(self.source)
        while self.running:
            ret, frame = cap.read()
            if ret:
                processed_frame, new_recs = self.processor.process_frame(frame)
                self.change_pixmap_signal.emit(processed_frame)
                self.stats_signal.emit(self.processor.get_stats())
                if new_recs:
                    self.new_record_signal.emit(new_recs)
            else:
                break
        cap.release()
        self.finished_signal.emit()

    def stop(self):
        self.running = False
        self.wait()


# 主窗口界面
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("智慧路口视频监控系统专业版 v4.0")
        self.resize(1400, 900)
        self.setStyleSheet("background-color: #f8f9fa;")

        # --- 核心布局 ---
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        main_layout = QHBoxLayout(main_widget)

        # 1. 左侧：视频显示
        self.video_label = QLabel("等待视频源加载...")
        self.video_label.setAlignment(Qt.AlignCenter)
        self.video_label.setStyleSheet("background-color: #000; border-radius: 10px; color: #555;")
        self.video_label.setMinimumWidth(950)
        main_layout.addWidget(self.video_label, 7)

        # 2. 右侧：控制面板
        right_panel = QVBoxLayout()

        # 实时统计看板
        stats_group = QGroupBox("📊 实时统计")
        stats_group.setStyleSheet("QGroupBox { font-size: 16px; font-weight: bold; color: #333; border: 1px solid #dee2e6; border-radius: 6px; margin-top: 8px; padding-top: 16px; } QGroupBox::title { subcontrol-origin: margin; left: 10px; }")
        stats_grid = QGridLayout()

        label_style = "font-size: 14px; color: #555;"
        count_style = "font-size: 28px; font-weight: bold; color: {}; background-color: white; border-radius: 4px; padding: 4px;"

        stats_grid.addWidget(self._make_label("🚗 机动车", label_style), 0, 0)
        self.count_car = QLabel("0")
        self.count_car.setAlignment(Qt.AlignCenter)
        self.count_car.setStyleSheet(count_style.format("#e67e22"))
        stats_grid.addWidget(self.count_car, 1, 0)

        stats_grid.addWidget(self._make_label("🚲 非机动车", label_style), 0, 1)
        self.count_bicycle = QLabel("0")
        self.count_bicycle.setAlignment(Qt.AlignCenter)
        self.count_bicycle.setStyleSheet(count_style.format("#3498db"))
        stats_grid.addWidget(self.count_bicycle, 1, 1)

        stats_grid.addWidget(self._make_label("🚶 行人", label_style), 0, 2)
        self.count_person = QLabel("0")
        self.count_person.setAlignment(Qt.AlignCenter)
        self.count_person.setStyleSheet(count_style.format("#2ecc71"))
        stats_grid.addWidget(self.count_person, 1, 2)

        stats_group.setLayout(stats_grid)
        right_panel.addWidget(stats_group)

        self.title_label = QLabel("📝 检测明细")
        self.title_label.setStyleSheet("font-size: 16px; font-weight: bold; color: #333; margin-top: 8px;")
        right_panel.addWidget(self.title_label)

        # 实时数据表格
        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["ID", "类别", "发现时间", "文件名"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.setStyleSheet("background-color: white; border: 1px solid #dee2e6;")
        right_panel.addWidget(self.table)

        # 系统日志
        self.log_output = QTextEdit()
        self.log_output.setReadOnly(True)
        self.log_output.setMaximumHeight(150)
        self.log_output.setPlaceholderText("系统运行日志将显示在这里...")
        right_panel.addWidget(self.log_output)

        # 功能按钮
        btn_style = "QPushButton { padding: 10px; font-size: 14px; background-color: #0078D7; color: white; border-radius: 4px; } QPushButton:hover { background-color: #005a9e; }"
        self.btn_img = QPushButton("📸 检测单张图片")
        self.btn_video = QPushButton("🎥 上传视频检测")
        self.btn_cam = QPushButton("🌐 开启实时摄像头")
        self.btn_stop = QPushButton("🛑 停止运行")

        for b in [self.btn_img, self.btn_video, self.btn_cam, self.btn_stop]:
            b.setStyleSheet(btn_style)
            if b == self.btn_stop: b.setStyleSheet(
                "background-color: #d83b01; color: white; padding: 10px; border-radius: 4px;")
            right_panel.addWidget(b)

        main_layout.addLayout(right_panel, 3)

        # --- 信号绑定 ---
        self.btn_cam.clicked.connect(lambda: self.start_task(0))
        self.btn_video.clicked.connect(self.select_video)
        self.btn_img.clicked.connect(self.select_image)
        self.btn_stop.clicked.connect(self.stop_all)

        self.thread = None
        self.processor = DetectionProcessor()  # 用于单图检测

    def select_video(self):
        path, _ = QFileDialog.getOpenFileName(self, "选择视频文件", "", "Videos (*.mp4 *.avi)")
        if path: self.start_task(path)

    def select_image(self):
        path, _ = QFileDialog.getOpenFileName(self, "选择单张图片", "", "Images (*.jpg *.png)")
        if path:
            self.processor.start_session()
            frame = cv2.imread(path)
            res_frame, records = self.processor.process_frame(frame, is_image=True)
            self.update_image(res_frame)
            self.add_table_record(records)
            self.update_stats(self.processor.get_stats())
            self._show_summary(self.processor)
            self.log_output.append(f"单图检测完成: {path}")

    def start_task(self, source):
        self.stop_all()
        self._reset_stats()
        self.thread = VideoThread(source)
        self.thread.change_pixmap_signal.connect(self.update_image)
        self.thread.new_record_signal.connect(self.add_table_record)
        self.thread.stats_signal.connect(self.update_stats)
        self.thread.finished_signal.connect(self.on_task_finished)
        self.thread.start()
        self.log_output.append(f"任务已启动，源: {source}")

    def stop_all(self):
        if self.thread:
            self._show_summary(self.thread.processor)
            self.thread.stop()
            self.video_label.setText("任务已停止")

    @Slot(np.ndarray)
    def update_image(self, frame):
        h, w, c = frame.shape
        q_img = QImage(frame.data, w, h, w * c, QImage.Format_RGB888).rgbSwapped()
        self.video_label.setPixmap(QPixmap.fromImage(q_img).scaled(
            self.video_label.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation))

    @Slot(dict)
    def update_stats(self, stats):
        self.count_car.setText(str(stats.get("car", 0)))
        self.count_bicycle.setText(str(stats.get("bicycle", 0)))
        self.count_person.setText(str(stats.get("person", 0)))

    @Slot(list)
    def add_table_record(self, records):
        for r in records:
            self.table.insertRow(0)  # 将新纪录插在第一行
            self.table.setItem(0, 0, QTableWidgetItem(str(r['id'])))
            self.table.setItem(0, 1, QTableWidgetItem(r['type']))
            self.table.setItem(0, 2, QTableWidgetItem(r['time']))
            self.table.setItem(0, 3, QTableWidgetItem(r['img']))
            self.log_output.append(f"检测到新目标: {r['type']} (ID: {r['id']})")

    @Slot()
    def on_task_finished(self):
        """视频播放结束后自动处理"""
        if self.thread:
            self._show_summary(self.thread.processor)
        self.video_label.setText("视频播放完毕")
        self.log_output.append("✅ 视频源已结束，检测已自动停止")

    def _reset_stats(self):
        self.count_car.setText("0")
        self.count_bicycle.setText("0")
        self.count_person.setText("0")
        self.table.setRowCount(0)

    def _show_summary(self, processor):
        s = processor.get_summary()
        if s["total"] > 0:
            self.log_output.append("\n" + "=" * 35)
            self.log_output.append(f"📋 场次: {s['session']}")
            self.log_output.append(f"   机动车: {s['car']}  非机动车: {s['bicycle']}  行人: {s['person']}")
            self.log_output.append(f"   总计: {s['total']} 个目标  |数据库: {s['db_status']}")
            self.log_output.append("=" * 35)

    @staticmethod
    def _make_label(text, style):
        lbl = QLabel(text)
        lbl.setAlignment(Qt.AlignCenter)
        lbl.setStyleSheet(style)
        return lbl


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())