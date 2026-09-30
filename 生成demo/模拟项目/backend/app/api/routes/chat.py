"""制片对话接口：发送指令、SSE 流式回复、任务中断。"""

from __future__ import annotations

import asyncio
import json
from collections.abc import AsyncIterator

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import current_user
from app.core.database import get_session, session_scope
from app.models import ConversationMessage, Project, User
from app.schemas import ChatMessageIn, ChatMessageOut
from app.services.agent_orchestrator import Orchestrator

router = APIRouter()

# 中断标记放在进程内存中，单实例部署够用；多实例会改用 Redis
_CANCELLED: set[str] = set()


@router.get("/{project_id}/chat/messages", response_model=list[ChatMessageOut])
async def list_messages(
    project_id: str,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(current_user),
) -> list[ConversationMessage]:
    """按时间顺序返回项目的历史对话。"""
    project = await _load_project(session, project_id, user)
    result = await session.execute(
        select(ConversationMessage)
        .where(ConversationMessage.project_id == project.id)
        .order_by(ConversationMessage.created_at)
    )
    return list(result.scalars())


@router.post("/{project_id}/chat/messages", response_model=ChatMessageOut, status_code=202)
async def send_message(
    project_id: str,
    payload: ChatMessageIn,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(current_user),
) -> ConversationMessage:
    """保存创作者指令并唤醒编排器；真正的回复通过 SSE 推送。"""
    project = await _load_project(session, project_id, user)
    message = ConversationMessage(
        project_id=project.id,
        role="user",
        content=payload.content.strip(),
    )
    session.add(message)
    await session.flush()

    orchestrator = Orchestrator(session)
    asyncio.create_task(orchestrator.dispatch(project, message.content))
    return message


@router.get("/{project_id}/chat/stream")
async def chat_stream(
    project_id: str,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(current_user),
) -> StreamingResponse:
    """SSE 流：推送对话消息、增量文本与智能体状态。"""
    project = await _load_project(session, project_id, user)

    async def event_source() -> AsyncIterator[str]:
        orchestrator = Orchestrator(session)
        try:
            async for event in orchestrator.stream(project):
                if project_id in _CANCELLED:
                    _CANCELLED.discard(project_id)
                    yield _format_event("done", {"reason": "cancelled"})
                    break
                yield _format_event(event.name, event.payload)
        except asyncio.CancelledError:
            # 客户端断开时直接结束，不写错误日志
            raise
        finally:
            yield _format_event("done", {})

    return StreamingResponse(
        event_source(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.post("/{project_id}/tasks/{task_id}/cancel", status_code=202)
async def cancel_task(
    project_id: str,
    task_id: str,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(current_user),
) -> dict[str, str]:
    """中断当前生成任务：编排器会在下一个检查点退出。"""
    project = await _load_project(session, project_id, user)
    _CANCELLED.add(project.id)
    return {"task_id": task_id, "status": "cancelling"}


@router.get("/{project_id}/candidates")
async def list_candidates(
    project_id: str,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(current_user),
) -> list[dict]:
    """返回待确认的候选素材。"""
    project = await _load_project(session, project_id, user)
    from app.models import Asset

    result = await session.execute(
        select(Asset).where(Asset.project_id == project.id, Asset.state == "candidate")
    )
    return [
        {
            "id": asset.id,
            "name": asset.name,
            "kind": _kind_of(asset.category),
            "score": asset.score,
            "prompt_hint": asset.prompt_hint,
            "thumbnail_url": f"/api/v1/assets/{asset.id}/thumbnail",
            "created_at": asset.created_at,
        }
        for asset in result.scalars()
    ]


@router.post("/{project_id}/candidates/{candidate_id}/pick", status_code=204)
async def pick_candidate(
    project_id: str,
    candidate_id: str,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(current_user),
) -> None:
    """采用候选素材：同批次其它候选自动失效。"""
    await _set_candidate(session, project_id, candidate_id, user, adopt=True)


@router.post("/{project_id}/candidates/{candidate_id}/revoke", status_code=204)
async def revoke_candidate(
    project_id: str,
    candidate_id: str,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(current_user),
) -> None:
    """撤回候选素材。"""
    await _set_candidate(session, project_id, candidate_id, user, adopt=False)


async def _set_candidate(
    session: AsyncSession,
    project_id: str,
    candidate_id: str,
    user: User,
    *,
    adopt: bool,
) -> None:
    from app.models import Asset

    project = await _load_project(session, project_id, user)
    result = await session.execute(
        select(Asset).where(Asset.id == candidate_id, Asset.project_id == project.id)
    )
    asset = result.scalar_one_or_none()
    if asset is None:
        raise HTTPException(status_code=404, detail="候选素材不存在")
    if adopt:
        asset.adopt()
    else:
        asset.revoke()


def _kind_of(category: str) -> str:
    if category in {"character", "scene", "prop", "storyboard"}:
        return "image"
    if category == "video":
        return "video"
    return "audio"


def _format_event(name: str, payload: dict) -> str:
    return f"event: {name}\ndata: {json.dumps(payload, ensure_ascii=False)}\n\n"


async def _load_project(session: AsyncSession, project_id: str, user: User) -> Project:
    result = await session.execute(
        select(Project).where(Project.id == project_id, Project.owner_id == user.id)
    )
    project = result.scalar_one_or_none()
    if project is None:
        raise HTTPException(status_code=404, detail="项目不存在或无权访问")
    return project
