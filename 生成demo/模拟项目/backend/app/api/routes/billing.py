"""计费与账号接口。"""

from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import current_user
from app.core.database import get_session
from app.core.security import hash_password, issue_session_token, password_strength_issues, verify_password
from app.models import Project, User
from app.schemas import BillingSummaryOut, LoginIn, RegisterIn
from app.services.cost_service import billing_summary

router = APIRouter()


@router.get("/summary", response_model=BillingSummaryOut)
async def get_billing_summary(
    session: AsyncSession = Depends(get_session),
    user: User = Depends(current_user),
) -> dict:
    """本月计费汇总：按计费项拆分金额并返回预算。"""
    return await billing_summary(session, user)


auth_router = APIRouter()


@auth_router.post("/register", status_code=status.HTTP_201_CREATED)
async def register(
    payload: RegisterIn,
    response: Response,
    session: AsyncSession = Depends(get_session),
) -> dict[str, str]:
    """注册账号：校验口令强度、查重邮箱并直接下发会话。"""
    issues = password_strength_issues(payload.password)
    if issues:
        raise HTTPException(status_code=422, detail="；".join(issues))

    existing = await session.execute(select(User).where(User.email == payload.email.lower()))
    if existing.scalar_one_or_none() is not None:
        raise HTTPException(status_code=409, detail="该邮箱已经注册，请直接登录")

    salt, digest = hash_password(payload.password)
    user = User(
        email=payload.email.lower(),
        display_name=payload.display_name.strip(),
        password_salt=salt,
        password_hash=digest,
        monthly_budget=200.0,
    )
    session.add(user)
    await session.flush()

    token, expires_at = issue_session_token(user.id)
    _set_session_cookie(response, token, expires_at)
    return {"user_id": user.id, "display_name": user.display_name}


@auth_router.post("/login")
async def login(
    payload: LoginIn,
    response: Response,
    session: AsyncSession = Depends(get_session),
) -> dict[str, str]:
    """登录：校验口令并签发会话 Cookie。"""
    result = await session.execute(select(User).where(User.email == payload.email.lower()))
    user = result.scalar_one_or_none()
    if user is None or not verify_password(payload.password, user.password_salt, user.password_hash):
        raise HTTPException(status_code=401, detail="邮箱或密码不正确")
    if not user.is_active:
        raise HTTPException(status_code=403, detail="账号已停用，请联系管理员")

    token, expires_at = issue_session_token(user.id)
    _set_session_cookie(response, token, expires_at)
    return {"user_id": user.id, "display_name": user.display_name}


@auth_router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(response: Response) -> None:
    """退出登录：清除会话 Cookie。"""
    response.delete_cookie("studio_session", path="/")


@auth_router.get("/me")
async def me(user: User = Depends(current_user)) -> dict[str, str | float]:
    """返回当前登录账号的概要信息。"""
    return {
        "user_id": user.id,
        "email": user.email,
        "display_name": user.display_name,
        "monthly_budget": user.monthly_budget,
    }


def _set_session_cookie(response: Response, token: str, expires_at: int) -> None:
    # HttpOnly + SameSite=Lax：前端脚本拿不到令牌，降低 XSS 风险
    response.set_cookie(
        "studio_session",
        token,
        httponly=True,
        samesite="lax",
        secure=False,
        max_age=max(0, expires_at - int(date.today().strftime("%s") or 0)),
        path="/",
    )
