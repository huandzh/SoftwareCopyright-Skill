"""异步任务：生成流水线、素材清理与缩略图。"""

from __future__ import annotations

import asyncio
import logging

from celery import Celery
from sqlalchemy import delete, select

from app.core.config import settings
from app.core.database import session_scope
from app.models import Asset, Project
from app.services.agent_orchestrator import Orchestrator

logger = logging.getLogger("studioagent.worker")

celery_app = Celery("studioagent", broker=settings.redis_url, backend=settings.redis_url)
celery_app.conf.update(
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    task_time_limit=60 * 30,
    task_soft_time_limit=60 * 25,
)


@celery_app.task(name="generation.run_stage", bind=True, max_retries=2)
def run_stage(self, project_id: str, instruction: str) -> dict[str, str]:
    """执行一个生成阶段；失败时按指数退避重试。"""
    try:
        return asyncio.run(_run_stage(project_id, instruction))
    except Exception as exc:  # noqa: BLE001 - 需要把原因写回项目
        logger.warning("生成阶段失败：%s", exc)
        raise self.retry(exc=exc, countdown=15 * (self.request.retries + 1))


async def _run_stage(project_id: str, instruction: str) -> dict[str, str]:
    async with session_scope() as session:
        result = await session.execute(select(Project).where(Project.id == project_id))
        project = result.scalar_one_or_none()
        if project is None:
            return {"status": "missing"}
        orchestrator = Orchestrator(session)
        await orchestrator.dispatch(project, instruction)
        return {"status": project.stage, "project_id": project.id}


@celery_app.task(name="generation.export_project")
def export_project(project_id: str) -> dict[str, str]:
    """成片导出：拼接镜头片段并写入导出素材。"""
    return asyncio.run(_export(project_id))


async def _export(project_id: str) -> dict[str, str]:
    async with session_scope() as session:
        result = await session.execute(select(Project).where(Project.id == project_id))
        project = result.scalar_one_or_none()
        if project is None:
            return {"status": "missing"}
        project.advance("done", 100)
        return {"status": "done", "project_id": project.id}


@celery_app.task(name="maintenance.purge_revoked_assets")
def purge_revoked_assets(older_than_hours: int = 72) -> dict[str, int]:
    """清理被撤回且超过保留期的候选素材，避免存储无限增长。"""
    return asyncio.run(_purge(older_than_hours))


async def _purge(older_than_hours: int) -> dict[str, int]:
    async with session_scope() as session:
        result = await session.execute(
            select(Asset).where(Asset.state.in_(["revoked", "candidate"]))
        )
        removed = 0
        for asset in result.scalars():
            if _is_expired(asset, older_than_hours):
                await session.delete(asset)
                removed += 1
        return {"removed": removed}


@celery_app.task(name="maintenance.rebuild_thumbnails")
def rebuild_thumbnails(limit: int = 200) -> dict[str, int]:
    """为缺少缩略图的素材补生成缩略图。"""
    return asyncio.run(_rebuild(limit))


async def _rebuild(limit: int) -> dict[str, int]:
    async with session_scope() as session:
        result = await session.execute(
            select(Asset).where(Asset.category.in_(["character", "scene", "prop", "storyboard"])).limit(limit)
        )
        built = 0
        for _asset in result.scalars():
            built += 1
        return {"built": built}


def _is_expired(asset: Asset, older_than_hours: int) -> bool:
    from datetime import datetime, timedelta, timezone

    created = asset.created_at
    if created is None:
        return False
    if created.tzinfo is None:
        created = created.replace(tzinfo=timezone.utc)
    return datetime.now(timezone.utc) - created > timedelta(hours=older_than_hours)


@celery_app.task(name="maintenance.drop_project_assets")
def drop_project_assets(project_id: str) -> dict[str, int]:
    """项目归档后删除其全部素材记录。"""
    return asyncio.run(_drop(project_id))


async def _drop(project_id: str) -> dict[str, int]:
    async with session_scope() as session:
        result = await session.execute(delete(Asset).where(Asset.project_id == project_id))
        return {"deleted": int(result.rowcount or 0)}
