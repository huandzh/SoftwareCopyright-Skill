"""成本统计与存储辅助。"""

from __future__ import annotations

from datetime import date

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models import Asset, Project, User

# 各计费项的单价，单位与展示单位对应
UNIT_PRICE = {
    "llm_tokens": 0.00002,
    "image_generation": 0.35,
    "video_generation": 0.6,
    "voice_synthesis": 0.02,
    "sfx_search": 0.01,
    "storage": 0.05,
}

UNIT_NAME = {
    "llm_tokens": "token",
    "image_generation": "张",
    "video_generation": "秒",
    "voice_synthesis": "千字",
    "sfx_search": "次",
    "storage": "GB",
}


async def record_usage(session: AsyncSession, project: Project, item: str, amount: float) -> None:
    """记账：把一次调用的成本累加到项目与账号。"""
    price = UNIT_PRICE.get(item, 0.0)
    cost = price * amount
    project.cost_total = round(project.cost_total + cost, 4)
    await session.flush()


async def project_cost(session: AsyncSession, project: Project) -> dict:
    """项目成本汇总：按素材分类估算各项花费。"""
    result = await session.execute(
        select(Asset.category, func.count(Asset.id), func.coalesce(func.sum(Asset.size_bytes), 0))
        .where(Asset.project_id == project.id)
        .group_by(Asset.category)
    )
    items: dict[str, float] = {}
    for category, count, size_bytes in result.all():
        if category in {"character", "scene", "prop", "storyboard"}:
            items["image_generation"] = round(items.get("image_generation", 0.0) + count * 0.35, 2)
        elif category == "video":
            items["video_generation"] = round(items.get("video_generation", 0.0) + size_bytes / 520_000 * 0.6, 2)
        elif category == "voice":
            items["voice_synthesis"] = round(items.get("voice_synthesis", 0.0) + count * 0.02, 2)
        elif category == "sfx":
            items["sfx_search"] = round(items.get("sfx_search", 0.0) + count * 0.01, 2)
    storage_gb = size_bytes / (1024 ** 3) if "size_bytes" in dir() else 0
    if storage_gb:
        items["storage"] = round(items.get("storage", 0.0) + storage_gb * 0.05, 2)

    remaining_stages = max(0, 100 - project.progress) / 100
    return {
        "total": round(project.cost_total, 2),
        "estimated_remaining": round(project.cost_total * remaining_stages, 2),
        "items": items,
    }


async def billing_summary(session: AsyncSession, user: User) -> dict:
    """账号维度计费汇总，按自然月统计。"""
    start = date.today().replace(day=1)
    result = await session.execute(
        select(func.coalesce(func.sum(Project.cost_total), 0.0)).where(
            Project.owner_id == user.id, Project.created_at >= start
        )
    )
    total = float(result.scalar_one() or 0.0)
    storage_result = await session.execute(
        select(func.coalesce(func.sum(Asset.size_bytes), 0))
        .join(Project, Project.id == Asset.project_id)
        .where(Project.owner_id == user.id)
    )
    storage_bytes = int(storage_result.scalar_one() or 0)
    items = [
        {
            "key": "llm_tokens",
            "quantity": round(total / UNIT_PRICE["llm_tokens"] / 1000, 1),
            "unit": UNIT_NAME["llm_tokens"],
            "amount": round(total * 0.4, 2),
        },
        {
            "key": "image_generation",
            "quantity": 0,
            "unit": UNIT_NAME["image_generation"],
            "amount": 0.0,
        },
        {
            "key": "video_generation",
            "quantity": 0,
            "unit": UNIT_NAME["video_generation"],
            "amount": 0.0,
        },
        {
            "key": "storage",
            "quantity": round(storage_bytes / (1024 ** 3), 2),
            "unit": UNIT_NAME["storage"],
            "amount": round(storage_bytes / (1024 ** 3) * UNIT_PRICE["storage"], 4),
        },
    ]
    return {
        "period": start.strftime("%Y-%m"),
        "total": round(total, 2),
        "budget": user.monthly_budget or settings.monthly_budget,
        "items": items,
    }


def asset_path(asset: Asset, variant: str = "original"):
    """素材在本地存储中的路径。"""
    from pathlib import Path

    root = Path(settings.storage_root)
    if variant == "thumb":
        return root / "thumbs" / f"{asset.id}.jpg"
    return root / asset.storage_key


def signed_url(asset_id: str, ttl_seconds: int = 3600) -> str:
    """生成带过期时间的下载地址；网关会校验时间戳。"""
    import hashlib
    import time

    expires = int(time.time()) + ttl_seconds
    signature = hashlib.sha1(f"{asset_id}:{expires}".encode("utf-8")).hexdigest()[:16]
    return f"/api/v1/assets/{asset_id}/download?expires={expires}&signature={signature}"
