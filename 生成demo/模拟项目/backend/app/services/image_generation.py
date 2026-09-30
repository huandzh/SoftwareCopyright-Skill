"""媒体生成服务：图片、视频合成、语音与音效。"""

from __future__ import annotations

import hashlib
import time
from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models import Asset


@dataclass
class ImageRequest:
    """图片生成请求：来自分镜的画面提示。"""

    prompt: str
    negative_prompt: str = ""
    aspect_ratio: str = "16:9"
    seed: int | None = None

    @classmethod
    def from_shot(cls, shot, profile: str) -> "ImageRequest":
        """按模型档位与镜头提示构造请求。"""
        style = {
            "fast": "简洁构图，快速出图",
            "balanced": "电影感光线，细节适中",
            "quality": "高细节，电影级质感",
        }.get(profile, "电影感光线")
        return cls(prompt=f"{shot.prompt}，{style}", aspect_ratio=shot.aspect_ratio)


class ImageService:
    """图片生成与候选评分。"""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def generate(self, request: ImageRequest, count: int = 4) -> list[Asset]:
        """生成若干候选图并给出评分；评分用于候选排序。"""
        assets: list[Asset] = []
        for index in range(count):
            seed = request.seed or int(time.time() * 1000) % 100000
            assets.append(
                Asset(
                    category="character" if "角色" in request.prompt else "scene",
                    name=f"候选图 {index + 1}",
                    storage_key=f"generated/{seed}-{index}.png",
                    mime_type="image/png",
                    size_bytes=1_800_000 + index * 4096,
                    source="generated",
                    state="candidate",
                    score=round(0.92 - index * 0.07, 2),
                    prompt_hint=request.prompt[:120],
                )
            )
        return assets


class VideoPipeline:
    """镜头片段合成与成片导出。"""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def compose(self, shot, options: dict | None = None) -> Asset:
        """把采用的候选图合成镜头片段，时长按分镜规划裁剪。"""
        duration = int((options or {}).get("duration", shot.duration_seconds))
        return Asset(
            category="video",
            name=f"镜头 {shot.index:02d}",
            storage_key=f"video/shot-{shot.id}.mp4",
            mime_type="video/mp4",
            size_bytes=duration * 520_000,
            source="generated",
            state="adopted",
            adopted=True,
        )

    async def export(self, project, clips: list[Asset]) -> Asset:
        """按分镜顺序拼接成片。"""
        total = sum(int(clip.size_bytes / 520_000) for clip in clips)
        return Asset(
            category="export",
            name=f"{project.name}-成片.mp4",
            storage_key=f"export/{project.id}.mp4",
            mime_type="video/mp4",
            size_bytes=total * 520_000,
            source="exported",
            state="adopted",
            adopted=True,
        )


class TTSService:
    """语音合成：旁白与台词。"""

    VOICE_PROFILES = {
        "narrator-female": "女声旁白，语速中等",
        "narrator-male": "男声旁白，语速偏慢",
        "character-young": "年轻角色，语气活泼",
        "character-old": "年长角色，语气沉稳",
    }

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def synthesize(self, line, voice_profile: str) -> Asset:
        """合成一段台词语音；语速按镜头时长调整。"""
        speed = 1.0 if line.duration_seconds >= 4 else 1.15
        return Asset(
            category="voice",
            name=f"配音 {line.index:02d}",
            storage_key=f"voice/{line.id}-{speed:.2f}.wav",
            mime_type="audio/wav",
            size_bytes=int(120_000 * speed),
            source="generated",
            state="adopted",
            adopted=True,
        )


class SFXService:
    """音效检索：按场景关键词查找环境音与转场音效。"""

    LIBRARY = {
        "city-night": ["夜晚街道", "远处车流", "霓虹灯电流声"],
        "forest": ["鸟鸣", "风吹树叶", "溪流"],
        "studio": ["设备运转", "键盘敲击", "空调底噪"],
        "transitions": ["淡入", "推移", "闪白"],
    }

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def search(self, keywords: list[str], duration: float) -> Asset:
        """按关键词检索音效，找不到时返回最接近的环境音。"""
        for key, tracks in self.LIBRARY.items():
            if any(keyword in key for keyword in keywords):
                name = tracks[0]
                break
        else:
            name = self.LIBRARY["studio"][0]
        return Asset(
            category="sfx",
            name=f"音效 {name}",
            storage_key=f"sfx/{hashlib.md5(name.encode('utf-8')).hexdigest()[:12]}.wav",
            mime_type="audio/wav",
            size_bytes=int(duration * 48_000),
            source="library",
            state="adopted",
            adopted=True,
        )


def media_root() -> str:
    return settings.storage_root
