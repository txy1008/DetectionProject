# 智能行人与车辆检测计数系统 (V5.1 专业版 · DeepSORT)

## 1. 项目简介

本项目是一款基于深度学习技术的**智慧交通监控系统**。系统能够实时检测视频流、摄像头或单张图片中的行人及车辆，通过 **DeepSORT** 多目标追踪算法（含 ReID 外观特征匹配）为每个目标分配唯一 ID，并实现分类计数、越线统计、热力图分析、区域入侵告警、速度估计等高级功能。系统集成了 MySQL 数据库进行持久化存储，支持 CSV 报表导出、历史数据图表分析及 PDF 报告生成。

### 核心功能

- **多源输入**：支持本地视频文件、USB 摄像头实时流、单张图片检测。
- **精准分类**：将 YOLO 默认类别重映射为：机动车 (car)、非机动车 (bicycle)、行人 (person) 三大类。
- **DeepSORT 智能追踪**：采用 DeepSORT 算法（MobileNet ReID），利用外观特征进行跨帧关联，结合连续帧确认机制有效减少 ID 跳变和误检。
- **越线计数**：自动统计目标穿越检测线的上行/下行数量。
- **热力图叠加**：一键切换热力图模式，可视化目标出现频率分布，支持自动衰减适应场景切换。
- **区域入侵告警**：用户自定义告警区域，目标进入时触发蜂鸣声告警。
- **速度估计**：基于追踪轨迹估算目标运动速度。
- **数据管理**：
  - **数据库**：实时将检测记录写入 MySQL，支持断连自动降级为 CSV。
  - **文件系统**：按「报告_日期_第N次」自动创建场次文件夹，截图按类别细分存储。
  - **报表导出**：同步生成 CSV 格式检测报告。
- **历史分析**：加载历史 CSV 数据，生成饼图与柱状图，支持一键导出 PDF 报告。
- **实时统计看板**：6 项指标实时更新（三类计数 + 上行/下行 + 总计）。

## 2. 技术栈

| 模块 | 技术 |
|------|------|
| 检测模型 | Ultralytics YOLOv8 (yolov8n.pt)，支持自训练模型切换 |
| 追踪算法 | DeepSORT（deep-sort-realtime），MobileNet ReID 外观特征 |
| 深度学习框架 | PyTorch |
| 图像处理 | OpenCV-Python |
| 界面开发 | PySide6 (Qt for Python)，多线程架构 |
| 数据可视化 | Matplotlib（图表 + PDF 导出） |
| 数据处理 | Pandas |
| 数据库 | MySQL 8.0 |

## 3. 项目结构

```
VisionProject/
├── main.py              # 程序入口
├── config.py            # 集中配置文件（模型/数据库/阈值/DeepSORT/UI）
├── processor.py         # 后端 AI 核心：YOLO检测 + DeepSORT追踪 + 数据持久化
├── ui/                  # 界面模块
│   ├── __init__.py      # 包初始化与导出
│   ├── main_window.py   # 主窗口布局与业务逻辑
│   ├── video_thread.py  # 视频处理子线程（QThread）
│   ├── history_dialog.py# 历史数据分析弹窗 + PDF 导出
│   └── alert_manager.py # 区域入侵告警管理器
├── models/              # 存放 YOLO 模型权重 (yolov8n.pt / best.pt)
├── captures/            # 自动生成的场次截图文件夹（按类别分目录）
├── results/             # 自动生成的 CSV 检测报告
├── requirements.txt     # Python 依赖管理
└── test_run.py          # 环境快速测试脚本
```

## 4. 安装与配置

### 4.1 环境安装

推荐使用清华大学镜像源安装依赖：

```bash
pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
```

### 4.2 数据库配置

在 MySQL Workbench 中运行以下脚本创建数据库：

```sql
CREATE DATABASE IF NOT EXISTS traffic_system_db;
USE traffic_system_db;
CREATE TABLE IF NOT EXISTS detections (
    id INT AUTO_INCREMENT PRIMARY KEY,
    session_id VARCHAR(100),
    obj_id INT,
    category VARCHAR(50),
    img_name VARCHAR(255),
    img_path VARCHAR(500),
    confidence FLOAT,
    detect_time DATETIME
);
```

修改 `config.py` 中的 `DB_CONFIG`，填入你的 MySQL 密码。

### 4.3 自训练模型切换

将训练好的 `best.pt` 放入 `models/` 目录，然后修改 `config.py`：

```python
MODEL_PATH = "models/best.pt"
```

如果自训练模型的类别 ID 与 COCO 不同，同步修改 `CLASS_MAPPING`。

## 5. 算法逻辑说明

### 5.1 类别映射 (Classification Mapping)

为符合交通统计标准，系统对检测目标进行了逻辑归并：

- `bus, truck, car` → **car** (机动车)
- `motorcycle, bicycle` → **bicycle** (非机动车/电动车)
- `person` → **person** (行人)

### 5.2 DeepSORT 追踪算法

系统采用 **YOLO 检测 + DeepSORT 追踪** 的两阶段架构：

1. **第一阶段**：YOLOv8 对每帧进行目标检测，输出检测框和类别。
2. **第二阶段**：DeepSORT 利用 MobileNet 提取每个目标的**外观特征（ReID）**，结合卡尔曼滤波预测的运动状态，通过匈牙利算法进行跨帧数据关联。

相比 ByteTrack 仅依赖 IoU 匹配，DeepSORT 的外观特征使其在**遮挡后重新识别**同一目标时表现更优。

### 5.3 稳定性机制 (Stability Buffer)

- **缓冲机制**：新 ID 必须连续出现 5 帧以上才被判定为有效目标，有效降低误报。
- **防覆盖命名**：截图文件名采用 `类别_ID_序号_时间` 格式，确保不会发生文件覆盖。

### 5.4 热力图衰减机制

热力图数据每帧乘以 0.95 的衰减系数，使旧场景数据在约 1~2 秒内自然消退，适应视频场景切换。

## 6. 使用说明

1. 运行 `python main.py` 启动系统。
2. 点击 **[开启摄像头]** 或 **[上传视频]** 进行实时动态检测。
3. 点击 **[检测单张图片]** 进行静态高精度分析。
4. 点击 **[热力图模式]** 切换热力图叠加显示。
5. 点击 **[设置告警区域]** 输入坐标比例定义禁区。
6. 点击 **[历史数据分析]** 查看图表并导出 PDF 报告。
7. 检测结果实时刷新在右侧统计看板和明细表格中。
8. 停止运行后，可在 `captures/` 和 `results/` 查看本次任务的详细导出内容。

## 7. 设计亮点

- **模块化架构**：前后端分离，配置集中管理，代码拆分为 8 个职责单一的模块。
- **多线程处理**：通过 QThread + Signal/Slot 机制，AI 推理不阻塞 UI，保证界面流畅响应。
- **DeepSORT 外观特征追踪**：基于 ReID 特征的深度关联，相比纯 IoU 匹配追踪更稳定。
- **容错性**：数据库连接异常时自动降级为 CSV 存储，确保数据不丢失。
- **多维度分析**：越线计数、热力图、速度估计、区域告警，覆盖智慧交通核心分析需求。
