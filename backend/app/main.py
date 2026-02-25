import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from dotenv import load_dotenv
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from app.routers import patients, tests, auth, admin, goals, websocket, emr, notifications, dashboard, tug_realtime, distance_goals, walking_routes

# Ensure db_factory is imported early so it selects the right backend
from app.models import db_factory as _dbf  # noqa: F401

load_dotenv()

# Rate limiter: 100 requests/minute per IP by default
# Disable in test mode (TESTING env var set by conftest.py)
_rate_limit_enabled = os.getenv("TESTING", "").lower() != "true"
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["100/minute"],
    enabled=_rate_limit_enabled,
)

app = FastAPI(
    title="10m Walk Test API",
    description="물리치료사를 위한 10m 보행 검사 분석 시스템",
    version="1.0.0"
)

# Attach rate limiter
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-Total-Frames", "X-FPS", "X-Current-Frame"],
)

# 업로드 디렉토리 생성
UPLOAD_DIR = os.getenv("UPLOAD_DIR", "./uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)

# 정적 파일 서빙 (업로드된 동영상)
app.mount("/uploads", StaticFiles(directory=UPLOAD_DIR), name="uploads")

# 라우터 등록
app.include_router(auth.router, prefix="/api/auth", tags=["auth"])
app.include_router(admin.router, prefix="/api/admin", tags=["admin"])
app.include_router(patients.router, prefix="/api/patients", tags=["patients"])
app.include_router(tests.router, prefix="/api/tests", tags=["tests"])
app.include_router(goals.router, prefix="/api/goals", tags=["goals"])
app.include_router(websocket.router, tags=["websocket"])
app.include_router(emr.router, prefix="/api/emr", tags=["emr"])
app.include_router(notifications.router, prefix="/api/notifications", tags=["notifications"])
app.include_router(dashboard.router, prefix="/api/dashboard", tags=["dashboard"])
app.include_router(tug_realtime.router, tags=["tug-realtime"])
app.include_router(distance_goals.router, prefix="/api/distance-goals", tags=["distance-goals"])
app.include_router(walking_routes.router, prefix="/api/walking-routes", tags=["walking-routes"])


@app.on_event("startup")
async def startup_event():
    """Initialize database tables on startup."""
    from app.models.db_factory import init_db
    try:
        init_db()
        print("[STARTUP] Database initialized successfully")
    except Exception as e:
        print(f"[STARTUP] Database init warning: {e}")


@app.get("/")
async def root():
    return {"message": "ReStep API", "version": "2.0.0"}


@app.get("/health")
async def health_check():
    return {"status": "healthy"}


