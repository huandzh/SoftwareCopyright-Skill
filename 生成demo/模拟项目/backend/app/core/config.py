"""运行配置：全部来自环境变量，带安全的本地默认值。"""

from __future__ import annotations

import os
from dataclasses import dataclass, field


def _env(name: str, default: str = "") -> str:
    return os.environ.get(name, default).strip()


def _env_int(name: str, default: int) -> int:
    raw = _env(name)
    if not raw:
        return default
    try:
        return int(raw)
    except ValueError:
        return default


@dataclass(frozen=True)
class Settings:
    """平台配置。生产环境必须通过环境变量覆盖默认值。"""

    app_name: str = "studioagent"
    environment: str = field(default_factory=lambda: _env("APP_ENV", "development"))
    database_url: str = field(
        default_factory=lambda: _env(
            "DATABASE_URL",
            "postgresql+asyncpg://studio:studio@127.0.0.1:5432/studioagent",
        )
    )
    redis_url: str = field(default_factory=lambda: _env("REDIS_URL", "redis://127.0.0.1:6379/0"))
    storage_root: str = field(default_factory=lambda: _env("STORAGE_ROOT", "./storage"))
    allowed_origins: list[str] = field(
        default_factory=lambda: [
            item.strip()
            for item in _env("ALLOWED_ORIGINS", "http://127.0.0.1:3000").split(",")
            if item.strip()
        ]
    )
    session_ttl_seconds: int = field(default_factory=lambda: _env_int("SESSION_TTL", 60 * 60 * 12))
    max_parallel_generations: int = field(default_factory=lambda: _env_int("MAX_PARALLEL", 3))
    default_model_profile: str = field(default_factory=lambda: _env("MODEL_PROFILE", "balanced"))
    image_provider: str = field(default_factory=lambda: _env("IMAGE_PROVIDER", "local-diffusion"))
    video_provider: str = field(default_factory=lambda: _env("VIDEO_PROVIDER", "frame-interpolation"))
    tts_provider: str = field(default_factory=lambda: _env("TTS_PROVIDER", "edge-tts"))
    monthly_budget: float = field(default_factory=lambda: float(_env("MONTHLY_BUDGET", "200") or 200))

    @property
    def is_production(self) -> bool:
        return self.environment.lower() in {"production", "prod"}


settings = Settings()
