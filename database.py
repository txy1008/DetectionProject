from sqlalchemy import create_engine, Column, Integer, String
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from config import DB_HOST, DB_PORT, DB_USER, DB_PASSWORD, DB_NAME

# MySQL 连接 URL，pymysql 驱动，utf8mb4 支持中文
DATABASE_URL = (
    f"mysql+pymysql://{DB_USER}:{DB_PASSWORD}"
    f"@{DB_HOST}:{DB_PORT}/{DB_NAME}"
    f"?charset=utf8mb4"
)

# pool_pre_ping=True：每次使用连接前检测是否存活，防止断连报错
engine = create_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


class DetectionRecord(Base):
    """
    检测记录表：每行对应一次检测会话中的一个目标
    """
    __tablename__ = "detection_records"

    id              = Column(Integer, primary_key=True, autoincrement=True)
    session_name    = Column(String(64),  nullable=False, index=True)  # 报告_20260526_第1次
    obj_id          = Column(Integer,     nullable=False)              # 目标 ID（图片顺序/追踪ID）
    class_name      = Column(String(64),  nullable=False)              # 类别（person, car...）
    detect_time     = Column(String(16),  nullable=False)              # 发现时间 HH:MM:SS
    screenshot_path = Column(String(512))                              # 截图本地绝对路径
    source_type     = Column(String(16),  nullable=False)              # 来源：image / video / camera


# ── 初始化 ─────────────────────────────────────────────────────────────────────

def init_db():
    """启动时调用，自动建表（表已存在则跳过）"""
    Base.metadata.create_all(bind=engine)


# ── 写入 ───────────────────────────────────────────────────────────────────────

def db_save_records(records: list, session_name: str, source_type: str):
    """
    批量写入检测记录。
    records 格式：[{"ID": 1, "类别": "person", "时间": "13:00:44", "存储路径": "..."}]
    """
    db = SessionLocal()
    try:
        for r in records:
            db.add(DetectionRecord(
                session_name    = session_name,
                obj_id          = r["ID"],
                class_name      = r["类别"],
                detect_time     = r["时间"],
                screenshot_path = r["存储路径"],
                source_type     = source_type,
            ))
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


# ── 查询 ───────────────────────────────────────────────────────────────────────

def db_get_sessions() -> list:
    """查询所有历史会话名（去重、倒序）"""
    db = SessionLocal()
    try:
        rows = (
            db.query(DetectionRecord.session_name)
            .distinct()
            .order_by(DetectionRecord.session_name.desc())
            .all()
        )
        return [r[0] for r in rows]
    finally:
        db.close()


def db_get_records(session_name: str = None, class_name: str = None) -> list:
    """
    查询检测记录，支持按会话名、类别过滤。
    不传参数则返回全部记录（最新在前）。
    """
    db = SessionLocal()
    try:
        query = db.query(DetectionRecord)
        if session_name:
            query = query.filter(DetectionRecord.session_name == session_name)
        if class_name:
            query = query.filter(DetectionRecord.class_name == class_name)
        rows = query.order_by(DetectionRecord.id.desc()).all()
        return [
            {
                "id":              r.id,
                "session_name":    r.session_name,
                "obj_id":          r.obj_id,
                "class_name":      r.class_name,
                "detect_time":     r.detect_time,
                "screenshot_path": r.screenshot_path,
                "source_type":     r.source_type,
            }
            for r in rows
        ]
    finally:
        db.close()
