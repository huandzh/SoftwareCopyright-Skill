"""任务、智能体与通知接口。"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import current_user
from app.core.database import get_session
from app.models import GenerationTask, Notification, Project, TaskEvent, User
from app.services.agent_orchestrator import AGENTS
from app.services.budget_guard import check_budget, estimate_stage_cost

router = APIRouter()


@router.get("/projects/{project_id}/tasks")
async def list_tasks(
    project_id: str,
    limit: int = Query(default=20, ge=1, le=100),
    session: AsyncSession = Depends(get_session),
    user: User = Depends(current_user),
) -> list[dict]:
    """返回项目的生成任务列表，按创建时间倒序。"""
    project = await _load_project(session, project_id, user)
    result = await session.execute(
        select(GenerationTask)
        .where(GenerationTask.project_id == project.id)
        .order_by(GenerationTask.created_at.desc())
        .limit(limit)
    )
    return [
        {
            "id": task.id,
            "stage": task.stage,
            "agent_key": task.agent_key,
            "status": task.status,
            "attempts": task.attempts,
            "cost": task.cost,
            "duration_seconds": task.duration_seconds,
            "last_error": task.last_error,
        }
        for task in result.scalars()
    ]


@router.get("/projects/{project_id}/tasks/{task_id}/events")
async def list_task_events(
    project_id: str,
    task_id: str,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(current_user),
) -> list[dict]:
    """生成时间线：按时间顺序返回任务事件。"""
    await _load_project(session, project_id, user)
    result = await session.execute(
        select(TaskEvent).where(TaskEvent.task_id == task_id).order_by(TaskEvent.created_at)
    )
    return [
        {
            "id": event.id,
            "type": event.type,
            "message": event.message,
            "detail": event.detail,
            "duration_ms": event.duration_ms,
            "created_at": event.created_at,
        }
        for event in result.scalars()
    ]


@router.get("/projects/{project_id}/budget/check")
async def budget_check(
    project_id: str,
    shots: int = Query(default=1, ge=1, le=200),
    session: AsyncSession = Depends(get_session),
    user: User = Depends(current_user),
) -> dict:
    """生成前预算检查：返回是否允许以及预估花费。"""
    project = await _load_project(session, project_id, user)
    estimated = estimate_stage_cost(project, shots)
    decision = check_budget(user, project, estimated)
    return {
        "allowed": decision.allowed,
        "estimated_cost": decision.estimated_cost,
        "reason": decision.reason,
    }


@router.get("/agents")
async def list_agents() -> list[dict[str, str]]:
    """返回平台内置的制片角色清单。"""
    return [dict(agent) for agent in AGENTS]


@router.get("/notifications")
async def list_notifications(
    unread_only: bool = Query(default=False),
    session: AsyncSession = Depends(get_session),
    user: User = Depends(current_user),
) -> list[dict]:
    """返回当前账号的通知。"""
    statement = select(Notification).where(Notification.user_id == user.id)
    if unread_only:
        statement = statement.where(Notification.read.is_(False))
    result = await session.execute(statement.order_by(Notification.created_at.desc()).limit(50))
    return [
        {
            "id": item.id,
            "level": item.level,
            "title": item.title,
            "body": item.body,
            "read": item.read,
            "created_at": item.created_at,
        }
        for item in result.scalars()
    ]


@router.post("/notifications/{notification_id}/read", status_code=status.HTTP_204_NO_CONTENT)
async def mark_notification_read(
    notification_id: str,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(current_user),
) -> None:
    """标记通知为已读。"""
    result = await session.execute(
        select(Notification).where(
            Notification.id == notification_id, Notification.user_id == user.id
        )
    )
    item = result.scalar_one_or_none()
    if item is None:
        raise HTTPException(status_code=404, detail="通知不存在")
    item.mark_read()


async def _load_project(session: AsyncSession, project_id: str, user: User) -> Project:
    result = await session.execute(
        select(Project).where(Project.id == project_id, Project.owner_id == user.id)
    )
    project = result.scalar_one_or_none()
    if project is None:
        raise HTTPException(status_code=404, detail="项目不存在或无权访问")
    return project
