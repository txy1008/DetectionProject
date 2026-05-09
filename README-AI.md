# 智能行人与车辆检测计数系统 (V5.1 · DeepSORT)

## 📌 项目概述

这是一个基于 **YOLOv8 + DeepSORT + PySide6** 开发的智慧交通监控系统。系统专门用于路口或小区门口的流量监控，支持实时检测、DeepSORT 多目标追踪（含 ReID 外观特征）、越线计数、热力图分析、区域入侵告警、历史数据图表分析及 PDF 报告导出。

## 🤖 AI 快速理解手册 (System Architecture)

如果你是 AI 助手，请关注以下逻辑：

1. **核心逻辑**：采用 `YOLOv8n` 做检测 + `DeepSORT` (MobileNet ReID) 做追踪，两阶段分离。
2. **模块化架构**：
   - `main.py` → 程序入口
   - `config.py` → 所有可调参数集中管理（模型路径、DB、阈值、DeepSORT 参数、UI 配置）
   - `processor.py` → 后端核心（YOLO 检测 + DeepSORT 追踪 + 越线计数 + 热力图 + 速度估计 + 告警 + 数据持久化）
   - `ui/main_window.py` → 主窗口 UI + 业务逻辑
   - `ui/video_thread.py` → QThread 视频处理子线程
   - `ui/history_dialog.py` → 历史分析弹窗（Matplotlib 图表 + PDF 导出）
   - `ui/alert_manager.py` → 区域入侵告警管理器
3. **多线程设计**：`VideoThread` 负责推理，通过信号槽（Signal/Slot）将结果传给 UI 主线程，防止界面卡死。
4. **数据持久化**：
   - **数据库**：MySQL (存入 ID, 类别, 置信度, 图片路径)，断连自动降级。
   - **文件系统**：`captures/` 存截图，`results/` 存生成的 CSV 报告。
5. **类别映射**：
   - `person` → `person`
   - `bus/truck/car` → `car` (机动车)
   - `motorcycle/bicycle` → `bicycle` (非机动车)

## 📁 项目目录结构

- `main.py`: **[入口]** 启动 PySide6 应用。
- `config.py`: **[配置]** 模型路径、DB 连接、DeepSORT 参数、检测阈值、UI 设置。
- `processor.py`: **[后端]** YOLO 检测 + DeepSORT 追踪 + 越线计数 + 热力图 + 速度估计 + 数据库写入 + 截图保存。
- `ui/main_window.py`: **[前端]** 主窗口布局、统计看板、按钮事件、告警区域设置。
- `ui/video_thread.py`: **[线程]** QThread 视频处理，信号驱动 UI 刷新。
- `ui/history_dialog.py`: **[分析]** 历史 CSV 数据加载、饼图/柱状图、PDF 导出。
- `ui/alert_manager.py`: **[告警]** 区域管理、入侵检测、声音告警、冷却机制。
- `models/`: 存放模型权重文件 (`yolov8n.pt` 或自训练 `best.pt`)。
- `captures/`: 自动按场次生成的检测截图文件夹。
- `results/`: 自动按场次生成的检测数据报表 (CSV)。

## 🛠️ 技术栈

- **语言**: Python 3.9+
- **检测**: Ultralytics YOLOv8
- **追踪**: DeepSORT (deep-sort-realtime, MobileNet ReID)
- **框架**: PyTorch
- **视觉**: OpenCV
- **UI**: PySide6 (Qt for Python)
- **图表**: Matplotlib
- **存储**: MySQL 8.0, Pandas (CSV Export)

## 🚀 关键逻辑点 (Highlights)

- **两阶段架构**: YOLO 只做检测，DeepSORT 独立做追踪（含外观特征提取），解耦清晰。
- **防抖动机制**: 目标连续出现 5 帧才触发数据库写入和截图，有效降低误报率。
- **热力图衰减**: 每帧乘以 0.95 衰减系数，适应场景切换，旧数据自然消退。
- **幽灵轨迹过滤**: 只绘制当前帧实际匹配到的轨迹 (`time_since_update == 0`)。
- **命名规范**: 采用「报告_日期_第N次」自动递增命名，防止数据覆盖。
- **ID 唯一性**: 文件名引入 `save_count` 序号，解决单帧多目标的文件覆盖冲突。

## 📝 数据库表设计 (ER 简述)

表名: `detections`
- `session_id`: 任务场次名 (报告_日期_第N次)
- `obj_id`: DeepSORT 追踪 ID (视频模式) 或 0 (单图模式)
- `category`: 映射后的类别名 (car/bicycle/person)
- `img_path`: 本地图片的绝对路径
- `detect_time`: 精确到秒的检测时间

## ⚙️ DeepSORT 配置参数 (config.py)

- `DEEPSORT_MAX_AGE = 30`: 目标消失后保留轨迹的最大帧数
- `DEEPSORT_N_INIT = 3`: 连续检测到 N 次后确认轨迹
- `DEEPSORT_NN_BUDGET = 100`: 外观特征库最大容量
- `DEEPSORT_EMBEDDER = "mobilenet"`: ReID 模型选择
- `DEEPSORT_EMBEDDER_GPU = True`: ReID 是否使用 GPU 加速
