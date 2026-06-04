"""
router.py — 所有 API 接口定义
前端开发只需阅读这一个文件，即可了解全部接口。

接口列表：
  POST   /api/detect/image    图片检测
  POST   /api/detect/video    视频检测
  WS     /ws/camera           摄像头实时检测
  GET    /api/sessions        历史会话列表
  GET    /api/records         检测记录查询（支持过滤）
  GET    /api/report/export   导出 Word 检测报告
  GET    /api/video/export    导出检测视频
"""

import os
import re
import time
import base64

import cv2
import numpy as np
from fastapi import APIRouter, File, Form, UploadFile, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse, FileResponse

from fastapi.concurrency import run_in_threadpool

from config import CAPTURES_DIR, RESULTS_DIR, UPLOADS_DIR, BASE_URL, VIDEOS_DIR
from processor import (
    process_image, process_video, process_camera_frame,
    get_session_name, save_csv,
)
from database import db_save_records, db_get_sessions, db_get_records
from report import generate_report

router = APIRouter()


# ── 图片检测 ───────────────────────────────────────────────────────────────────

@router.post("/api/detect/image")
async def detect_image(file: UploadFile = File(...), conf: float = Form(0.3)):
    """
    图片检测接口
    请求参数：
      - file : 图片文件（multipart/form-data）
      - conf : 置信度阈值，默认 0.3
    返回：
      - session_name     本次会话名
      - object_count     检测到的目标数量
      - objects          目标列表（id, class_name, confidence, bbox）
      - result_image_url 画框后的完整图片 URL
      - csv_url          CSV 下载链接
    """
    try:
        contents = await file.read()
        nparr    = np.frombuffer(contents, np.uint8)
        img      = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

        result = await run_in_threadpool(process_image, img, conf)

        safe_name = re.sub(r'[^\w.-]', '_', file.filename)
        annotated_filename = f"annotated_{int(time.time())}_{safe_name}"
        session_cap_dir = os.path.join(CAPTURES_DIR, result["session_name"])
        os.makedirs(session_cap_dir, exist_ok=True)
        ext = os.path.splitext(annotated_filename)[1] or ".jpg"
        _, buf = cv2.imencode(ext, result["annotated_img"])
        with open(os.path.join(session_cap_dir, annotated_filename), "wb") as f:
            f.write(buf.tobytes())

        db_save_records(result["records"], result["session_name"], source_type="image")

        return JSONResponse(content={
            "code": 200,
            "msg":  "检测成功",
            "data": {
                "session_name":     result["session_name"],
                "object_count":     result["object_count"],
                "objects":          result["objects"],
                "result_image_url": f"{BASE_URL}/captures/{result['session_name']}/{annotated_filename}",
                "csv_url":          f"{BASE_URL}/results/{result['session_name']}.csv",
            },
        })

    except Exception as e:
        return JSONResponse(status_code=500, content={"code": 500, "msg": str(e)})


# ── 视频检测 ───────────────────────────────────────────────────────────────────

@router.post("/api/detect/video")
async def detect_video(file: UploadFile = File(...), conf: float = Form(0.3)):
    """
    视频检测接口
    请求参数：
      - file : 视频文件（multipart/form-data）
      - conf : 置信度阈值，默认 0.3
    返回：
      - session_name      本次会话名
      - object_count      检测到的唯一目标数量
      - result_video_url  处理后视频 URL
      - csv_url           CSV 下载链接
    """
    try:
        safe_vid = re.sub(r'[^\w.-]', '_', file.filename)
        input_video_path = os.path.join(UPLOADS_DIR, f"vid_{int(time.time())}_{safe_vid}")

        with open(input_video_path, "wb") as buffer:
            buffer.write(await file.read())

        result = await run_in_threadpool(process_video, input_video_path, conf)

        db_save_records(result["records"], result["session_name"], source_type="video")

        return JSONResponse(content={
            "code": 200,
            "msg":  "视频检测完成",
            "data": {
                "session_name":     result["session_name"],
                "object_count":     result["object_count"],
                "result_video_url": f"{BASE_URL}/captures/{result['session_name']}/{result['output_filename']}",
                "csv_url":          f"{BASE_URL}/results/{result['session_name']}.csv",
            },
        })

    except Exception as e:
        return JSONResponse(status_code=500, content={"code": 500, "msg": str(e)})


# ── 摄像头实时检测 ─────────────────────────────────────────────────────────────

