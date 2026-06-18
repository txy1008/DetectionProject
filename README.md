# 🚀 目标检测与追踪分析后端 (YOLO + DeepSORT)

这是一个基于 YOLO 和 DeepSORT 的智能视频/图像分析后端处理模块 (`processor.py`)。该模块实现了目标的实时检测、多目标追踪、轨迹记录、速度估算、自动截图留存、数据库持久化以及自动生成丰富图表的 Word 数据报告。

## ✨ 核心特性

- **🧠 智能检测与追踪**：整合 `Ultralytics YOLO` 进行高精度目标检测，利用 `DeepSORT` 进行视频流的稳定多目标追踪（抗遮挡、去重）。
- **🔄 动态配置**：支持在运行时无缝切换 YOLO 模型 (`change_model`)，并支持动态调整置信度阈值。
- **👥 多用户会话管理**：通过 `start_session` 隔离不同用户的数据，自动建立规范的本地文件存储目录（支持按天、按次划分）。
- **💾 数据持久化落地**：
  - **图片留存**：自动对检测到的目标进行精准抠图（Crop）并按类别分类保存。
  - **数据库录入**：无缝对接 MySQL，记录每次检测的详细元数据（时间、ID、类别、置信度、路径）。
  - **CSV 备份**：实时同步生成 CSV 格式的检测流水账。
- **📊 自动化数据报告**：一键生成结构化的 `.docx` (Word) 检测报告，内置数据摘要、明细表格以及由 `Matplotlib` 自动生成的分析图表（饼图、柱状图）。
- **⚡ 针对性优化**：
  - **双模式处理**：区分单图模式（仅检测）与视频模式（检测+追踪+测速）。
  - **防崩溃机制**：内置 DeepSORT 特征维度冲突异常捕获及自动重启机制。
  - **并发写保护**：为截取文件名加入序号 (`seq_num`)，防止同秒内目标文件互相覆盖。

---

## 🛠️ 技术栈与依赖

- **深度学习**：`torch`, `ultralytics` (YOLO)
- **目标追踪**：`deep_sort_realtime`
- **图像处理**：`OpenCV` (cv2)
- **数据处理**：`pandas`, `numpy`
- **数据库**：`mysql-connector-python`
- **文档与图表**：`python-docx`, `matplotlib`

*(需配合外部 `config.py` 提供数据库配置、路径常量及 DeepSORT 超参数)*

---

## 📂 文件存储架构

系统运行时，会自动根据用户和当前日期构建规范的存储目录：

```text
根目录/
├── results/                     # 分析结果与报告目录
│   └── {username}/              # 按用户隔离
│       ├── 报告_20231027_第1次.csv    # 实时检测数据流
│       └── 报告_20231027_第1次.docx   # 导出的 Word 统计报告
└── captures/                    # 目标抓拍图存储目录
    └── {username}/              
        └── 报告_20231027_第1次/
            ├── car/             # 抓拍的机动车图片
            ├── bicycle/         # 抓拍的非机动车图片
            └── person/          # 抓拍的行人图片
```

---

## 🗄️ 数据库表结构要求

模块默认向 `detections` 表中写入数据。在使用前，请确保您的 MySQL 数据库包含以下表结构：

```sql
CREATE TABLE detections (
    id INT AUTO_INCREMENT PRIMARY KEY,
    session_id VARCHAR(255),      -- 场次名称 (如：报告_20231027_第1次)
    obj_id INT,                   -- 追踪/检测分配的 ID
    category VARCHAR(50),         -- 类别 (car, bicycle, person)
    img_name VARCHAR(255),        -- 截图文件名
    img_path TEXT,                -- 截图本地绝对路径
    confidence FLOAT,             -- 检测置信度
    detect_time DATETIME          -- 检测到的时间
);
```

---

## 💻 核心 API 使用指南

### 1. 初始化处理器
```python
from processor import DetectionProcessor

# 初始化，自动加载 config.py 中的模型和配置
processor = DetectionProcessor()
```

### 2. 启动新会话
每次处理新的视频或图像批次前，建议开启新会话以隔离数据。
```python
session_name = processor.start_session(username="admin_user")
print(f"当前场次: {session_name}")
```

### 3. 处理帧流 (单图 / 视频流)
在主循环中传入 OpenCV 格式的图像帧 (`numpy.ndarray`)。

**处理单张图片 (不启用追踪)：**
```python
annotated_frame, new_records = processor.process_frame(frame, is_image=True)
```

**处理连续视频流 (启用 DeepSORT 追踪与测速)：**
```python
annotated_frame, new_records = processor.process_frame(frame, is_image=False)
```
*返回值 `annotated_frame` 为绘制了检测框和标签的图像，`new_records` 为当前帧新增的需保存的记录字典列表。*

### 4. 获取实时统计
```python
stats = processor.get_stats()
# 返回示例: {"car": 15, "bicycle": 5, "person": 22}
```

### 5. 生成并导出报告
会话结束后，一键生成包含图表的 Word 报告。
```python
report_path = processor.generate_word_report()
print(f"报告已生成至: {report_path}")
```

### 6. 动态切换模型
```python
success = processor.change_model("path/to/new/yolov8_custom.pt")
```

---

## ⚙️ 核心处理逻辑流程 (视频模式)

1. **YOLO 预检测**：获取原始画面中的边界框 (`boxes`)、类别 (`cls`) 和置信度 (`conf`)。
2. **格式转换**：将 YOLO 的 `[x1, y1, x2, y2]` 转换为 DeepSORT 要求的 `([x, y, w, h], conf, cls)` 格式。
3. **DeepSORT 追踪更新**：提取画面外观特征并更新卡尔曼滤波，维持跨帧目标的 ID 一致性。
4. **异常轨过滤**：剔除未确认 (Unconfirmed) 和幽灵 (time_since_update > 0) 轨迹。
5. **轨迹记录与测速**：记录目标中心点变化，若存在超过 5 帧的历史，则进行像素级速度估算。
6. **逻辑防抖过滤**：目标必须连续出现在 `config.STABLE_FRAMES` 帧中才会被视为有效目标并录入系统。
7. **数据固化**：对有效目标进行截图、保存至硬盘，并写入 MySQL 数据库及内存 Pandas Dataframe 中。

---

## ⚠️ 注意事项

1. **GUI 线程安全**：本模块中的 `matplotlib` 强制使用了 `Agg` 后端 (`matplotlib.use("Agg")`)，这非常适合在无头服务器或后台线程中生成图表，不会阻塞主 UI 线程。
2. **配置文件依赖**：使用前必须保证项目根目录下存在 `config.py`，且包含 `MODEL_PATH`、`YOLO_DEVICE`、`DB_CONFIG`、`RESULTS_DIR`、`CAPTURES_DIR` 以及 DeepSORT 的相关超参数。
