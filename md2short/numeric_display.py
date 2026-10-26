"""Scribe 단어의 표시 텍스트를 대본 원문 표기로 복원한다 (timing은 Scribe 값 유지).

Scribe는 숫자·약어를 발음형("칠천이백삼십", "에센피")으로 전사하는 경우가 있다. 대본 토큰과 Scribe 단어를
같은 발음 정규화(`tts_text.to_spoken`) 후 시퀀스 정렬하고, 충분히 닮은 구간만 원문 토큰으로 바꾼다.
토큰 수와 단어 수가 다른 구간은 한 표시 단어로 합치되 start=첫 단어, end=마지막 단어를 쓴다.
"""

from __future__ import annotations

import re
from difflib import SequenceMatcher

from md2short.schema import CaptionWord
from md2short.tts_text import to_spoken

# replace 구간을 원문으로 바꿀 최소 발음 유사도 (concat 기준). 앞뒤가 equal 블록에 끼인 구간이라
# 위치 근거가 강하므로 음역 변형(에센피 ↔ 에스앤피 = 0.57)까지 받아들이도록 0.5로 둔다.
SPAN_MATCH_THRESHOLD = 0.5

_KEEP = re.compile(r"[^0-9a-z가-힣]")


def _key(text: str) -> str:
    return _KEEP.sub("", to_spoken(text).lower())


def _similar(a: str, b: str) -> float:
    if not a and not b:
        return 1.0
    return SequenceMatcher(None, a, b, autojunk=False).ratio()


def align_display_words(
    script_text: str, words: list[CaptionWord]
) -> tuple[list[CaptionWord], list[int | None]]:
    """(표시용 words, 각 word가 대응하는 대본 토큰 index 또는 None)."""
    tokens = script_text.split()
    tkeys = [_key(t) for t in tokens]
    wkeys = [_key(w.text) for w in words]
    out: list[CaptionWord] = []
    src: list[int | None] = []
    matcher = SequenceMatcher(None, tkeys, wkeys, autojunk=False)
    for op, i1, i2, j1, j2 in matcher.get_opcodes():
        if op == "equal":
            for k in range(i2 - i1):
                w = words[j1 + k]
                out.append(CaptionWord(text=tokens[i1 + k], start=w.start, end=w.end))
                src.append(i1 + k)
        elif op == "replace":
            span_t = "".join(tkeys[i1:i2])
            span_w = "".join(wkeys[j1:j2])
            if _similar(span_t, span_w) >= SPAN_MATCH_THRESHOLD:
                if i2 - i1 == j2 - j1:
                    for k in range(i2 - i1):
                        w = words[j1 + k]
                        out.append(CaptionWord(text=tokens[i1 + k], start=w.start, end=w.end))
                        src.append(i1 + k)
                else:
                    # 개수가 다르면(Scribe가 토큰을 쪼갰거나 합침) 구간 전체를 한 표시 단어로 합친다
                    out.append(CaptionWord(text=" ".join(tokens[i1:i2]), start=words[j1].start, end=words[j2 - 1].end))
                    src.append(i1)
            else:
                out.extend(words[j1:j2])
                src.extend([None] * (j2 - j1))
        elif op == "insert":
            out.extend(words[j1:j2])
            src.extend([None] * (j2 - j1))
        elif op == "delete" and out:
            # Scribe가 놓친 토큰은 직전 단어에 붙여 표시만 보존한다 (timing 불변)
            prev = out[-1]
            out[-1] = CaptionWord(text=" ".join([prev.text, *tokens[i1:i2]]), start=prev.start, end=prev.end)
    return out, src