@router.websocket("/ws/camera")
async def camera_websocket(websocket: WebSocket):
    """
    摄像头实时检测 WebSocket 接口
    客户端发送 JSON : {"frame": "<base64 JPEG>", "conf": 0.3}
    服务端返回 JSON : {
        "objects":         [{"id": 1, "class_name": "person", "confidence": 0.85}],
        "annotated_frame": "<base64 JPEG>",
        "total_unique":    N,
        "session_name":    "报告_20260526_第1次",
        "csv_url":         "http://..."
    }
    """
    await websocket.accept()

    session_name   = get_session_name()
    seen_ids       = {}
    class_counters = {}
    records        = []
    db_saved_count = 0  # 记录已写入数据库的条数，避免重复写

    try:
        while True:
            data  = await websocket.receive_json()
            conf         = float(data.get("conf", 0.3))
            _hid         = data.get("highlight_id")
            highlight_id = int(_hid) if _hid else None

            img_bytes = base64.b64decode(data["frame"])
            nparr     = np.frombuffer(img_bytes, np.uint8)
            frame     = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            if frame is None:
                continue

            result = process_camera_frame(
                frame, conf, session_name, seen_ids, class_counters, records, highlight_id
            )

            # 有新目标时，只把本帧新增的记录写入数据库
            if result["new_record"]:
                new_entries = records[db_saved_count:]
                db_save_records(new_entries, session_name, source_type="camera")
                db_saved_count = len(records)

            await websocket.send_json({
                "objects":         result["objects"],
                "annotated_frame": result["annotated_frame"],
                "total_unique":    result["total_unique"],
                "session_name":    session_name,
                "csv_url":         f"{BASE_URL}/results/{session_name}.csv",
            })

    except WebSocketDisconnect:
        if records:
            save_csv(session_name, records)
        print(f"摄像头会话结束，共检测到 {len(seen_ids)} 个唯一目标")


# ── 历史数据查询 ───────────────────────────────────────────────────────────────

@router.get("/api/sessions")
async def list_sessions():
    """
    历史检测会话列表（从数据库读取）
    返回：[{"session_name": "报告_...", "csv_url": "http://..."}]
    """
    sessions = db_get_sessions()
    return JSONResponse(content={
        "code": 200,
        "data": [
            {
                "session_name": s,
                "csv_url":      f"{BASE_URL}/results/{s}.csv",
            }
            for s in sessions
        ],
    })


@router.get("/api/records")
async def get_records(session_name: str = None, class_name: str = None):
    """
    检测记录查询接口
    请求参数（均为可选 Query 参数）：
      - session_name : 按会话名过滤，如 报告_20260526_第1次
      - class_name   : 按类别过滤，如 person
    返回所有匹配记录（最新在前）
    """
    records = db_get_records(session_name=session_name, class_name=class_name)
    return JSONResponse(content={"code": 200, "total": len(records), "data": records})


# ── 导出检测报告 ──────────────────────────────────────────────────────────────

@router.get("/api/report/export")
async def export_report(session_name: str):
    """
    导出 Word 检测报告
    请求参数：
      - session_name : 会话名，如 报告_20260526_第1次
    返回：
      - .docx 文件下载
    """
    try:
        docx_path = await run_in_threadpool(generate_report, session_name)
        filename = os.path.basename(docx_path)
        return FileResponse(
            path=docx_path,
            filename=filename,
            media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        )
    except ValueError as e:
        return JSONResponse(status_code=404, content={"code": 404, "msg": str(e)})
    except Exception as e:
        return JSONResponse(status_code=500, content={"code": 500, "msg": str(e)})


@router.get("/api/video/export")
async def export_video(session_name: str):
    """
    导出检测后的视频
    请求参数：
      - session_name : 会话名，如 报告_20260526_第1次
    返回：
      - .mp4 视频文件下载
    """
    try:
        session_cap_dir = os.path.join(CAPTURES_DIR, session_name)
        if not os.path.exists(session_cap_dir):
            return JSONResponse(status_code=404, content={"code": 404, "msg": f"会话 '{session_name}' 不存在"})

        # 查找会话目录下的 tracked_*.mp4 文件
        video_files = [f for f in os.listdir(session_cap_dir) if f.startswith("tracked_") and f.endswith(".mp4")]
        if not video_files:
            return JSONResponse(status_code=404, content={"code": 404, "msg": f"会话 '{session_name}' 没有检测视频"})

        # 复制视频到 results/videos/ 目录
        source_video = os.path.join(session_cap_dir, video_files[0])
        video_filename = f"{session_name}_{video_files[0]}"
        dest_video = os.path.join(VIDEOS_DIR, video_filename)

        # 使用 shutil 复制文件
        import shutil
        shutil.copy2(source_video, dest_video)

        return FileResponse(
            path=dest_video,
            filename=video_filename,
            media_type="video/mp4",
        )
    except Exception as e:
        return JSONResponse(status_code=500, content={"code": 500, "msg": str(e)})
