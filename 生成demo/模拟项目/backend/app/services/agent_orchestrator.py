"""智能体编排：按项目阶段依次唤醒六个制片角色。"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.models import ConversationMessage, Project
from app.services.cost_service import record_usage
from app.services.image_generation import ImageService
from app.services.tts_service import TTSService
from app.services.video_pipeline import VideoPipeline


@dataclass
class StreamEvent:
    """推送给前端的 SSE 事件。"""

    name: str
    payload: dict[str, Any]


AGENTS: list[dict[str, str]] = [
    {"key": "script", "name": "剧本分析师", "duty": "分析创意描述，输出题材、节奏、人物关系与关键情节。"},
    {"key": "storyboard", "name": "分镜规划师", "duty": "把剧本拆成镜头列表，给出景别、时长与画面提示词。"},
    {"key": "visual", "name": "视觉素材生成师", "duty": "按分镜生成角色、场景与道具候选图，并给出候选评分。"},
    {"key": "video", "name": "视频合成师", "duty": "把采用的候选图合成镜头片段，校验时长与转场衔接。"},
    {"key": "voice", "name": "配音师", "duty": "生成旁白与角色台词配音，按镜头时长调整语速。"},
    {"key": "sfx", "name": "音效设计师", "duty": "按场景挑选环境音与转场音效，并补齐缺失片段。"},
]

# 阶段与负责的智能体对应关系，编排器据此决定下一个接话的角色
STAGE_AGENT: dict[str, str] = {
    "draft": "script",
    "scripting": "script",
    "storyboarding": "storyboard",
    "visualizing": "visual",
    "composing": "video",
    "dubbing": "voice",
    "review": "sfx",
    "exporting": "video",
}


def agent_statuses(project: Project) -> list[dict[str, str | None]]:
    """根据项目阶段推导六个智能体的展示状态。"""
    active = STAGE_AGENT.get(project.stage, "script")
    statuses: list[dict[str, str | None]] = []
    for agent in AGENTS:
        if project.stage == "failed" and agent["key"] == active:
            state = "failed"
        elif agent["key"] == active:
            state = "working" if project.stage not in {"review", "done"} else "waiting_user"
        else:
            state = "done" if project.stage in {"review", "exporting", "done"} else "idle"
        statuses.append(
            {
                "key": agent["key"],
                "name": agent["name"],
                "duty": agent["duty"],
                "state": state,
                "current_task": None,
                "last_summary": None,
                "last_error": project.last_error if state == "failed" else None,
            }
        )
    return statuses


class Orchestrator:
    """把创作者指令分派给当前阶段的智能体，并流式回传结果。"""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.images = ImageService(session)
        self.tts = TTSService(session)
        self.pipeline = VideoPipeline(session)

    async def dispatch(self, project: Project, instruction: str) -> None:
        """保存指令并推进阶段；异常时记录失败原因。"""
        agent_key = STAGE_AGENT.get(project.stage, "script")
        try:
            await self._run_agent(project, agent_key, instruction)
        except Exception as exc:  # noqa: BLE001 - 失败原因需要原样呈现给创作者
            project.advance("failed", project.progress)
            project.last_error = str(exc)
            await self.session.commit()

    async def stream(self, project: Project):
        """按顺序产出对话与状态事件，前端据此更新界面。"""
        agent_key = STAGE_AGENT.get(project.stage, "script")
        agent = next(item for item in AGENTS if item["key"] == agent_key)
        yield StreamEvent("agent", {"agentKey": agent_key, "state": "working"})
        yield StreamEvent(
            "message",
            {
                "id": f"{project.id}-{agent_key}",
                "role": "assistant",
                "agentKey": agent_key,
                "agentName": agent["name"],
                "content": f"{agent['name']}已接手，正在处理：{project.idea[:60]}",
            },
        )
        # 生成过程较慢，按固定间隔发送心跳，避免网关断开长连接
        for _ in range(3):
            await asyncio.sleep(0.5)
            yield StreamEvent("agent", {"agentKey": agent_key, "state": "working"})
        yield StreamEvent("agent", {"agentKey": agent_key, "state": "done"})

    async def _run_agent(self, project: Project, agent_key: str, instruction: str) -> None:
        handler = {
            "script": self._run_script,
            "storyboard": self._run_storyboard,
            "visual": self._run_visual,
            "video": self._run_video,
            "voice": self._run_voice,
            "sfx": self._run_sfx,
        }[agent_key]
        await handler(project, instruction)

    async def _run_script(self, project: Project, instruction: str) -> None:
        """剧本分析师：分析创意描述，输出题材、节奏、人物关系与关键情节。"""
        agent = next(item for item in AGENTS if item["key"] == "script")
        prompt = build_script_prompt(project.idea, profile)
        result = await self.llm.complete(prompt, temperature=0.6)
        script = ScriptDraft.parse(result)
        await self._persist_message(project, agent.key, script.summary)
        await record_usage(self.session, project, "script", amount=1)
        await self._persist_message(project, agent["key"], "剧本分析师已完成")

    async def _run_storyboard(self, project: Project, instruction: str) -> None:
        """分镜规划师：把剧本拆成镜头列表，给出景别、时长与画面提示词。"""
        agent = next(item for item in AGENTS if item["key"] == "storyboard")
        prompt = build_storyboard_prompt(project.script, profile)
        result = await self.llm.complete(prompt, temperature=0.4)
        shots = ShotPlan.parse_many(result)
        await self._persist_shots(project, shots)
        await record_usage(self.session, project, "storyboard", amount=1)
        await self._persist_message(project, agent["key"], "分镜规划师已完成")

    async def _run_visual(self, project: Project, instruction: str) -> None:
        """视觉素材生成师：按分镜生成角色、场景与道具候选图，并给出候选评分。"""
        agent = next(item for item in AGENTS if item["key"] == "visual")
        for shot in pending_shots:
            request = ImageRequest.from_shot(shot, profile)
            candidates = await self.images.generate(request, count=4)
            await self._persist_candidates(project, shot, candidates)
        await record_usage(self.session, project, "visual", amount=1)
        await self._persist_message(project, agent["key"], "视觉素材生成师已完成")

    async def _run_video(self, project: Project, instruction: str) -> None:
        """视频合成师：把采用的候选图合成镜头片段，校验时长与转场衔接。"""
        agent = next(item for item in AGENTS if item["key"] == "video")
        for shot in ready_shots:
            clip = await self.pipeline.compose(shot, options)
            await self._persist_clip(project, shot, clip)
        await record_usage(self.session, project, "video", amount=1)
        await self._persist_message(project, agent["key"], "视频合成师已完成")

    async def _run_voice(self, project: Project, instruction: str) -> None:
        """配音师：生成旁白与角色台词配音，按镜头时长调整语速。"""
        agent = next(item for item in AGENTS if item["key"] == "voice")
        lines = collect_dialogue(project.script, adopted_shots)
        for line in lines:
            audio = await self.tts.synthesize(line, voice_profile)
            await self._persist_audio(project, line, audio)
        await record_usage(self.session, project, "voice", amount=1)
        await self._persist_message(project, agent["key"], "配音师已完成")

    async def _run_sfx(self, project: Project, instruction: str) -> None:
        """音效设计师：按场景挑选环境音与转场音效，并补齐缺失片段。"""
        agent = next(item for item in AGENTS if item["key"] == "sfx")
        plan = build_sfx_plan(project.shots)
        for slot in plan.slots:
            track = await self.sfx.search(slot.keywords, duration=slot.duration)
            await self._persist_sfx(project, slot, track)
        await record_usage(self.session, project, "sfx", amount=1)
        await self._persist_message(project, agent["key"], "音效设计师已完成")

    async def _persist_message(self, project: Project, agent_key: str, content: str) -> None:
        """把智能体输出写入对话记录，前端刷新后仍能看到过程。"""
        self.session.add(
            ConversationMessage(
                project_id=project.id,
                role="assistant",
                agent_key=agent_key,
                content=content,
            )
        )
        await self.session.commit()

    async def _persist_shots(self, project: Project, shots: list) -> None:
        """保存分镜列表并更新镜头数量。"""
        project.shot_count = len(shots)
        project.advance("visualizing", 35)
        await self.session.commit()

    async def _persist_candidates(self, project: Project, shot, candidates: list) -> None:
        """把生成的候选素材写入资产表，等待创作者确认。"""
        for asset in candidates:
            asset.project_id = project.id
            self.session.add(asset)
        project.advance("review", 60)
        await self.session.commit()

    async def _persist_clip(self, project: Project, shot, clip) -> None:
        clip.project_id = project.id
        self.session.add(clip)
        await self.session.commit()

    async def _persist_audio(self, project: Project, line, audio) -> None:
        audio.project_id = project.id
        self.session.add(audio)
        await self.session.commit()

    async def _persist_sfx(self, project: Project, slot, track) -> None:
        track.project_id = project.id
        self.session.add(track)
        project.advance("review", 88)
        await self.session.commit()
