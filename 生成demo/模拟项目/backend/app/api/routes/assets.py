"""素材接口：全局素材库、下载、缩略图、复用与删除。"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import current_user
from app.core.database import get_session
from app.models import Asset, Project, User
from app.services.storage import asset_path, signed_url

router = APIRouter()

# 全局素材库的分类顺序，前端按同一顺序展示
CATEGORY_LABELS = {
    "character": ("角色", "人物形象与角色设定图"),
    "scene": ("场景", "环境、地点与氛围图"),
    "prop": ("道具", "剧情相关物品与装备"),
    "storyboard": ("分镜", "镜头画面草图与构图"),
    "video": ("视频片段", "已合成的镜头视频"),
    "voice": ("配音", "旁白与台词音频"),
    "sfx": ("音效", "环境音与转场音效"),
    "export": ("成片导出", "最终合成输出文件"),
}


@router.get("/assets")
async def list_global_assets(
    keyword: str = Query(default="", max_length=80),
    session: AsyncSession = Depends(get_session),
    user: User = Depends(current_user),
) -> list[dict]:
    """全局素材库：汇总当前账号所有项目里已采用的素材。"""
    result = await session.execute(
        select(Asset, Project.name)
        .join(Project, Project.id == Asset.project_id)
        .where(Project.owner_id == user.id, Asset.state == "adopted")
        .order_by(Asset.created_at.desc())
    )
    grouped: dict[str, list[dict]] = {}
    for asset, project_name in result.all():
        if keyword and keyword.lower() not in asset.name.lower():
            continue
        grouped.setdefault(asset.category, []).append(
            {
                "id": asset.id,
                "name": asset.name,
                "source": project_name,
                "size_bytes": asset.size_bytes,
                "download_url": signed_url(asset.id),
                "created_at": asset.created_at,
            }
        )
    return [
        {
            "key": key,
            "label": CATEGORY_LABELS[key][0],
            "hint": CATEGORY_LABELS[key][1],
            "items": items,
        }
        for key, items in grouped.items()
    ]


@router.get("/assets/{asset_id}/download")
async def download_asset(
    asset_id: str,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(current_user),
) -> FileResponse:
    """下载素材原文件。"""
    asset = await _load_asset(session, asset_id, user)
    path = asset_path(asset)
    if not path.is_file():
        raise HTTPException(status_code=410, detail="素材文件已被清理")
    return FileResponse(path, media_type=asset.mime_type, filename=asset.name)


@router.get("/assets/{asset_id}/thumbnail")
async def asset_thumbnail(
    asset_id: str,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(current_user),
) -> FileResponse:
    """返回缩略图；没有缩略图时退回原文件。"""
    asset = await _load_asset(session, asset_id, user)
    thumb = asset_path(asset, variant="thumb")
    return FileResponse(thumb if thumb.is_file() else asset_path(asset))


@router.post("/assets/{asset_id}/reuse", status_code=status.HTTP_201_CREATED)
async def reuse_asset(
    asset_id: str,
    target_project_id: str,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(current_user),
) -> dict[str, str]:
    """把全局素材库里的素材复制到另一个项目。"""
    asset = await _load_asset(session, asset_id, user)
    target = await _load_project(session, target_project_id, user)
    copy = Asset(
        project_id=target.id,
        category=asset.category,
        name=asset.name,
        storage_key=asset.storage_key,
        mime_type=asset.mime_type,
        size_bytes=asset.size_bytes,
        source="reused",
        state="adopted",
        adopted=True,
    )
    session.add(copy)
    await session.flush()
    return {"id": copy.id, "project_id": target.id}


@router.delete("/assets/{asset_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_asset(
    asset_id: str,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(current_user),
) -> None:
    """删除素材记录；文件由后台清理任务按引用计数回收。"""
    asset = await _load_asset(session, asset_id, user)
    await session.delete(asset)


async def _load_asset(session: AsyncSession, asset_id: str, user: User) -> Asset:
    result = await session.execute(
        select(Asset).join(Project).where(Asset.id == asset_id, Project.owner_id == user.id)
    )
    asset = result.scalar_one_or_none()
    if asset is None:
        raise HTTPException(status_code=404, detail="素材不存在或无权访问")
    return asset


async def _load_project(session: AsyncSession, project_id: str, user: User) -> Project:
    result = await session.execute(
        select(Project).where(Project.id == project_id, Project.owner_id == user.id)
    )
    project = result.scalar_one_or_none()
    if project is None:
        raise HTTPException(status_code=404, detail="项目不存在或无权访问")
    return project
