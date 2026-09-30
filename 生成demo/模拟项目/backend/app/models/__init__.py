"""数据模型：项目、资产、对话与账号。"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


def new_id() -> str:
    return uuid.uuid4().hex


class Base(DeclarativeBase):
    """所有模型的公共基类。"""


class TimestampMixin:
    """统一创建与更新时间，避免每个模型重复声明。"""

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class User(Base, TimestampMixin):
    """账号：当前只支持邮箱口令登录。"""

    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    display_name: Mapped[str] = mapped_column(String(64))
    password_salt: Mapped[str] = mapped_column(String(32))
    password_hash: Mapped[str] = mapped_column(String(128))
    monthly_budget: Mapped[float] = mapped_column(Float, default=200.0)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    projects: Mapped[list["Project"]] = relationship(back_populates="owner", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<User {self.email}>"


class Project(Base, TimestampMixin):
    """视频项目：一次从创意到成片的完整制作过程。"""

    __tablename__ = "projects"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    owner_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(120))
    idea: Mapped[str] = mapped_column(Text)
    stage: Mapped[str] = mapped_column(String(24), default="draft")
    progress: Mapped[int] = mapped_column(Integer, default=0)
    duration_seconds: Mapped[int] = mapped_column(Integer, default=0)
    shot_count: Mapped[int] = mapped_column(Integer, default=0)
    model_profile: Mapped[str] = mapped_column(String(24), default="balanced")
    cost_total: Mapped[float] = mapped_column(Float, default=0.0)
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)

    owner: Mapped[User] = relationship(back_populates="projects")
    assets: Mapped[list["Asset"]] = relationship(back_populates="project", cascade="all, delete-orphan")
    messages: Mapped[list["ConversationMessage"]] = relationship(
        back_populates="project", cascade="all, delete-orphan"
    )

    @property
    def is_finished(self) -> bool:
        return self.stage in {"done", "failed"}

    def advance(self, stage: str, progress: int) -> None:
        """推进阶段；已完成的阶段不会被回退，除非显式重跑。"""
        self.stage = stage
        self.progress = max(0, min(100, progress))


class Asset(Base, TimestampMixin):
    """素材：候选图、镜头片段、配音、音效与成片导出。"""

    __tablename__ = "assets"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), index=True)
    category: Mapped[str] = mapped_column(String(24), index=True)
    name: Mapped[str] = mapped_column(String(160))
    storage_key: Mapped[str] = mapped_column(String(255))
    mime_type: Mapped[str] = mapped_column(String(64), default="application/octet-stream")
    size_bytes: Mapped[int] = mapped_column(Integer, default=0)
    source: Mapped[str] = mapped_column(String(32), default="generated")
    state: Mapped[str] = mapped_column(String(16), default="candidate")
    score: Mapped[float] = mapped_column(Float, default=0.0)
    prompt_hint: Mapped[str] = mapped_column(Text, default="")
    adopted: Mapped[bool] = mapped_column(Boolean, default=False)

    project: Mapped[Project] = relationship(back_populates="assets")

    def adopt(self) -> None:
        """采用该素材：同批次的其它候选会被标记为未采用。"""
        self.state = "adopted"
        self.adopted = True

    def revoke(self) -> None:
        """撤回候选：素材保留在存储中，但不进入项目资产列表。"""
        self.state = "revoked"
        self.adopted = False


class ConversationMessage(Base, TimestampMixin):
    """制片对话消息：创作者指令与智能体回复。"""

    __tablename__ = "conversation_messages"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), index=True)
    role: Mapped[str] = mapped_column(String(16))
    agent_key: Mapped[str | None] = mapped_column(String(24), nullable=True)
    content: Mapped[str] = mapped_column(Text)

    project: Mapped[Project] = relationship(back_populates="messages")
