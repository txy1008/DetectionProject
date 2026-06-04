"""
main.py — 应用启动入口
只负责：创建 app、注册路由、挂载静态文件、初始化数据库
所有接口定义见 router.py
POST  /api/detect/image   → 图片检测
POST  /api/detect/video   → 视频检测
WS    /ws/camera          → 摄像头实时
GET   /api/sessions       → 历史会话列表
GET   /api/records        → 检测记录查询（可按会话/类别过滤）
GET   /api/report/export  → 导出 Word 检测报告
GET   /api/video/export   → 导出检测视频
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from config import CAPTURES_DIR, RESULTS_DIR
from database import init_db
from router import router

app = FastAPI(title="目标检测系统 API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 静态文件：前端可通过 URL 直接访问截图和结果文件
app.mount("/captures", StaticFiles(directory=CAPTURES_DIR), name="captures")
app.mount("/results",  StaticFiles(directory=RESULTS_DIR),  name="results")

# 注册所有 API 路由
app.include_router(router)

# 启动时初始化数据库（建表）
init_db()


@app.get("/")
async def root():
    return {"message": "YOLOv8 目标检测系统后端已启动！"}