import os

# 项目根目录（config.py 所在目录）
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# ── 目录路径 ──────────────────────────────────────────────────────────────────
CAPTURES_DIR = os.path.join(BASE_DIR, "captures")   # 截图存放根目录
RESULTS_DIR  = os.path.join(BASE_DIR, "results")    # CSV 和标注结果存放目录
UPLOADS_DIR  = os.path.join(BASE_DIR, "uploads")    # 临时上传目录
MODELS_DIR   = os.path.join(BASE_DIR, "models")     # 模型存放目录
VIDEOS_DIR   = os.path.join(RESULTS_DIR, "videos")  # 导出视频存放目录

# ── 模型路径（优先 models/ 目录，找不到则用根目录）────────────────────────────
_candidates = [
    os.path.join(MODELS_DIR, "yolov8n.pt"),
    os.path.join(BASE_DIR,   "yolov8n.pt"),
]
MODEL_PATH = next((p for p in _candidates if os.path.exists(p)), _candidates[-1])

# ── 服务地址 ──────────────────────────────────────────────────────────────────
BASE_URL = "http://127.0.0.1:8000"

# ── MySQL 数据库连接配置（按实际情况修改）────────────────────────────────────
DB_HOST     = "localhost"       # 数据库服务器地址
DB_PORT     = 3306              # 端口，默认 3306
DB_USER     = "root"            # 用户名
DB_PASSWORD = "Txy20041008"     # 密码
DB_NAME     = "detection_db"    # 数据库名（需要提前在 MySQL 中建好）

# ── 检测默认参数 ──────────────────────────────────────────────────────────────
DEFAULT_CONF = 0.3           # 默认置信度阈值
TRACKER      = "botsort.yaml"  # 追踪算法配置文件

# ── 自动创建所有必要目录 ──────────────────────────────────────────────────────
for _d in [CAPTURES_DIR, RESULTS_DIR, UPLOADS_DIR, MODELS_DIR, VIDEOS_DIR]:
    os.makedirs(_d, exist_ok=True)
