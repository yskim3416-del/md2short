"""마크다운 → 평문 추출 fallback (한국어 전용)."""

from __future__ import annotations

import re

_SENTENCE_END = re.compile(r"(?<=[.!?。！？…])\s+")


def strip_markdown(md: str) -> str:
    text = re.sub(r"```.*?```", "", md, flags=re.S)
    text = re.sub(r"<!--.*?-->", "", text, flags=re.S)
    lines = []
    for raw in text.splitlines():
        line = raw.strip()
        if not line or re.fullmatch(r"[-*_=]{3,}", line) or line.startswith("|"):
            continue
        line = re.sub(r"^#{1,6}\s*", "", line)
        line = re.sub(r"^>\s*", "", line)
        line = re.sub(r"^([-*+]|\d+[.)])\s+", "", line)
        line = re.sub(r"!\[[^\]]*\]\([^)]*\)", "", line)
        line = re.sub(r"\[([^\]]+)\]\([^)]*\)", r"\1", line)
        line = re.sub(r"(\*\*|__|\*|_|`|~~)(.+?)\1", r"\2", line)
        line = line.strip()
        if not line:
            continue
        if not re.search(r"[.!?。！？…]$", line):
            line += "."
        lines.append(line)
    return "\n".join(lines)


def fallback_extract(md: str) -> dict[str, str]:
    """원문 문장을 그대로 보존해 hook/body로 나눈다."""
    text = strip_markdown(md)
    if not text:
        return {"hook": "", "body": "", "cta": ""}
    hook = _SENTENCE_END.split(text, maxsplit=1)[0].strip()
    # 본문은 줄 구조를 유지해야 문단 경계가 자막 boundary로 이어진다
    return {"hook": hook, "body": text[len(hook):].lstrip(), "cta": ""}
