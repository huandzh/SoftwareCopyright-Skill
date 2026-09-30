"""分镜解析：把镜头列表转成可调度的镜头对象。"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

SHOT_SIZES = ("大远景", "远景", "全景", "中景", "近景", "特写")
CAMERA_MOVES = ("固定", "推镜", "拉镜", "摇镜", "跟拍", "升降")


@dataclass
class Shot:
    """一个镜头。"""

    id: str
    index: int
    size: str
    duration_seconds: int
    camera: str
    prompt: str
    aspect_ratio: str = "16:9"
    notes: list[str] = field(default_factory=list)

    @property
    def key(self) -> str:
        return f"shot-{self.index:02d}"


@dataclass
class ShotPlan:
    """整段分镜。"""

    shots: list[Shot]

    @classmethod
    def parse_many(cls, raw: str) -> list[Shot]:
        """解析模型返回的镜头列表；缺字段时按上下文补默认值。"""
        shots: list[Shot] = []
        for line in raw.splitlines():
            text = line.strip(" -\t")
            if not text or len(text) < 4:
                continue
            if not re.search(r"镜头|画面|景别", text):
                continue
            index = len(shots) + 1
            shots.append(
                Shot(
                    id=f"shot-{index}",
                    index=index,
                    size=cls._match(text, SHOT_SIZES, "中景"),
                    duration_seconds=cls._duration(text),
                    camera=cls._match(text, CAMERA_MOVES, "固定"),
                    prompt=cls._prompt(text),
                )
            )
        return shots

    @staticmethod
    def _match(text: str, options: tuple[str, ...], default: str) -> str:
        for option in options:
            if option in text:
                return option
        return default

    @staticmethod
    def _duration(text: str) -> int:
        match = re.search(r"(\d+(?:\.\d+)?)\s*秒", text)
        if match:
            return max(2, min(20, int(float(match.group(1)))))
        return 5

    @staticmethod
    def _prompt(text: str) -> str:
        for separator in ("：", ":"):
            if separator in text:
                return text.split(separator, 1)[1].strip()[:200]
        return text[:200]

    @property
    def total_duration(self) -> int:
        return sum(shot.duration_seconds for shot in self.shots)

    def pending(self, adopted_keys: set[str]) -> list[Shot]:
        """返回还没有采用素材的镜头。"""
        return [shot for shot in self.shots if shot.key not in adopted_keys]


def collect_dialogue(script, shots: list[Shot]) -> list[dict]:
    """从剧本与分镜里整理出需要配音的台词行。"""
    lines: list[dict] = []
    for scene in getattr(script, "scenes", []) or []:
        for index, beat in enumerate(scene.beats, start=1):
            lines.append(
                {
                    "id": f"line-{scene.index}-{index}",
                    "index": len(lines) + 1,
                    "duration_seconds": max(2, min(12, len(beat) // 3)),
                    "text": beat,
                }
            )
    if not lines:
        lines.append({"id": "line-1-1", "index": 1, "duration_seconds": 6, "text": "旁白占位"})
    return lines


def build_sfx_plan(shots: list[Shot]):
    """按镜头内容规划音效槽位。"""

    @dataclass
    class Slot:
        key: str
        keywords: list[str]
        duration: float

    @dataclass
    class Plan:
        slots: list[Slot]

    slots = []
    for shot in shots:
        keywords = [word for word in ("夜", "街", "林", "室内", "海", "山") if word in shot.prompt]
        slots.append(
            Slot(
                key=f"sfx-{shot.index:02d}",
                keywords=keywords or ["室内"],
                duration=float(shot.duration_seconds),
            )
        )
    return Plan(slots=slots)
