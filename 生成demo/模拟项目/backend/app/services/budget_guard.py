"""预算守卫：在生成前预估成本并拦截超额任务。"""

from __future__ import annotations

from dataclasses import dataclass

from app.core.config import settings
from app.models import Asset, Project, User

# 各档位的单镜头预估成本
PROFILE_COST = {
    "fast": 0.18,
    "balanced": 0.42,
    "quality": 0.86,
}


@dataclass
class BudgetDecision:
    """预算判断结果。"""

    allowed: bool
    estimated_cost: float
    reason: str = ""


def estimate_stage_cost(project: Project, shot_count: int) -> float:
    """按镜头数量与模型档位预估本阶段成本。"""
    unit = PROFILE_COST.get(project.model_profile, PROFILE_COST["balanced"])
    stage_factor = {
        "draft": 0.2,
        "scripting": 0.5,
        "storyboarding": 0.8,
        "visualizing": 1.0,
        "composing": 1.4,
        "dubbing": 0.7,
        "review": 0.2,
        "exporting": 0.3,
    }.get(project.stage, 1.0)
    return round(unit * max(1, shot_count) * stage_factor, 2)


def check_budget(user: User, project: Project, estimated: float) -> BudgetDecision:
    """判断剩余预算是否足够；不足时给出原因，供前端展示。"""
    remaining = (user.monthly_budget or settings.monthly_budget) - project.cost_total
    if estimated <= 0:
        return BudgetDecision(allowed=True, estimated_cost=0.0, reason="无需计费")
    if remaining <= 0:
        return BudgetDecision(allowed=False, estimated_cost=estimated, reason="本月预算已用完")
    if estimated > remaining:
        return BudgetDecision(
            allowed=False,
            estimated_cost=estimated,
            reason=f"预计花费 {estimated:.2f} 元，剩余预算只有 {remaining:.2f} 元",
        )
    return BudgetDecision(allowed=True, estimated_cost=estimated, reason="")


def assets_size(assets: list[Asset]) -> int:
    """统计素材总大小，用于存储计费。"""
    return sum(int(asset.size_bytes or 0) for asset in assets)
