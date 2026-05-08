智能行人与车辆检测计数系统 (V4.0 专业版)
1. 项目简介
本项目是一款基于深度学习技术的智慧交通监控原型系统。系统能够实时检测视频流、摄像头或单张图片中的行人及车辆，通过多目标追踪算法（ByteTrack）为每个目标分配唯一 ID，并实现分类计数。系统集成了 MySQL 数据库进行持久化存储，并支持自动化的 CSV 报表导出及分场次截图管理。
核心功能
多源输入：支持本地视频文件、USB 摄像头实时流、单张图片检测。
精准分类：针对课程需求，将 YOLO 默认类别重映射为：机动车 (car)、非机动车 (bicycle)、行人 (person) 三大类。
智能追踪：采用 ByteTrack 算法，结合“连续帧确认机制”，有效减少 ID 跳变和误检。
数据管理：
数据库：实时将检测 ID、时间、置信度、图片绝对路径写入 MySQL。
文件系统：按“报告_日期_第N次”自动创建场次文件夹，截图按类别细分存储。
报表导出：同步生成 CSV 格式的检测报告。
专业 UI：基于 PySide6 开发的多线程交互界面，包含实时画面显示、统计看板、历史记录表格及系统日志。
2. 技术栈
检测框架：Ultralytics YOLOv8 (yolov8n.pt)
图像处理：OpenCV-Python
界面开发：PySide6 (Qt for Python)
数据处理：Pandas, MySQL-Connector-Python
数据库：MySQL 8.0
运行环境：纯 CPU 优化推理
3. 项目结构
code
Text
VisionProject/
├── captures/           # 自动生成的场次截图文件夹 (按类别分目录)
├── results/            # 自动生成的 CSV 检测报告
├── models/             # 存放 YOLO 模型权重 (yolov8n.pt / best.pt)
├── main_ui.py          # 界面逻辑与多线程管理
├── processor.py        # 后端 AI 检测核心逻辑与数据库交互
├── test_run.py         # 环境快速测试脚本
└── traffic_system.db   # (可选) SQLite 备份记录
4. 安装与配置
4.1 环境安装
推荐使用清华大学镜像源安装依赖：
code
Bash
pip install ultralytics opencv-python PySide6 pandas mysql-connector-python -i https://pypi.tuna.tsinghua.edu.cn/simple
4.2 数据库配置
在 MySQL Workbench 中运行以下脚本创建数据库：
code
SQL
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
修改 processor.py 中的 self.db_config，填入你的 MySQL password。
5. 算法逻辑说明
5.1 类别映射 (Classification Mapping)
为符合交通统计标准，系统对检测目标进行了逻辑归并：
bus, truck, car 
→
→
 car (机动车)
motorcycle, bicycle 
→
→
 bicycle (非机动车/电动车)
person 
→
→
 person (行人)
5.2 稳定性机制 (Stability Buffer)
为解决 CPU 环境下 FPS 波动导致的 ID 跳变：
缓冲机制：新 ID 必须在画面中连续出现 5 帧以上才会被判定为“有效目标”。
防覆盖命名：截图文件名采用 类别_ID_序号_时间 格式，确保在单张图片多个目标检测时不会发生文件覆盖。
6. 使用说明
运行 main_ui.py 启动系统。
点击 [开启摄像头] 或 [上传视频] 进行实时动态检测。
点击 [检测单张图片] 进行静态高精度分析。
检测结果将实时刷新在右侧表格中。
停止运行后，可在 captures 和 results 查看本次任务的详细导出内容。
7. 实践课心得与亮点
工程化设计：采用前端界面与后端算法分离的架构，增强了代码的可维护性。
多线程处理：通过 QThread 解决 AI 推理过程中的 UI 阻塞问题，保证了界面的流畅响应。
容错性：加入了数据库连接异常捕捉机制，确保在无数据库环境下系统依然能通过本地 CSV 正常运行。