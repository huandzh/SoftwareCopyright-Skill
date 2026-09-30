"""请求与响应模型。"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class ProjectCreate(BaseModel):
    """新建项目请求。"""

    name: str = Field(min_length=1, max_length=120)
    idea: str = Field(min_length=4, max_length=4000)
    model_profile: str = Field(default="balanced", pattern="^(fast|balanced|quality)$")


class ProjectUpdate(BaseModel):
    """更新项目请求，只允许修改名称、创意描述与模型档位。"""

    name: str | None = Field(default=None, min_length=1, max_length=120)
    idea: str | None = Field(default=None, min_length=4, max_length=4000)
    model_profile: str | None = Field(default=None, pattern="^(fast|balanced|quality)$")


class AgentStatusOut(BaseModel):
    key: str
    name: str
    duty: str
    state: str
    current_task: str | None = None
    last_summary: str | None = None
    last_error: str | None = None


class ProjectCostOut(BaseModel):
    total: float
    estimated_remaining: float
    items: dict[str, float]


class ProjectOut(BaseModel):
    id: str
    name: str
    idea: str
    stage: str
    progress: int
    duration_seconds: int
    shot_count: int
    updated_at: datetime
    last_error: str | None = None


class ProjectDetailOut(ProjectOut):
    agents: list[AgentStatusOut]
    cost: ProjectCostOut | None = None
    created_at: datetime
    model_profile: str


class AssetOut(BaseModel):
    id: str
    name: str
    source: str
    size_bytes: int
    download_url: str
    created_at: datetime


class AssetCategoryOut(BaseModel):
    key: str
    label: str
    hint: str
    items: list[AssetOut]


class CandidateOut(BaseModel):
    id: str
    name: str
    kind: str
    score: float
    prompt_hint: str
    thumbnail_url: str
    created_at: datetime


class ChatMessageIn(BaseModel):
    content: str = Field(min_length=1, max_length=2000)


class ChatMessageOut(BaseModel):
    id: str
    role: str
    content: str
    created_at: datetime
    agent_key: str | None = None
    agent_name: str | None = None


class BillingItemOut(BaseModel):
    key: str
    quantity: float
    unit: str
    amount: float


class BillingSummaryOut(BaseModel):
    period: str
    total: float
    budget: float
    items: list[BillingItemOut]


class LoginIn(BaseModel):
    email: str = Field(min_length=5, max_length=255)
    password: str = Field(min_length=8, max_length=128)


class RegisterIn(LoginIn):
    display_name: str = Field(min_length=1, max_length=64)
