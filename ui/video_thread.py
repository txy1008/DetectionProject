import time
import cv2
import numpy as np
from PySide6.QtCore import QThread, Signal
from processor import DetectionProcessor


class VideoThread(QThread):
    """视频处理子线程 - 负责推理，通过信号将结果传给 UI"""
    change_pixmap_signal = Signal(np.ndarray)
    new_record_signal = Signal(list)
    stats_signal = Signal(dict)
    finished_signal = Signal()

    def __init__(self, source=0):
        super().__init__()
        self.source = source
        self.running = True
        self.paused = False
        self.processor = DetectionProcessor()

    def run(self):
        self.processor.start_session()
        cap = cv2.VideoCapture(self.source)
        while self.running:
            if self.paused:
                time.sleep(0.05)
                continue
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

    def pause(self):
        self.paused = True

    def resume(self):
        self.paused = False

    def stop(self):
        self.running = False
        self.paused = False
        self.wait()

    def update_model(self, model_path):
        """接收UI指令，更新处理器中的模型"""
        if hasattr(self, 'processor'):
            self.processor.change_model(model_path)