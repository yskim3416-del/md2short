"""날짜 기반 오프닝 (docs/architecture.md §5.10)."""

from __future__ import annotations

import re
from datetime import date

from md2short.schema import CaptionWord

OPENING_TEMPLATES = {"ko": "{month}월 {day}일 데이브리핑입니다."}
_OPENING_END = "데이브리핑"


def spoken_opening(today: date, language: str = "ko") -> str:
    return OPENING_TEMPLATES[language].format(month=today.month, day=today.day)


def opening_visual_text(today: date) -> str:
    return f"{today.year % 100}년 {today.month}월 {today.day}일\n데이브리핑"


def opening_duration_ms(words: list[CaptionWord], max_words: int = 8) -> int:
    """오프닝 문구가 끝나는 단어의 end(ms). words.json 실측값만 사용한다."""
    for w in words[:max_words]:
        if _OPENING_END in re.sub(r"\s", "", w.text):
            return w.end
    return 0
