# 🎯 YOLOv8 目标检测系统

基于 **FastAPI + YOLOv8 + MySQL** 的目标检测后端服务，支持图片检测、视频多目标跟踪和摄像头实时检测，自动裁剪保存目标截图并生成 CSV 报告。

---

## 📁 项目结构

```
DetectionProject/
├── main.py           # 应用入口：创建 FastAPI 实例、挂载静态文件、初始化数据库
├── config.py         # 全局配置：路径、数据库连接、检测参数
├── router.py         # 所有 API 接口定义
├── processor.py      # YOLO 模型加载 & 检测/跟踪核心逻辑
├── database.py       # SQLAlchemy 数据库模型与增删改查
├── report.py         # Word 检测报告生成（导出 .docx）
├── yolov8n.pt        # YOLOv8 预训练权重（也可放在 models/ 目录下）
├── captures/         # 检测截图输出目录（按会话/类别分文件夹）
├── results/          # CSV 报告 & Word 报告输出目录
├── uploads/          # 临时上传文件目录
└── models/           # 模型存放目录（可选）
```

## 🛠️ 环境依赖

- **Python** >= 3.9
- **MySQL** >= 5.7（需提前创建数据库）

### Python 依赖包

| 包名 | 用途 |
|---|---|
| `fastapi` | Web 框架 |
| `uvicorn` | ASGI 服务器 |
| `ultralytics` | YOLOv8 推理 & 跟踪 |
| `opencv-python` | 图像/视频处理 |
| `numpy` | 数组运算 |
| `sqlalchemy` | ORM 数据库操作 |
| `pymysql` | MySQL 驱动 |
| `python-multipart` | FastAPI 文件上传支持 |
| `python-docx` | Word 文档生成 |
| `matplotlib` | 图表绘制（报告中的饼图/柱状图） |

安装全部依赖：

```bash
pip install fastapi uvicorn ultralytics opencv-python numpy sqlalchemy pymysql python-multipart python-docx matplotlib
```

## ⚙️ 配置说明

编辑 `config.py` 中的数据库连接信息：

```python
DB_HOST     = "localhost"
DB_PORT     = 3306
DB_USER     = "root"
DB_PASSWORD = "your_password"
DB_NAME     = "detection_db"
```

> **注意**：请先在 MySQL 中手动创建数据库：
> ```sql
> CREATE DATABASE detection_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
> ```

其他可调参数：

| 参数 | 默认值 | 说明 |
|---|---|---|
| `DEFAULT_CONF` | `0.3` | 默认检测置信度阈值 |
| `TRACKER` | `botsort.yaml` | 多目标跟踪算法配置 |
| `BASE_URL` | `http://127.0.0.1:8000` | 服务基地址（用于拼接资源 URL） |

## 🚀 启动服务

