"""데이터 모델 (docs/architecture.md §4)."""

from __future__ import annotations

import re
from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field, field_validator

DEFAULT_VOICES: dict[str, str] = {"ko": "v1jVu1Ky28piIPEJqRrm"}
CTA_TEXT: dict[str, str] = {"ko": "구독과 알림 설정 부탁드립니다"}
SCRIBE_LANG: dict[str, str] = {"ko": "kor"}


class VisualMode(str, Enum):
    emoticon = "emoticon"
    photo = "photo"


class JobConfig(BaseModel):
    platform: Literal["youtube_shorts", "instagram_reels", "tiktok"] = "youtube_shorts"
    language: Literal["ko"] = "ko"
    voice_id: str = DEFAULT_VOICES["ko"]
    voice_speed: float = Field(1.0, ge=0.7, le=1.2)
    template_id: str = "tech_explainer"
    bg_color: str = "0xFFFFFF"
    chunk_size: int = Field(14, ge=1, le=24)
    engine: Literal["remotion"] = "remotion"
    visual_mode: Literal["emoticon", "photo"] = "emoticon"
    show_opening: bool = True
    show_outro: bool = False
    audio_post: bool = True  # TTS 무음 압축 + 라우드니스 정규화
    model: str = "gpt-5-mini"

    @field_validator("bg_color")
    @classmethod
    def _check_bg(cls, v: str) -> str:
        if not re.fullmatch(r"(0x|#)?[0-9A-Fa-f]{6}", v):
            raise ValueError(f"bg_color must be a 6-digit hex color, got {v!r}")
        return v

    @property
    def bg_css(self) -> str:
        """`0xFFFFFF` / `FFFFFF` / `#ffffff` → `#FFFFFF`."""
        return "#" + self.bg_color[-6:].upper()


class CaptionWord(BaseModel):
    text: str
    start: int
    end: int


class WordsDoc(BaseModel):
    language_code: str = "kor"
    audio_duration_ms: int
    text: str = ""
    words: list[CaptionWord]
