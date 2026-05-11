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

        # ========== 左侧：显示区 ==========
        left_panel = QVBoxLayout()

        # 视频模式显示区（单帧）
        self.video_label = QLabel("等待视频源加载...")
        self.video_label.setAlignment(Qt.AlignCenter)
        self.video_label.setStyleSheet("background-color: #000; border-radius: 10px; color: #aaa; font-size: 18px;")
        self.video_label.setMinimumSize(900, 600)
        left_panel.addWidget(self.video_label)

        # 图片对比模式显示区（原图 + 检测图）
        self.img_compare_widget = QWidget()
        img_compare_layout = QVBoxLayout(self.img_compare_widget)
        img_compare_layout.setContentsMargins(0, 0, 0, 0)
        img_compare_layout.setSpacing(2)

        title_style = "font-size: 12px; font-weight: bold; color: #666; margin: 0; padding: 0;"

        lbl_orig_title = QLabel("▶ 原图")
        lbl_orig_title.setStyleSheet(title_style)
        lbl_orig_title.setAlignment(Qt.AlignLeft)
        lbl_orig_title.setFixedHeight(18)
        img_compare_layout.addWidget(lbl_orig_title)

        self.img_original_label = QLabel()
        self.img_original_label.setAlignment(Qt.AlignCenter)
        self.img_original_label.setStyleSheet("background-color: #1a1a1a; border-radius: 4px;")
        img_compare_layout.addWidget(self.img_original_label, 1)

        # 检测结果标题行（标题 + 显示全部按钮）
        detect_title_row = QHBoxLayout()
        detect_title_row.setContentsMargins(0, 0, 0, 0)
        self.lbl_detect_title = QLabel("▶ 检测结果（点击表格行筛选目标）")
        self.lbl_detect_title.setStyleSheet(title_style)
        self.lbl_detect_title.setFixedHeight(18)
        detect_title_row.addWidget(self.lbl_detect_title)
        self.btn_show_all = QPushButton("显示全部")
        self.btn_show_all.setFixedSize(70, 20)
        self.btn_show_all.setStyleSheet(
            "QPushButton { font-size: 11px; background: #0078D7; color: white; border-radius: 3px; padding: 0; }"
            "QPushButton:hover { background: #005a9e; }")
        self.btn_show_all.clicked.connect(self._restore_all_detections)
        detect_title_row.addWidget(self.btn_show_all)
        img_compare_layout.addLayout(detect_title_row)

        self.img_detect_label = QLabel()
        self.img_detect_label.setAlignment(Qt.AlignCenter)
        self.img_detect_label.setStyleSheet("background-color: #1a1a1a; border-radius: 4px;")
        img_compare_layout.addWidget(self.img_detect_label, 1)

        self.img_compare_widget.hide()
        left_panel.addWidget(self.img_compare_widget)

        main_layout.addLayout(left_panel, 7)

        # 图片检测结果缓存（用于点击筛选）
        self._img_original_frame = None    # 原图 numpy
        self._img_annotated_frame = None   # 全框检测图 numpy
        self._img_detections = []           # [{id, box, name, conf, color}, ...]

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
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.cellClicked.connect(self._on_table_cell_clicked)
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
            self._img_original_frame = frame.copy()
            self._img_detections = []

            res_frame, records = self.processor.process_frame(frame, is_image=True)
            self._img_annotated_frame = res_frame.copy()

            # 收集每个检测结果的详情（用于点击筛选）
            if hasattr(self.processor, '_last_image_detections'):
                self._img_detections = self.processor._last_image_detections

            # 切换到图片对比模式
            self.video_label.hide()
            self.img_compare_widget.show()
            self._show_image_on_label(self._img_original_frame, self.img_original_label)
            self._show_image_on_label(res_frame, self.img_detect_label)
            self.lbl_detect_title.setText("▶ 检测结果（点击表格行筛选目标）")

            self.add_table_record(records)
            self.update_stats(self.processor.get_stats())
            self._show_summary(self.processor)
            self.log_output.append(f"单图检测完成: {path}（点击表格行可筛选某个目标）")

    def start_task(self, source):
        self.stop_all()
        self._reset_stats()
        # 切换回视频模式
        self.img_compare_widget.hide()
        self.video_label.show()
        self._img_original_frame = None
        self._img_annotated_frame = None
        self._img_detections = []
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

    def _on_table_cell_clicked(self, row, _col):
        """点击表格行：图片模式下筛选单个目标"""
        if self._img_original_frame is None or not self._img_detections:
            return
        id_item = self.table.item(row, 0)
        if id_item is None:
            return
        selected_id = id_item.text()

        frame = self._img_original_frame.copy()
        matched = [d for d in self._img_detections if str(d['id']) == selected_id]
        if not matched:
            return

        for d in matched:
            x1, y1, x2, y2 = [int(v) for v in d['box']]
            color = d['color']
            cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
            cv2.putText(frame, f"{d['name']} #{d['id']} {d['conf']:.2f}",
                        (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)

        self._show_image_on_label(frame, self.img_detect_label)
        self.lbl_detect_title.setText(f"▶ 筛选目标: #{selected_id}（点「显示全部」恢复）")
        self.log_output.append(f"🔍 已筛选目标 #{selected_id}")

    def _restore_all_detections(self):
        """恢复显示全部检测框"""
        if self._img_annotated_frame is not None:
            self._show_image_on_label(self._img_annotated_frame, self.img_detect_label)
            self.lbl_detect_title.setText("▶ 检测结果（点击表格行筛选目标）")
            self.table.clearSelection()

    def _show_image_on_label(self, frame, label):
        """将 numpy 图片显示到指定 QLabel"""
        h, w, c = frame.shape
        q_img = QImage(frame.data, w, h, w * c, QImage.Format_RGB888).rgbSwapped()
        label.setPixmap(QPixmap.fromImage(q_img).scaled(
            label.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation))

    def _reset_stats(self):
        self.count_car.setText("0")
        self.count_bicycle.setText("0")
        self.count_person.setText("0")
        self.count_total.setText("0")
        self.table.setRowCount(0)
        self._img_original_frame = None
        self._img_annotated_frame = None
        self._img_detections = []

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
