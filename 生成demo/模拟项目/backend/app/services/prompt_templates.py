"""提示词模板：按智能体与模型档位拼装提示词。"""

from __future__ import annotations

from string import Template

BASE_SYSTEM = Template(
    """你是 $agent_name，负责 $agent_duty
当前项目阶段：$stage
模型档位：$profile
要求：输出中文，结论先行，不要重复创作者已经说过的内容。"""
)


AGENT_DUTIES = {
    "script": ("剧本分析师", "拆解创意描述，输出题材、节奏与关键情节。"),
    "storyboard": ("分镜规划师", "把剧本拆成镜头列表，标注景别与时长。"),
    "visual": ("视觉素材生成师", "生成角色、场景与道具候选图。"),
    "video": ("视频合成师", "合成镜头片段并校验衔接。"),
    "voice": ("配音师", "生成旁白与台词配音。"),
    "sfx": ("音效设计师", "匹配环境音与转场音效。"),
}


PROFILE_HINTS = {
    "fast": "优先给出可直接执行的最小方案，减少润色。",
    "balanced": "在质量与耗时之间取平衡，补充必要细节。",
    "quality": "给出完整方案，包含备选思路与风险提示。",
}


STAGE_REQUIREMENTS = {
    "draft": "先确认题材、时长与风格，不要直接生成分镜。",
    "scripting": "输出分场大纲、人物关系和关键情节。",
    "storyboarding": "输出镜头列表，每个镜头给出景别、时长与画面提示。",
    "visualizing": "为每个镜头给出画面提示词，避免出现真实人物姓名。",
    "composing": "说明镜头衔接方式和转场选择理由。",
    "dubbing": "给出旁白与台词的语速、停顿和情绪要求。",
    "review": "汇总待确认项，逐条给出建议。",
    "exporting": "检查分辨率、帧率与字幕，给出导出前清单。",
}


def render_prompt(
    *,
    agent: str,
    profile: str,
    idea: str,
    instruction: str,
    stage: str,
) -> str:
    """渲染最终提示词：系统约束 + 项目背景 + 创作者指令。"""
    name, duty = AGENT_DUTIES.get(agent, ("制片助理", "协助推进视频制作流程。"))
    system = BASE_SYSTEM.substitute(
        agent_name=name,
        agent_duty=duty,
        stage=stage,
        profile=profile,
    )
    parts = [
        system,
        PROFILE_HINTS.get(profile, PROFILE_HINTS["balanced"]),
        STAGE_REQUIREMENTS.get(stage, "按当前项目状态给出下一步建议。"),
        "项目创意：" + idea.strip(),
        "创作者指令：" + instruction.strip(),
    ]
    return "\n".join(part for part in parts if part)
