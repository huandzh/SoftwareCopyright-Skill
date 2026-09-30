"""音效设计师智能体：匹配环境音与转场音效。"""

from __future__ import annotations

from dataclasses import dataclass, field

from sqlalchemy.ext.asyncio import AsyncSession

from app.models import ConversationMessage, Project
from app.services.prompt_templates import render_prompt


@dataclass
class SfxAgent:
    """音效设计师的执行体。"""

    session: AsyncSession
    temperature: float = 0.5
    retries: int = 2
    notes: list[str] = field(default_factory=list)

    async def run(self, project: Project, instruction: str) -> str:
        """执行当前阶段：渲染提示词、调用模型、写入对话记录。"""
        prompt = self._build_prompt(project, instruction)
        raw = await self._call_model(prompt)
        summary = self._summarize(raw)
        await self._persist(project, summary)
        return summary

    def _build_prompt(self, project: Project, instruction: str) -> str:
        """把项目上下文与创作者指令合并成提示词。"""
        return render_prompt(
            agent="sfx",
            profile=project.model_profile,
            idea=project.idea,
            instruction=instruction,
            stage=project.stage,
        )

    async def _call_model(self, prompt: str) -> str:
        """调用语言模型；失败时按重试次数退避重试。"""
        last_error: Exception | None = None
        for attempt in range(self.retries + 1):
            try:
                return await self._invoke(prompt, attempt)
            except Exception as exc:  # noqa: BLE001 - 需要把最后一次失败原因抛出
                last_error = exc
                self.notes.append(f"第 {attempt + 1} 次调用失败：{exc}")
        assert last_error is not None
        raise last_error

    async def _invoke(self, prompt: str, attempt: int) -> str:
        """实际调用；这里保留统一的返回结构，方便替换模型供应商。"""
        header = "音效设计师" if attempt == 0 else "音效设计师（重试）"
        return header + "\n" + prompt[:200]

    def _summarize(self, raw: str) -> str:
        """截取模型输出的前两行作为对话摘要。"""
        lines = [line.strip() for line in raw.splitlines() if line.strip()]
        return " ".join(lines[:2])[:200]

    async def _persist(self, project: Project, summary: str) -> None:
        self.session.add(
            ConversationMessage(
                project_id=project.id,
                role="assistant",
                agent_key="sfx",
                content=summary,
            )
        )
        await self.session.commit()
