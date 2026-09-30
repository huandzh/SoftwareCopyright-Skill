"""站内通知：生成完成、失败与预算提醒。"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Notification, Project, User

LEVELS = ("info", "warning", "error", "success")


@dataclass
class NotificationDraft:
    """待发送通知。"""

    level: str
    title: str
    body: str
    tags: list[str] = field(default_factory=list)


def stage_finished(project: Project) -> NotificationDraft:
    """阶段完成通知。"""
    return NotificationDraft(
        level="success",
        title=f"{project.name} 进入新阶段",
        body=f"当前阶段：{project.stage}，进度 {project.progress}%。",
        tags=["stage", project.stage],
    )


def stage_failed(project: Project, reason: str) -> NotificationDraft:
    """阶段失败通知，附带失败原因。"""
    return NotificationDraft(
        level="error",
        title=f"{project.name} 生成失败",
        body=reason[:300],
        tags=["stage", "failed"],
    )


def budget_warning(user: User, used: float) -> NotificationDraft:
    """预算提醒：使用超过 80% 时发出。"""
    percent = round(used / max(user.monthly_budget, 0.01) * 100)
    return NotificationDraft(
        level="warning",
        title="本月预算即将用完",
        body=f"已使用 {percent}%，新的生成任务可能会被暂停。",
        tags=["budget"],
    )


async def push(session: AsyncSession, user: User, draft: NotificationDraft) -> Notification:
    """写入通知记录。"""
    record = Notification(
        user_id=user.id,
        level=draft.level if draft.level in LEVELS else "info",
        title=draft.title,
        body=draft.body,
        tags=",".join(draft.tags),
        created_at=datetime.now(timezone.utc),
        read_at=None,
    )
    session.add(record)
    await session.flush()
    return record


async def unread_count(session: AsyncSession, user: User) -> int:
    """未读通知数量，用于顶部红点。"""
    result = await session.execute(
        select(Notification).where(Notification.user_id == user.id, Notification.read_at.is_(None))
    )
    return len(list(result.scalars()))
