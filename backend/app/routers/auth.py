import os
from fastapi import APIRouter, HTTPException, Request, Header
from pydantic import BaseModel
from typing import Optional
from slowapi import Limiter
from slowapi.util import get_remote_address

from app.models.db_factory import db, verify_password
from app.utils.jwt_handler import (
    create_access_token,
    create_refresh_token,
    verify_token,
)
from app.services.audit_logger import log_action

router = APIRouter()
_rate_limit_enabled = os.getenv("TESTING", "").lower() != "true"
limiter = Limiter(key_func=get_remote_address, enabled=_rate_limit_enabled)


class LoginRequest(BaseModel):
    username: str
    password: str


class RegisterRequest(BaseModel):
    username: str
    password: str
    name: str


class UserResponse(BaseModel):
    id: str
    username: str
    name: str
    role: str
    is_approved: bool


class LoginResponse(BaseModel):
    success: bool
    message: str
    user: Optional[UserResponse] = None
    access_token: Optional[str] = None
    refresh_token: Optional[str] = None
    token_type: Optional[str] = None


class RegisterResponse(BaseModel):
    success: bool
    message: str
    user: Optional[UserResponse] = None


class RefreshRequestBody(BaseModel):
    refresh_token: str


class RefreshResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


@router.post("/register", response_model=RegisterResponse)
@limiter.limit("3/minute")
async def register(request: Request, body: RegisterRequest):
    """물리치료사 회원가입"""
    # 아이디 중복 체크
    existing_user = db.get_user_by_username(body.username)
    if existing_user:
        raise HTTPException(status_code=400, detail="이미 사용 중인 아이디입니다.")

    # 사용자 생성
    try:
        user_data = {
            "username": body.username,
            "password": body.password,
            "name": body.name,
            "role": "therapist",
            "is_approved": 0
        }
        user = db.create_user(user_data)

        log_action(
            user_id=user["id"],
            action="register",
            resource_type="auth",
            resource_id=user["id"],
            details={"username": body.username},
            ip_address=request.client.host if request.client else None,
        )

        return {
            "success": True,
            "message": "회원가입이 완료되었습니다. 관리자 승인 후 이용 가능합니다.",
            "user": {
                "id": user["id"],
                "username": user["username"],
                "name": user["name"],
                "role": user["role"],
                "is_approved": bool(user["is_approved"])
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"회원가입 중 오류가 발생했습니다: {str(e)}")


@router.post("/login", response_model=LoginResponse)
@limiter.limit("5/minute")
async def login(request: Request, body: LoginRequest):
    """로그인 - JWT 토큰 반환"""
    # 사용자 조회
    user = db.get_user_by_username(body.username)
    if not user:
        log_action(
            user_id=None,
            action="login_failed",
            resource_type="auth",
            details={"username": body.username, "reason": "user_not_found"},
            ip_address=request.client.host if request.client else None,
        )
        raise HTTPException(status_code=401, detail="아이디 또는 비밀번호가 올바르지 않습니다.")

    # 비밀번호 검증
    if not verify_password(body.password, user["password_hash"]):
        log_action(
            user_id=user["id"],
            action="login_failed",
            resource_type="auth",
            resource_id=user["id"],
            details={"username": body.username, "reason": "wrong_password"},
            ip_address=request.client.host if request.client else None,
        )
        raise HTTPException(status_code=401, detail="아이디 또는 비밀번호가 올바르지 않습니다.")

    # JWT 토큰 생성
    access_token = create_access_token(
        user_id=user["id"],
        username=user["username"],
        role=user["role"],
        is_approved=bool(user["is_approved"]),
    )
    refresh_tok = create_refresh_token(user_id=user["id"])

    log_action(
        user_id=user["id"],
        action="login",
        resource_type="auth",
        resource_id=user["id"],
        details={"username": body.username},
        ip_address=request.client.host if request.client else None,
    )

    return {
        "success": True,
        "message": "로그인 성공",
        "user": {
            "id": user["id"],
            "username": user["username"],
            "name": user["name"],
            "role": user["role"],
            "is_approved": bool(user["is_approved"])
        },
        "access_token": access_token,
        "refresh_token": refresh_tok,
        "token_type": "bearer",
    }


@router.post("/refresh", response_model=RefreshResponse)
async def refresh_token_endpoint(body: RefreshRequestBody):
    """Refresh access token using a valid refresh token."""
    payload = verify_token(body.refresh_token)
    if not payload or payload.get("type") != "refresh":
        raise HTTPException(status_code=401, detail="유효하지 않은 리프레시 토큰입니다.")

    user_id = payload.get("sub")
    user = db.get_user(user_id)
    if not user:
        raise HTTPException(status_code=401, detail="사용자를 찾을 수 없습니다.")

    new_access_token = create_access_token(
        user_id=user["id"],
        username=user["username"],
        role=user["role"],
        is_approved=bool(user["is_approved"]),
    )

    return {
        "access_token": new_access_token,
        "token_type": "bearer",
    }


@router.get("/me")
async def get_current_user(authorization: Optional[str] = Header(None)):
    """현재 사용자 정보 조회 - JWT 토큰 기반"""
    if not authorization or not authorization.startswith("Bearer "):
        return {"message": "사용자 정보는 클라이언트에서 관리됩니다."}

    token = authorization.split(" ", 1)[1]
    payload = verify_token(token)
    if not payload or payload.get("type") != "access":
        raise HTTPException(status_code=401, detail="유효하지 않은 토큰입니다.")

    user = db.get_user(payload["sub"])
    if not user:
        raise HTTPException(status_code=401, detail="사용자를 찾을 수 없습니다.")

    return {
        "id": user["id"],
        "username": user["username"],
        "name": user["name"],
        "role": user["role"],
        "is_approved": bool(user["is_approved"]),
    }
