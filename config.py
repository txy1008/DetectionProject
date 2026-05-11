"""
全局配置文件 - 所有可调参数集中管理
"""

# ==================== 模型配置 ====================
# 切换模型：将路径改为你自己训练的 best.pt 即可
MODEL_PATH = "models/yolov8n.pt"
# MODEL_PATH = "models/best.pt"  # 自训练模型（训练好后取消注释）

# 检测置信度阈值
CONF_VIDEO = 0.6       # 视频模式置信度
CONF_IMAGE = 0.4       # 单图模式置信度
IOU_THRESHOLD = 0.5    # NMS IOU 阈值

# 目标稳定帧数（连续出现 N 帧才确认为有效目标）
STABLE_FRAMES = 5

# ==================== DeepSORT 追踪配置 ====================
DEEPSORT_MAX_AGE = 30         # 目标消失后保留轨迹的最大帧数
DEEPSORT_N_INIT = 3           # 连续检测到 N 次后确认轨迹
DEEPSORT_NN_BUDGET = 100      # 外观特征库最大容量
DEEPSORT_EMBEDDER = "mobilenet"  # ReID 模型: mobilenet / torchreid / clip_RN50
DEEPSORT_EMBEDDER_GPU = True  # ReID 是否用 GPU

# ==================== 类别映射 ====================
# COCO 数据集 ID → 自定义类别
# 如果你自训练的模型类别 ID 不同，在这里修改
CLASS_MAPPING = {
    0: "person",      # COCO: person
    1: "bicycle",     # COCO: bicycle
    2: "car",         # COCO: car
    3: "bicycle",     # COCO: motorcycle → 归为非机动车
    5: "car",         # COCO: bus → 归为机动车
    7: "car",         # COCO: truck → 归为机动车
}

# 需要检测的 COCO 类别 ID 列表（自动从映射表生成）
TARGET_CLASSES = list(CLASS_MAPPING.keys())

# ==================== 数据库配置 ====================
DB_CONFIG = {
    'host': 'localhost',
    'user': 'root',
    'password': 'Txy20041008',  # 修改为你的 MySQL 密码
    'database': 'traffic_system_db'
}

# ==================== 路径配置 ====================
CAPTURES_DIR = "captures"
RESULTS_DIR = "results"

# ==================== UI 配置 ====================
WINDOW_TITLE = "智慧路口视频监控系统专业版 v5.1 (DeepSORT)"
WINDOW_WIDTH = 1600
WINDOW_HEIGHT = 950
