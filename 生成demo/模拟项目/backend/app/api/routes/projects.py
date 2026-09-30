"""项目相关接口：列表、详情、创建、更新、归档与导出。"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import current_user
from app.core.database import get_session
from app.models import Asset, Project, User
from app.schemas import (
    ProjectCreate,
    ProjectDetailOut,
    ProjectOut,
    ProjectUpdate,
)
from app.services.agent_orchestrator import agent_statuses
from app.services.cost_service import project_cost

router = APIRouter()


@router.get("", response_model=list[ProjectOut])
async def list_projects(
    session: AsyncSession = Depends(get_session),
    user: User = Depends(current_user),
) -> list[Project]:
    """按更新时间倒序返回当前账号的项目列表。"""
    result = await session.execute(
        select(Project).where(Project.owner_id == user.id).order_by(Project.updated_at.desc())
    )
    return list(result.scalars())


@router.post("", response_model=ProjectOut, status_code=status.HTTP_201_CREATED)
async def create_project(
    payload: ProjectCreate,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(current_user),
) -> Project:
    """创建项目：只保存名称与创意描述，后续阶段由智能体推进。"""
    project = Project(
        owner_id=user.id,
        name=payload.name.strip(),
        idea=payload.idea.strip(),
        model_profile=payload.model_profile,
        stage="draft",
        progress=0,
    )
    session.add(project)
    await session.flush()
    return project


@router.get("/{project_id}", response_model=ProjectDetailOut)
async def get_project(
    project_id: str,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(current_user),
) -> dict:
    """项目详情：附带六个智能体的当前状态与成本汇总。"""
    project = await _load_project(session, project_id, user)
    cost = await project_cost(session, project)
    return {
        "id": project.id,
        "name": project.name,
        "idea": project.idea,
        "stage": project.stage,
        "progress": project.progress,
        "duration_seconds": project.duration_seconds,
        "shot_count": project.shot_count,
        "updated_at": project.updated_at,
        "last_error": project.last_error,
        "created_at": project.created_at,
        "model_profile": project.model_profile,
        "agents": agent_statuses(project),
        "cost": cost,
    }


@router.patch("/{project_id}", response_model=ProjectOut)
async def update_project(
    project_id: str,
    payload: ProjectUpdate,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(current_user),
) -> Project:
    """修改项目名称、创意描述或模型档位；已完成的阶段不会被回退。"""
    project = await _load_project(session, project_id, user)
    if payload.name is not None:
        project.name = payload.name.strip()
    if payload.idea is not None:
        project.idea = payload.idea.strip()
    if payload.model_profile is not None:
        project.model_profile = payload.model_profile
    return project


@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
async def archive_project(
    project_id: str,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(current_user),
) -> None:
    """归档项目：删除项目及其素材记录，存储清理交给后台任务。"""
    project = await _load_project(session, project_id, user)
    await session.delete(project)


@router.get("/{project_id}/assets")
async def list_project_assets(
    project_id: str,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(current_user),
) -> list[dict]:
    """按分类返回项目资产，下载地址带签名与过期时间。"""
    project = await _load_project(session, project_id, user)
    result = await session.execute(
        select(Asset)
        .where(Asset.project_id == project.id, Asset.state == "adopted")
        .order_by(Asset.category, Asset.created_at.desc())
    )
    grouped: dict[str, list[dict]] = {}
    for asset in result.scalars():
        grouped.setdefault(asset.category, []).append(
            {
                "id": asset.id,
                "name": asset.name,
                "source": asset.source,
                "size_bytes": asset.size_bytes,
                "download_url": f"/api/v1/assets/{asset.id}/download",
                "created_at": asset.created_at,
            }
        )
    return [
        {"key": key, "label": label, "hint": hint, "items": grouped.get(key, [])}
        for key, label, hint in ASSET_CATEGORIES
        if grouped.get(key)
    ]


@router.post("/{project_id}/export")
async def export_project(
    project_id: str,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(current_user),
) -> dict[str, str]:
    """导出成片：把已采用的镜头片段按分镜顺序拼接。"""
    project = await _load_project(session, project_id, user)
    if project.stage not in {"review", "done"}:
        raise HTTPException(status_code=409, detail="当前阶段还不能导出成片")
    project.advance("exporting", 96)
    return {"download_url": f"/api/v1/projects/{project.id}/export/download"}


async def _load_project(session: AsyncSession, project_id: str, user: User) -> Project:
    result = await session.execute(
        select(Project).where(Project.id == project_id, Project.owner_id == user.id)
    )
    project = result.scalar_one_or_none()
    if project is None:
        raise HTTPException(status_code=404, detail="项目不存在或无权访问")
    return project


ASSET_CATEGORIES = [
    ("character", "角色", "人物形象与角色设定图"),
    ("scene", "场景", "环境、地点与氛围图"),
    ("prop", "道具", "剧情相关物品与装备"),
    ("storyboard", "分镜", "镜头画面草图与构图"),
    ("video", "视频片段", "已合成的镜头视频"),
    ("voice", "配音", "旁白与台词音频"),
    ("sfx", "音效", "环境音与转场音效"),
    ("export", "成片导出", "最终合成输出文件"),
]
