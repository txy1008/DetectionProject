import os
import threading
import time
from pathlib import Path
import datetime

import cv2
import pandas as pd
import bcrypt
import jwt
import mysql.connector
from fastapi import FastAPI, File, UploadFile, Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from pydantic import BaseModel

import config
from processor import DetectionProcessor


# JWT and Auth Setup
JWT_SECRET = "super-secret-key-vision-project-2026"
JWT_ALGORITHM = "HS256"
security = HTTPBearer(auto_error=False)

def create_access_token(username: str) -> str:
    expire = datetime.datetime.utcnow() + datetime.timedelta(hours=2)
    payload = {
        "sub": username,
        "exp": expire
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)

async def get_current_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
    token: str | None = None
):
    actual_token = None
    if credentials:
        actual_token = credentials.credentials
    elif token:
        actual_token = token
    else:
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            actual_token = auth_header.split(" ")[1]

    if not actual_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        payload = jwt.decode(actual_token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token claims",
                headers={"WWW-Authenticate": "Bearer"},
            )
        return username
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token expired",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except jwt.PyJWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

# Database Setup
def init_db():
    try:
        cfg = config.DB_CONFIG.copy()
        db_name = cfg.pop('database', 'traffic_system_db')
        conn = mysql.connector.connect(**cfg)
        cursor = conn.cursor()
        cursor.execute(f"CREATE DATABASE IF NOT EXISTS {db_name} CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
        cursor.close()
        conn.close()

        conn = mysql.connector.connect(**config.DB_CONFIG)
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INT AUTO_INCREMENT PRIMARY KEY,
                username VARCHAR(50) UNIQUE NOT NULL,
                password VARCHAR(255) NOT NULL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
        """)
        conn.commit()
        cursor.close()
        conn.close()
        print("[Database] MySQL initialization complete. 'users' table is ready.")
    except Exception as e:
        print(f"[Database] MySQL initialization failed: {e}")

init_db()


app = FastAPI(title="Smart Intersection Detection API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
Path("uploads").mkdir(exist_ok=True)
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")

processor = DetectionProcessor()
state_lock = threading.Lock()
is_running = False
is_paused = False
source = 0
capture = None
video_writer = None
latest_results = []
latest_frame = None
latest_annotated = None
last_source_frame = None


class UserAuth(BaseModel):
    username: str
    password: str


class ModelRequest(BaseModel):
    model: str


class ConfidenceRequest(BaseModel):
    confidence: float


class StartRequest(BaseModel):
    model: str | None = None
    confidence: float | None = None


def normalize_model_path(model_name: str) -> str:
    model_path = Path(model_name)
    if model_path.is_absolute():
        return str(model_path)
    return str(Path("models") / model_path.name)


def ensure_session():
    if not processor.session_name:
        processor.start_session()


def start_new_detection_session(username: str = "default"):
    global latest_results, latest_frame, latest_annotated
    session_name = processor.start_session(username)
    latest_results = []
    latest_frame = None
    latest_annotated = None
    return session_name


def append_records(records):
    global latest_results
    if records:
        latest_results = [*latest_results, *records][-300:]


def encode_jpeg(frame):
    ok, buffer = cv2.imencode(".jpg", frame)
    if not ok:
        return None
    return buffer.tobytes()


def safe_csv_path(file_name: str, username: str = "default") -> Path:
    candidate = Path(config.RESULTS_DIR) / username / Path(file_name).name
    if not candidate.exists() or candidate.suffix.lower() != ".csv":
        raise FileNotFoundError(file_name)
    return candidate


def read_history_records(file_name: str, username: str = "default"):
    csv_path = safe_csv_path(file_name, username)
    df = pd.read_csv(csv_path, encoding="utf-8-sig")
    records = []
    for index, row in df.fillna("").iterrows():
        records.append({
            "id": row.get("ID", index + 1),
            "category": row.get("类别", row.get("category", "")),
            "time": row.get("时间", row.get("time", "")),
            "path": row.get("存储路径", row.get("path", "")),
        })
    return csv_path, records


def draw_single_highlight(target_id: int):
    if latest_frame is None:
        return None
    target = None
    for item in latest_results:
        if str(item.get("id")) == str(target_id):
            target = item
            break
    if not target or not target.get("box"):
        return None
    frame = latest_frame.copy()
    x1, y1, x2, y2 = map(int, target["box"])
    category = target.get("category", target.get("type", "target"))
    confidence = float(target.get("confidence", 0))
    color = (173, 252, 221)
    cv2.rectangle(frame, (x1, y1), (x2, y2), color, 5)
    cv2.putText(frame, f"{category} ID:{target_id} {confidence:.2f}", (x1, max(30, y1 - 12)),
                cv2.FONT_HERSHEY_SIMPLEX, 0.9, color, 3)
    output_path = Path(config.RESULTS_DIR) / f"highlight_{target_id}.jpg"
    cv2.imwrite(str(output_path), frame)
    return output_path


def frame_generator():
    global capture, latest_frame, latest_annotated, is_running, is_paused, source, video_writer
    ensure_session()
    fps = 20.0
    while True:
        start_time = time.time()
        with state_lock:
            if not is_running:
                if video_writer is not None:
                    video_writer.release()
                    video_writer = None
                time.sleep(0.1)
                continue
            if is_paused:
                if latest_annotated is not None:
                    data = encode_jpeg(latest_annotated)
                    if data is not None:
                        yield b"--frame\r\nContent-Type: image/jpeg\r\n\r\n" + data + b"\r\n"
                time.sleep(0.2)
                continue
            if capture is None or not capture.isOpened():
                capture = cv2.VideoCapture(source)
                if video_writer is not None:
                    video_writer.release()
                    video_writer = None
                fps = capture.get(cv2.CAP_PROP_FPS)
                if fps <= 0 or fps > 100:
                    fps = 20.0
                width = int(capture.get(cv2.CAP_PROP_FRAME_WIDTH))
                height = int(capture.get(cv2.CAP_PROP_FRAME_HEIGHT))
                if width > 0 and height > 0:
                    user_results_dir = os.path.join(config.RESULTS_DIR, processor.session_user)
                    os.makedirs(user_results_dir, exist_ok=True)
                    output_path = Path(user_results_dir) / f"{processor.session_name}_result.mp4"
                    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
                    video_writer = cv2.VideoWriter(str(output_path), fourcc, fps, (width, height))
            ok, frame = capture.read()
            if not ok:
                is_running = False
                is_paused = False
                if capture is not None:
                    capture.release()
                    capture = None
                if video_writer is not None:
                    video_writer.release()
                    video_writer = None
                break
        annotated, records = processor.process_frame(frame, is_image=False)
        with state_lock:
            latest_frame = frame
            latest_annotated = annotated
            append_records(records)
            data = encode_jpeg(annotated)
            if video_writer is not None:
                video_writer.write(annotated)
        if data is None:
            continue
        yield b"--frame\r\nContent-Type: image/jpeg\r\n\r\n" + data + b"\r\n"
        
        # Pacing: limit loop speed to match original video FPS
        if fps > 0:
            frame_delay = 1.0 / fps
            elapsed = time.time() - start_time
            sleep_time = frame_delay - elapsed
            if sleep_time > 0:
                time.sleep(sleep_time)

def original_frame_generator():
    while True:
        if latest_frame is None:
            time.sleep(0.1)
            continue
        data = encode_jpeg(latest_frame)
        if data is None:
            time.sleep(0.1)
            continue
        yield b"--frame\r\nContent-Type: image/jpeg\r\n\r\n" + data + b"\r\n"


def register_routes(prefix: str = ""):
    @app.post(f"{prefix}/register")
    def register(payload: UserAuth):
        username = payload.username.strip()
        password = payload.password
        if len(username) < 3 or len(username) > 20:
            return JSONResponse({"success": False, "message": "用户名长度需在3-20个字符之间"}, status_code=400)
        if len(password) < 6 or len(password) > 20:
            return JSONResponse({"success": False, "message": "密码长度需在6-20个字符之间"}, status_code=400)

        try:
            conn = mysql.connector.connect(**config.DB_CONFIG)
            cursor = conn.cursor()
            cursor.execute("SELECT id FROM users WHERE username = %s", (username,))
            user = cursor.fetchone()
            if user:
                cursor.close()
                conn.close()
                return JSONResponse({"success": False, "message": "该用户名已被注册"}, status_code=400)

            hashed = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
            cursor.execute("INSERT INTO users (username, password) VALUES (%s, %s)", (username, hashed))
            conn.commit()
            cursor.close()
            conn.close()
            return {"success": True, "message": "注册成功"}
        except Exception as e:
            return JSONResponse({"success": False, "message": f"系统错误: {str(e)}"}, status_code=500)

    @app.post(f"{prefix}/login")
    def login(payload: UserAuth):
        username = payload.username.strip()
        password = payload.password

        try:
            conn = mysql.connector.connect(**config.DB_CONFIG)
            cursor = conn.cursor()
            cursor.execute("SELECT password FROM users WHERE username = %s", (username,))
            user = cursor.fetchone()
            cursor.close()
            conn.close()

            if not user:
                return JSONResponse({"success": False, "message": "用户名或密码错误"}, status_code=401)

            hashed_password = user[0]
            if bcrypt.checkpw(password.encode('utf-8'), hashed_password.encode('utf-8')):
                token = create_access_token(username)
                return {
                    "success": True,
                    "message": "登录成功",
                    "token": token,
                    "username": username
                }
            else:
                return JSONResponse({"success": False, "message": "用户名或密码错误"}, status_code=401)
        except Exception as e:
            return JSONResponse({"success": False, "message": f"系统错误: {str(e)}"}, status_code=500)

    @app.get(f"{prefix}/health")
    def health():
        return {"status": "ok", "model": config.MODEL_PATH, "running": is_running}

    @app.get(f"{prefix}/models")
    def models():
        model_dir = Path("models")
        return {"models": [p.name for p in model_dir.glob("*.pt")]}

    @app.post(f"{prefix}/set_model", dependencies=[Depends(get_current_user)])
    def set_model(payload: ModelRequest):
        model_path = normalize_model_path(payload.model)
        ok = processor.change_model(model_path)
        return {"success": ok, "model": model_path, "names": processor.model.names}

    @app.post(f"{prefix}/set_confidence", dependencies=[Depends(get_current_user)])
    def set_confidence(payload: ConfidenceRequest):
        processor.conf_threshold = float(payload.confidence)
        return {"success": True, "confidence": processor.conf_threshold}

    @app.post(f"{prefix}/open_camera")
    def open_camera(username: str = Depends(get_current_user)):
        global source, capture, is_running, is_paused
        session_name = start_new_detection_session(username)
        with state_lock:
            source = 0
            is_running = True
            is_paused = False
        if capture is not None:
            capture.release()
            capture = None
        return {"success": True, "source": "camera", "running": is_running, "session": session_name}

    @app.post(f"{prefix}/start_detection")
    def start_detection(payload: StartRequest | None = None, username: str = Depends(get_current_user)):
        global is_running, is_paused, latest_results
        session_name = processor.session_name if is_running and processor.session_name else start_new_detection_session(username)
        if payload and payload.model:
            processor.change_model(normalize_model_path(payload.model))
        if payload and payload.confidence is not None:
            processor.conf_threshold = float(payload.confidence)
        with state_lock:
            is_running = True
            is_paused = False
        return {"success": True, "running": is_running, "session": session_name}

    @app.post(f"{prefix}/pause_detection", dependencies=[Depends(get_current_user)])
    def pause_detection():
        global is_paused
        with state_lock:
            is_paused = True
        return {"success": True, "paused": is_paused}

    @app.post(f"{prefix}/stop_detection", dependencies=[Depends(get_current_user)])
    def stop_detection():
        global is_running, is_paused, capture, video_writer
        with state_lock:
            is_running = False
            is_paused = False
            if capture is not None:
                capture.release()
                capture = None
            if video_writer is not None:
                video_writer.release()
                video_writer = None
        return {"success": True, "running": is_running}

    @app.post(f"{prefix}/upload")
    async def upload(file: UploadFile = File(...), username: str = Depends(get_current_user)):
        global source, capture, latest_results, latest_frame, latest_annotated, is_running, is_paused, video_writer
        session_name = start_new_detection_session(username)
        upload_dir = Path("uploads")
        upload_dir.mkdir(exist_ok=True)
        file_path = upload_dir / file.filename
        file_path.write_bytes(await file.read())
        suffix = file_path.suffix.lower()
        if suffix in {".jpg", ".jpeg", ".png", ".bmp", ".webp"}:
            frame = cv2.imread(str(file_path))
            if frame is None:
                return JSONResponse({"success": False, "message": "无法读取图片"}, status_code=400)
            annotated, records = processor.process_frame(frame, is_image=True)
            latest_frame = frame
            latest_annotated = annotated
            append_records(records)
            original_path = Path(config.RESULTS_DIR) / f"latest_upload_original_{username}.jpg"
            result_path = Path(config.RESULTS_DIR) / f"latest_upload_result_{username}.jpg"
            cv2.imwrite(str(original_path), frame)
            cv2.imwrite(str(result_path), annotated)
            image_prefix = f"/{prefix.strip('/')}" if prefix else ""
            return {
                "success": True,
                "type": "image",
                "session": session_name,
                "csv": f"{session_name}.csv",
                "results": latest_results,
                "original_image": f"{image_prefix}/latest_original",
                "result_image": f"{image_prefix}/latest_result"
            }
        with state_lock:
            source = str(file_path)
            is_running = True
            is_paused = False
            if capture is not None:
                capture.release()
                capture = None
            if video_writer is not None:
                video_writer.release()
                video_writer = None
        return {
            "success": True,
            "type": "video",
            "path": str(file_path),
            "video_url": f"/uploads/{file_path.name}",
            "running": is_running,
            "session": session_name,
            "csv": f"{session_name}.csv"
        }

    @app.get(f"{prefix}/export_video")
    def export_video(username: str = Depends(get_current_user)):
        if not processor.session_name:
            raise HTTPException(status_code=400, detail="没有正在运行的检测会话")
        
        user_results_dir = Path(config.RESULTS_DIR) / username
        output_path = user_results_dir / f"{processor.session_name}_result.mp4"
        
        global video_writer
        with state_lock:
            if video_writer is not None:
                video_writer.release()
                video_writer = None
                
        if not output_path.exists():
            raise HTTPException(status_code=404, detail="未找到当前会话的检测结果视频，可能当前检测的不是视频文件")
            
        return FileResponse(
            path=str(output_path),
            filename=f"{processor.session_name}_检测结果.mp4",
            media_type="video/mp4"
        )

    @app.get(f"{prefix}/video_feed")
    def video_feed():
        return StreamingResponse(frame_generator(), media_type="multipart/x-mixed-replace; boundary=frame")

    @app.get(f"{prefix}/original_feed")
    def original_feed():
        return StreamingResponse(original_frame_generator(), media_type="multipart/x-mixed-replace; boundary=frame")

    @app.get(f"{prefix}/detection_results", dependencies=[Depends(get_current_user)])
    def detection_results():
        return {"results": latest_results, "stats": processor.get_stats(), "summary": processor.get_summary(), "session": processor.session_name, "csv": f"{processor.session_name}.csv" if processor.session_name else ""}

    @app.get(f"{prefix}/latest_result")
    def latest_result(username: str = Depends(get_current_user)):
        result_path = Path(config.RESULTS_DIR) / f"latest_upload_result_{username}.jpg"
        if result_path.exists():
            return FileResponse(result_path)
        return JSONResponse({"message": "no result"}, status_code=404)

    @app.get(f"{prefix}/latest_original")
    def latest_original(username: str = Depends(get_current_user)):
        result_path = Path(config.RESULTS_DIR) / f"latest_upload_original_{username}.jpg"
        if result_path.exists():
            return FileResponse(result_path)
        return JSONResponse({"message": "no original"}, status_code=404)

    @app.get(f"{prefix}/highlight/{{target_id}}")
    def highlight_target(target_id: int):
        path = draw_single_highlight(target_id)
        if not path:
            return JSONResponse({"message": "target not found"}, status_code=404)
        return FileResponse(path)

    @app.get(f"{prefix}/export_csv")
    def export_csv(username: str = Depends(get_current_user)):
        if not processor.session_name:
            return JSONResponse({"message": "no session"}, status_code=404)
        csv_path = Path(config.RESULTS_DIR) / username / f"{processor.session_name}.csv"
        if not csv_path.exists():
            return JSONResponse({"message": "csv not found"}, status_code=404)
        return FileResponse(csv_path, filename=csv_path.name, media_type="text/csv")

    @app.get(f"{prefix}/export_word")
    def export_word(username: str = Depends(get_current_user)):
        user_results_dir = os.path.join(config.RESULTS_DIR, username)
        os.makedirs(user_results_dir, exist_ok=True)
        report_path = processor.generate_word_report(save_path=os.path.join(user_results_dir, f"{processor.session_name}.docx"))
        if not report_path:
            return JSONResponse({"message": "no records"}, status_code=404)
        path = Path(report_path)
        return FileResponse(path, filename=path.name)

    @app.get(f"{prefix}/export_pdf")
    def export_pdf(username: str = Depends(get_current_user)):
        return export_word(username)

    @app.get(f"{prefix}/history/files")
    def history_files(username: str = Depends(get_current_user)):
        user_result_dir = Path(config.RESULTS_DIR) / username
        user_result_dir.mkdir(parents=True, exist_ok=True)
        files = []
        for path in sorted(user_result_dir.glob("*.csv"), key=lambda item: item.stat().st_mtime, reverse=True):
            files.append({
                "name": path.name,
                "size_kb": round(path.stat().st_size / 1024, 2),
                "modified": path.stat().st_mtime
            })
        return {"files": files}

    @app.get(f"{prefix}/history/data")
    def history_data(file: str, username: str = Depends(get_current_user)):
        try:
            csv_path, records = read_history_records(file, username)
        except FileNotFoundError:
            return JSONResponse({"message": "csv not found"}, status_code=404)
        return {"file": csv_path.name, "records": records}

    @app.get(f"{prefix}/history/export_word")
    def history_export_word(file: str, username: str = Depends(get_current_user)):
        try:
            csv_path, records = read_history_records(file, username)
        except FileNotFoundError:
            return JSONResponse({"message": "csv not found"}, status_code=404)
        original_records = processor.session_records
        original_session = processor.session_name
        processor.session_records = [{"ID": r["id"], "类别": r["category"], "时间": r["time"], "存储路径": r["path"]} for r in records]
        processor.session_name = csv_path.stem
        user_result_dir = Path(config.RESULTS_DIR) / username
        report_path = processor.generate_word_report(user_result_dir / f"{csv_path.stem}.docx")
        processor.session_records = original_records
        processor.session_name = original_session
        if not report_path:
            return JSONResponse({"message": "no records"}, status_code=404)
        path = Path(report_path)
        return FileResponse(path, filename=path.name)

    @app.get(f"{prefix}/history/export_pdf")
    def history_export_pdf(file: str, username: str = Depends(get_current_user)):
        return history_export_word(file, username)


register_routes("")
register_routes("/api")
