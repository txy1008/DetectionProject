# 智能行人与车辆检测计数系统 (V4.0)

## 📌 项目概述
这是一个基于 **YOLOv8** 和 **PySide6** 开发的工业级机器视觉实践项目。系统专门用于路口或小区门口的流量监控，支持实时检测、目标追踪、数据入库及报表导出。

## 🤖 AI 快速理解手册 (System Architecture)
如果你是 AI 助手，请关注以下逻辑：
1. **核心逻辑**：采用 `YOLOv8n` + `ByteTrack` 算法。
2. **多线程设计**：`VideoThread` 负责推理，通过信号槽（Signal/Slot）将结果传给 UI 主线程，防止界面卡死。
3. **数据持久化**：
   - **数据库**：MySQL (存入 ID, 类别, 置信度, 图片路径)。
   - **文件系统**：`captures/` 存截图，`results/` 存生成的 CSV 报告。
4. **类别映射**：
   - `person` -> `person`
   - `bus/truck/car` -> `car` (机动车)
   - `motorcycle/bicycle` -> `bicycle` (非机动车)

## 📁 项目目录结构
- `main_ui.py`: **[前端]** PySide6 界面、多线程调度、信号处理。
- `processor.py`: **[后端]** YOLO 模型推理、类别映射逻辑、MySQL 写入、图片自动保存。
- `models/`: 存放模型权重文件 (`yolov8n.pt`)。
- `captures/`: 自动按场次生成的检测截图文件夹。
- `results/`: 自动按场次生成的检测数据报表 (CSV)。

## 🛠️ 技术栈
- **语言**: Python 3.9+
- **视觉**: Ultralytics YOLOv8, OpenCV
- **UI**: PySide6 (Qt for Python)
- **存储**: MySQL 8.0, Pandas (CSV Export)

## 🚀 关键逻辑点 (Highlights)
- **防抖动机制**: 目标在画面中连续出现 5 帧才被触发数据库写入和截图，有效降低误报率。
- **命名规范**: 采用 `报告_日期_第N次` 自动递增命名，防止数据覆盖。
- **ID 唯一性**: 在文件名中引入 `save_count` 序号，解决单帧多目标检测时的文件覆盖冲突。

## 📝 数据库表设计 (ER 简述)
表名: `detections`
- `session_id`: 任务场次名 (报告_日期_第N次)
- `obj_id`: 追踪 ID (视频模式) 或 0 (单图模式)
- `category`: 映射后的类别名 (car/bicycle/person)
- `img_path`: 本地图片的绝对路径
- `detect_time`: 精确到秒的检测时间