```bash
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

启动后访问：
- **API 文档**：http://127.0.0.1:8000/docs
- **根路径**：http://127.0.0.1:8000/ → `{"message": "YOLOv8 目标检测系统后端已启动！"}`

## 📡 API 接口

### 1. 图片检测

```
POST /api/detect/image
Content-Type: multipart/form-data
```

| 参数 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `file` | File | ✅ | 图片文件 |
| `conf` | float | ❌ | 置信度阈值，默认 0.3 |

**返回示例**：

```json
{
  "code": 200,
  "msg": "检测成功",
  "data": {
    "session_name": "报告_20260528_第1次",
    "object_count": 3,
    "objects": [
      {"id": 1, "class_name": "person", "confidence": 0.912, "bbox": [100.0, 50.0, 300.0, 400.0]}
    ],
    "result_image_url": "http://127.0.0.1:8000/captures/报告_20260528_第1次/annotated_xxx.jpg",
    "csv_url": "http://127.0.0.1:8000/results/报告_20260528_第1次.csv"
  }
}
```

### 2. 视频检测

```
POST /api/detect/video
Content-Type: multipart/form-data
```

| 参数 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `file` | File | ✅ | 视频文件 |
| `conf` | float | ❌ | 置信度阈值，默认 0.3 |

**返回示例**：

```json
{
  "code": 200,
  "msg": "视频检测完成",
  "data": {
    "session_name": "报告_20260528_第1次",
    "object_count": 12,
    "result_video_url": "http://127.0.0.1:8000/captures/报告_20260528_第1次/tracked_xxx.mp4",
    "csv_url": "http://127.0.0.1:8000/results/报告_20260528_第1次.csv"
  }
}
```

### 3. 摄像头实时检测（WebSocket）

```
WS /ws/camera
```

**客户端发送**：

```json
{
  "frame": "<base64 编码的 JPEG 图片>",
  "conf": 0.3,
  "highlight_id": null
}
```

**服务端返回**：

```json
{
  "objects": [{"id": 1, "class_name": "person", "confidence": 0.85}],
  "annotated_frame": "<base64 编码的标注帧>",
  "total_unique": 5,
  "session_name": "报告_20260528_第1次",
  "csv_url": "http://127.0.0.1:8000/results/报告_20260528_第1次.csv"
}
```

### 4. 历史会话列表

```
GET /api/sessions
```

**返回示例**：

```json
{
  "code": 200,
  "data": [
    {"session_name": "报告_20260528_第1次", "csv_url": "http://..."}
  ]
}
```

### 5. 导出 Word 检测报告

```
GET /api/report/export?session_name=报告_20260528_第1次
```

| 参数 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `session_name` | string | ✅ | 要导出的会话名 |

**返回**：直接下载 `.docx` 文件（Content-Type: application/vnd.openxmlformats-officedocument.wordprocessingml.document）

**报告内容**：
- 报告信息（时间、模型、检测依据）
- 检测结果汇总（总数 + 人员/车辆/动物分类统计）
- 数据分析图表（饼图 + 柱状图）
- 检测明细记录表格（完整 CSV 数据）

### 6. 检测记录查询

```
GET /api/records?session_name=报告_20260528_第1次&class_name=person
```

| 参数 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `session_name` | string | ❌ | 按会话名过滤 |
| `class_name` | string | ❌ | 按类别过滤 |

**返回示例**：

```json
{
  "code": 200,
  "total": 3,
  "data": [
    {
      "id": 1,
      "session_name": "报告_20260528_第1次",
      "obj_id": 1,
      "class_name": "person",
      "detect_time": "13:00:44",
      "screenshot_path": "D:\\...\\person_ID1_No1_130044.jpg",
      "source_type": "image"
    }
  ]
}
```

## 📂 输出文件说明

每次检测自动生成一个会话，命名格式为 `报告_YYYYMMDD_第N次`。

```
captures/
└── 报告_20260528_第1次/
    ├── annotated_xxx.jpg          # 图片检测标注结果
    ├── tracked_xxx.mp4            # 视频跟踪结果
    ├── person/                    # 按类别分文件夹
    │   ├── person_ID1_No1_130044.jpg
    │   └── person_ID2_No2_130045.jpg
    └── car/
        └── car_ID3_No1_130046.jpg

results/
├── 报告_20260528_第1次.csv        # CSV 报告
├── 报告_20260528_第1次.docx       # Word 检测报告（导出时生成）
└── videos/                        # 导出视频目录
    └── 报告_20260528_第1次_tracked_xxx.mp4
```

**CSV 列说明**：

| 列名 | 说明 |
|---|---|
| `ID` | 目标 ID（图片为顺序编号，视频/摄像头为跟踪 ID） |
| `类别` | 检测到的目标类别 |
| `时间` | 检测时间（HH:MM:SS） |
| `存储路径` | 目标截图的本地绝对路径 |

## 🗄️ 数据库

使用 MySQL 存储检测记录，表结构如下（`detection_records`）：

| 字段 | 类型 | 说明 |
|---|---|---|
| `id` | INT (PK) | 自增主键 |
| `session_name` | VARCHAR(64) | 会话名称 |
| `obj_id` | INT | 目标 ID |
| `class_name` | VARCHAR(64) | 目标类别 |
| `detect_time` | VARCHAR(16) | 检测时间 |
| `screenshot_path` | VARCHAR(512) | 截图路径 |
| `source_type` | VARCHAR(16) | 来源类型：`image` / `video` / `camera` |

> 表在服务启动时自动创建（已存在则跳过）。

## 📝 License

MIT
