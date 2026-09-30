"""剧本解析：把模型输出整理成分场结构与人物表。"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from app.models import Project


@dataclass
class Scene:
    """一场戏。"""

    index: int
    title: str
    location: str
    time_of_day: str
    summary: str
    beats: list[str] = field(default_factory=list)

    @property
    def duration_seconds(self) -> int:
        """按情节节拍数量估算时长，每拍约 6 秒。"""
        return max(6, len(self.beats) * 6)


@dataclass
class Character:
    """出场人物。"""

    name: str
    role: str
    description: str = ""


@dataclass
class ScriptDraft:
    """剧本初稿。"""

    logline: str
    genre: str
    scenes: list[Scene]
    characters: list[Character]

    @classmethod
    def parse(cls, raw: str) -> "ScriptDraft":
        """把模型返回的文本解析成结构化剧本。"""
        lines = [line.strip() for line in raw.splitlines() if line.strip()]
        logline = lines[0] if lines else "未命名故事"
        genre = cls._detect_genre(raw)
        scenes = cls._parse_scenes(lines)
        characters = cls._parse_characters(lines)
        return cls(logline=logline, genre=genre, scenes=scenes, characters=characters)

    @staticmethod
    def _detect_genre(raw: str) -> str:
        for genre in ("剧情", "纪录", "广告", "科普", "喜剧", "悬疑"):
            if genre in raw:
                return genre
        return "剧情"

    @staticmethod
    def _parse_scenes(lines: list[str]) -> list[Scene]:
        scenes: list[Scene] = []
        pattern = re.compile(r"^(?:场景|第)\s*(\d+)?\s*[：:、.]?\s*(.*)$")
        for line in lines:
            match = pattern.match(line)
            if not match:
                continue
            index = len(scenes) + 1
            title = match.group(2).strip() or f"场景 {index}"
            scenes.append(
                Scene(
                    index=index,
                    title=title,
                    location=ScriptDraft._pick(line, ("室内", "室外", "街道", "室内外")),
                    time_of_day=ScriptDraft._pick(line, ("白天", "夜晚", "清晨", "黄昏")),
                    summary=line,
                    beats=[title],
                )
            )
        if not scenes:
            scenes.append(Scene(index=1, title="主场景", location="未指定", time_of_day="白天", summary=lines[0] if lines else ""))
        return scenes

    @staticmethod
    def _parse_characters(lines: list[str]) -> list[Character]:
        characters: list[Character] = []
        for line in lines:
            if "：" not in line or "人物" not in line:
                continue
            _, _, rest = line.partition("：")
            for item in re.split(r"[、,，]", rest):
                name = item.strip()
                if name and name not in [character.name for character in characters]:
                    characters.append(Character(name=name, role="主要角色"))
        return characters

    @staticmethod
    def _pick(line: str, options: tuple[str, ...]) -> str:
        for option in options:
            if option in line:
                return option
        return "未指定"

    @property
    def total_duration(self) -> int:
        return sum(scene.duration_seconds for scene in self.scenes)


def estimate_project_duration(project: Project, script: ScriptDraft | None) -> int:
    """估算成片时长：优先用剧本估算，没有剧本时按创意描述长度粗略推算。"""
    if script is not None and script.scenes:
        return script.total_duration
    return max(15, min(180, len(project.idea) // 2))
