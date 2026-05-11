import cv2
import numpy as np
from PySide6.QtWidgets import (QMainWindow, QWidget, QHBoxLayout, QVBoxLayout,
                               QPushButton, QLabel, QTextEdit, QFileDialog,
                               QTableWidget, QTableWidgetItem, QHeaderView,
                               QGroupBox, QGridLayout, QTabWidget, QInputDialog,
                               QMessageBox, QSlider)
from PySide6.QtCore import Qt, Slot
from PySide6.QtGui import QImage, QPixmap

import config
from processor import DetectionProcessor
from ui.video_thread import VideoThread
from ui.history_dialog import HistoryDialog


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(config.WINDOW_TITLE)
        self.resize(config.WINDOW_WIDTH, config.WINDOW_HEIGHT)
        self.setStyleSheet("background-color: #f8f9fa;")

        # --- 核心布局 ---
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        main_layout = QHBoxLayout(main_widget)

        # ========== 左侧：视频显示区 ==========
        left_panel = QVBoxLayout()
        self.video_label = QLabel("等待视频源加载...")
        self.video_label.setAlignment(Qt.AlignCenter)
        self.video_label.setStyleSheet("background-color: #000; border-radius: 10px; color: #aaa; font-size: 18px;")
        self.video_label.setMinimumSize(900, 600)
        left_panel.addWidget(self.video_label)
        main_layout.addLayout(left_panel, 7)

        # ========== 右侧：控制面板 ==========
        right_panel = QVBoxLayout()

        # --- 实时统计看板 ---
        stats_group = QGroupBox("📊 实时统计")
        stats_group.setStyleSheet(
            "QGroupBox { font-size: 16px; font-weight: bold; color: #333; "
            "border: 1px solid #dee2e6; border-radius: 6px; margin-top: 8px; padding-top: 16px; }"
            "QGroupBox::title { subcontrol-origin: margin; left: 10px; }")
        stats_grid = QGridLayout()

        label_style = "font-size: 13px; color: #555;"
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

        stats_grid.addWidget(self._make_label("📊 总计", label_style), 2, 0)
        self.count_total = QLabel("0")
        self.count_total.setAlignment(Qt.AlignCenter)
        self.count_total.setStyleSheet(count_style.format("#2c3e50"))
        stats_grid.addWidget(self.count_total, 3, 0)

        stats_group.setLayout(stats_grid)
        right_panel.addWidget(stats_group)

        # --- 置信度调节 ---
        conf_group = QGroupBox("🎯 置信度阈值")
        conf_group.setStyleSheet(
            "QGroupBox { font-size: 14px; font-weight: bold; color: #333; "
            "border: 1px solid #dee2e6; border-radius: 6px; margin-top: 8px; padding-top: 16px; }"
            "QGroupBox::title { subcontrol-origin: margin; left: 10px; }")
        conf_layout = QHBoxLayout()
        self.conf_slider = QSlider(Qt.Horizontal)
        self.conf_slider.setMinimum(10)
        self.conf_slider.setMaximum(95)
        self.conf_slider.setValue(int(config.CONF_VIDEO * 100))
        self.conf_slider.setTickInterval(5)
        self.conf_slider.setTickPosition(QSlider.TicksBelow)
        self.conf_slider.setStyleSheet(
            "QSlider::groove:horizontal { height: 6px; background: #ddd; border-radius: 3px; }"
            "QSlider::handle:horizontal { width: 16px; margin: -5px 0; background: #0078D7; border-radius: 8px; }"
            "QSlider::sub-page:horizontal { background: #0078D7; border-radius: 3px; }")
        self.conf_label = QLabel(f"{config.CONF_VIDEO:.2f}")
        self.conf_label.setStyleSheet("font-size: 18px; font-weight: bold; color: #0078D7; min-width: 40px;")
        self.conf_label.setAlignment(Qt.AlignCenter)
        self.conf_slider.valueChanged.connect(self._on_conf_changed)
        conf_layout.addWidget(self.conf_slider)
        conf_layout.addWidget(self.conf_label)
        conf_group.setLayout(conf_layout)
        right_panel.addWidget(conf_group)

        # --- 选项卡：明细 / 日志 ---
        self.tabs = QTabWidget()
        self.tabs.setStyleSheet("QTabWidget::pane { border: 1px solid #dee2e6; }")

        # Tab 1: 检测明细
        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["ID", "类别", "发现时间", "文件名"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.setStyleSheet("background-color: white;")
        self.tabs.addTab(self.table, "📝 检测明细")

        # Tab 2: 系统日志
        self.log_output = QTextEdit()
        self.log_output.setReadOnly(True)
        self.log_output.setPlaceholderText("系统运行日志...")
        self.log_output.setStyleSheet("background-color: white; font-family: Consolas;")
        self.tabs.addTab(self.log_output, "📋 系统日志")

        right_panel.addWidget(self.tabs)

        # --- 功能按钮 ---
        btn_style = ("QPushButton { padding: 10px; font-size: 14px; "
                     "background-color: #0078D7; color: white; border-radius: 4px; }"
                     "QPushButton:hover { background-color: #005a9e; }")
        btn_stop_style = ("QPushButton { padding: 10px; font-size: 14px; "
                          "background-color: #d83b01; color: white; border-radius: 4px; }"
                          "QPushButton:hover { background-color: #a02d01; }")

        self.btn_img = QPushButton("📸 检测单张图片")
        self.btn_video = QPushButton("🎥 上传视频检测")
        self.btn_cam = QPushButton("🌐 开启实时摄像头")
        self.btn_heatmap = QPushButton("🔥 热力图模式")
        self.btn_stop = QPushButton("🛑 停止运行")

        btn_toggle_style = ("QPushButton { padding: 10px; font-size: 14px; "
                            "background-color: #6c757d; color: white; border-radius: 4px; }"
                            "QPushButton:hover { background-color: #545b62; }")

        for b in [self.btn_img, self.btn_video, self.btn_cam]:
            b.setStyleSheet(btn_style)
            right_panel.addWidget(b)
        self.btn_heatmap.setStyleSheet(btn_toggle_style)
        self.btn_heatmap.setCheckable(True)
        right_panel.addWidget(self.btn_heatmap)

        self.btn_history = QPushButton("📈 历史数据分析")
        self.btn_history.setStyleSheet(btn_toggle_style)
        right_panel.addWidget(self.btn_history)

        self.btn_alert = QPushButton("⚠ 设置告警区域")
        self.btn_alert.setStyleSheet(
            "QPushButton { padding: 10px; font-size: 14px; "
            "background-color: #ffc107; color: #333; border-radius: 4px; }"
            "QPushButton:hover { background-color: #e0a800; }")
        right_panel.addWidget(self.btn_alert)

        self.btn_stop.setStyleSheet(btn_stop_style)
        right_panel.addWidget(self.btn_stop)

        main_layout.addLayout(right_panel, 3)

        # --- 信号绑定 ---
        self.btn_cam.clicked.connect(lambda: self.start_task(0))
        self.btn_video.clicked.connect(self.select_video)
        self.btn_img.clicked.connect(self.select_image)
        self.btn_heatmap.clicked.connect(self.toggle_heatmap)
        self.btn_history.clicked.connect(self.open_history)
        self.btn_alert.clicked.connect(self.setup_alert_zone)
        self.btn_stop.clicked.connect(self.stop_all)

        self.thread = None
        self.processor = DetectionProcessor()  # 用于单图检测
        self.show_heatmap = False

    # ==================== 业务逻辑 ====================

    def select_video(self):
        path, _ = QFileDialog.getOpenFileName(self, "选择视频文件", "", "Videos (*.mp4 *.avi *.mkv)")
        if path:
            self.start_task(path)

    def select_image(self):
        path, _ = QFileDialog.getOpenFileName(self, "选择单张图片", "", "Images (*.jpg *.png *.bmp)")
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
        self.log_output.append(f"✅ 任务已启动，源: {source}")

    def stop_all(self):
        if self.thread:
            self._show_summary(self.thread.processor)
            self._auto_export_word(self.thread.processor)
            self.thread.stop()
            self.thread = None
            self.video_label.setText("任务已停止")

    # ==================== 槽函数 ====================

    @Slot(np.ndarray)
    def update_image(self, frame):
        # 热力图叠加
        if self.show_heatmap and self.thread and self.thread.processor:
            frame = self.thread.processor.get_heatmap_overlay(frame)
        h, w, c = frame.shape
        q_img = QImage(frame.data, w, h, w * c, QImage.Format_RGB888).rgbSwapped()
        self.video_label.setPixmap(QPixmap.fromImage(q_img).scaled(
            self.video_label.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation))

    @Slot(dict)
    def update_stats(self, stats):
        self.count_car.setText(str(stats.get("car", 0)))
        self.count_bicycle.setText(str(stats.get("bicycle", 0)))
        self.count_person.setText(str(stats.get("person", 0)))
        total = stats.get("car", 0) + stats.get("bicycle", 0) + stats.get("person", 0)
        self.count_total.setText(str(total))

    @Slot(list)
    def add_table_record(self, records):
        for r in records:
            self.table.insertRow(0)
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
            self._auto_export_word(self.thread.processor)
        self.video_label.setText("视频播放完毕")
        self.log_output.append("✅ 视频源已结束，检测已自动停止")

    # ==================== 辅助方法 ====================

    def open_history(self):
        dialog = HistoryDialog(self)
        dialog.exec()

    def setup_alert_zone(self):
        """设置告警区域 - 通过输入坐标比例"""
        processor = self._get_active_processor()
        if not processor:
            QMessageBox.information(self, "提示", "请先启动检测任务")
            return

        text, ok = QInputDialog.getText(
            self, "设置告警区域",
            "输入区域坐标比例 (x1,y1,x2,y2)\n"
            "例如: 0.2,0.3,0.8,0.7\n"
            "表示画面 20%~80% 宽度, 30%~70% 高度\n"
            "输入 clear 清除所有区域",
            text="0.2,0.3,0.8,0.7")

        if ok and text:
            if text.strip().lower() == "clear":
                processor.alert_manager.clear_zones()
                self.log_output.append("⚠ 已清除所有告警区域")
                return
            try:
                parts = [float(x.strip()) for x in text.split(",")]
                if len(parts) != 4:
                    raise ValueError
                h = self.video_label.pixmap().height() if self.video_label.pixmap() else 720
                w = self.video_label.pixmap().width() if self.video_label.pixmap() else 1280
                # 使用实际视频尺寸
                if processor.heatmap_data is not None:
                    h, w = processor.heatmap_data.shape
                x1, y1 = int(parts[0] * w), int(parts[1] * h)
                x2, y2 = int(parts[2] * w), int(parts[3] * h)
                processor.alert_manager.add_zone(x1, y1, x2, y2)
                self.log_output.append(f"⚠ 告警区域已设置: ({x1},{y1})-({x2},{y2})")
            except (ValueError, IndexError):
                QMessageBox.warning(self, "格式错误", "请输入 4 个 0~1 之间的数字，用逗号分隔")

    def _get_active_processor(self):
        """获取当前活动的 processor"""
        if self.thread and self.thread.processor:
            return self.thread.processor
        return None

    def toggle_heatmap(self):
        self.show_heatmap = self.btn_heatmap.isChecked()
        status = "开启" if self.show_heatmap else "关闭"
        self.log_output.append(f"🔥 热力图模式已{status}")

    def _on_conf_changed(self, value):
        """置信度滑块变化时实时更新"""
        conf = value / 100.0
        self.conf_label.setText(f"{conf:.2f}")
        # 更新当前活动的 processor
        if self.thread and self.thread.processor:
            self.thread.processor.conf_threshold = conf
        self.processor.conf_threshold = conf

    def _reset_stats(self):
        self.count_car.setText("0")
        self.count_bicycle.setText("0")
        self.count_person.setText("0")
        self.count_total.setText("0")
        self.table.setRowCount(0)

    def _show_summary(self, processor):
        s = processor.get_summary()
        if s["total"] > 0:
            self.log_output.append("\n" + "=" * 40)
            self.log_output.append(f"📋 场次: {s['session']}")
            self.log_output.append(f"   机动车: {s['car']}  非机动车: {s['bicycle']}  行人: {s['person']}")
            self.log_output.append(f"   总计: {s['total']} 个目标  |数据库: {s['db_status']}")
            self.log_output.append(f"   置信度阈值: {self.conf_slider.value() / 100:.2f}")
            self.log_output.append("=" * 40)

    def _auto_export_word(self, processor):
        """自动导出 Word 报告"""
        try:
            path = processor.generate_word_report()
            if path:
                self.log_output.append(f"📄 Word 报告已自动生成: {path}")
        except Exception as e:
            self.log_output.append(f"⚠ Word 报告生成失败: {e}")

    @staticmethod
    def _make_label(text, style):
        lbl = QLabel(text)
        lbl.setAlignment(Qt.AlignCenter)
        lbl.setStyleSheet(style)
        return lbl
