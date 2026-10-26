"""`### N컷` 스토리보드 입력 처리.

`자막` 필드만 내레이션에 쓰고, `화면 연출`은 emoticon cue 선택 힌트로만 쓴다.
"""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass

_CUT_HEADER = re.compile(r"^###\s*(\d+)\s*컷\s*$", re.M)
_FIELD = re.compile(r"^\s*(?:[-*]\s*)?(?:\*\*)?\s*(자막|화면\s*연출|이미지\s*프롬프트)\s*(?:\*\*)?\s*[:：]\s*(?:\*\*)?\s*(.*)$")


@dataclass
class Cut:
    index: int
    caption: str
    direction: str = ""
    image_prompt: str = ""

    def to_dict(self) -> dict:
        return asdict(self)


def is_storyboard(md: str) -> bool:
    return bool(_CUT_HEADER.search(md))


def parse_storyboard(md: str) -> list[Cut]:
    headers = list(_CUT_HEADER.finditer(md))
    cuts: list[Cut] = []
    for i, h in enumerate(headers):
        block = md[h.end(): headers[i + 1].start() if i + 1 < len(headers) else len(md)]
        fields: dict[str, str] = {}
        for line in block.splitlines():
            m = _FIELD.match(line)
            if m:
                key = re.sub(r"\s", "", m.group(1))
                fields[key] = m.group(2).strip().strip('"“”')
        caption = fields.get("자막", "").strip()
        if not caption:
            continue
        if not re.search(r"[.!?。！？…]$", caption):
            caption += "."
        cuts.append(Cut(int(h.group(1)), caption, fields.get("화면연출", ""), fields.get("이미지프롬프트", "")))
    return cuts


def narration(cuts: list[Cut]) -> str:
    """컷마다 한 줄. 줄 경계가 곧 컷 경계다."""
    return "\n".join(c.caption for c in cuts)
