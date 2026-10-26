"""자막 segment 분할 — Remotion `Captions.tsx` fallback 규칙과 동일 (.omc/contracts/props-contract.md).

Python이 boundary를 확정해 `captionSegments`로 넘기고, visual cue도 같은 boundary를 공유한다.
"""

from __future__ import annotations

import re

from md2short.schema import CaptionWord

GAP_BOUNDARY_MS = 600
MAX_SEGMENT_CHARS = 28  # 문장이 이보다 길면 의미 단위로 나눔 — 2줄에 읽히는 글자 크기 유지
GAP_MIN_WORDS = 5  # 쉼으로 끊는 건 이미 이만큼 쌓인 경우만 — "미국 증시가"처럼 주어만 남는 조각 방지
_SENTENCE_END = re.compile(r"[.!?。！？…][\"'”’)」』\]）]*$")  # Captions.tsx TRAILING_QUOTES와 동일


def ends_sentence(text: str) -> bool:
    return bool(_SENTENCE_END.search(text.strip()))


_GOOD_BREAK = re.compile(r"(,|은|는|이|가|을|를|에|에서|로|으로|와|과|고|며|면|서|도|만|이후|이전|동안|때문에)$")
BREAK_PENALTY = 10  # 조사·쉼표로 끝나지 않는 단어 뒤에서 끊을 때의 글자 수 환산 벌점


def _balanced_end(words: list[CaptionWord], start: int) -> int | None:
    """start부터 문장 끝까지가 MAX_SEGMENT_CHARS를 넘으면 이번 조각을 끝낼 word index, 아니면 None.

    균등 분할 목표 길이에 가깝고 조사·쉼표로 끝나는(의미 단위) 단어 뒤를 고른다
    — "정부의 AI 시장이 본격" / "사용자" 같은 어색한 끊김 방지.
    """
    end = start
    while end < len(words) - 1 and not ends_sentence(words[end].text):
        end += 1
    total = len(" ".join(w.text for w in words[start: end + 1]))
    if total <= MAX_SEGMENT_CHARS:
        return None
    target = total / -(-total // MAX_SEGMENT_CHARS)
    best: tuple[float, int] | None = None
    for j in range(start, end):
        prefix = len(" ".join(w.text for w in words[start: j + 1]))
        if prefix > MAX_SEGMENT_CHARS:
            break
        cost = abs(prefix - target) + (0 if _GOOD_BREAK.search(words[j].text) else BREAK_PENALTY)
        if best is None or cost < best[0]:
            best = (cost, j)
    return best[1] if best else start


def build_caption_segments(
    words: list[CaptionWord],
    chunk_size: int = 14,
    skip_before_ms: int = 0,
    forced_breaks: set[int] | None = None,
) -> list[dict]:
    """`[wordStart, wordEnd)` 인덱스 범위 segment 목록.

    forced_breaks: 이 word index *뒤에서* 반드시 끊는다 (스토리보드 컷 경계).
    """
    forced_breaks = forced_breaks or set()
    segments: list[dict] = []
    start: int | None = None
    for i, w in enumerate(words):
        if w.start < skip_before_ms:
            continue
        if start is None:
            start = i
            split_at = _balanced_end(words, i)
        nxt = words[i + 1] if i + 1 < len(words) else None
        close = (
            nxt is None
            or ends_sentence(w.text)
            or ((nxt.start - w.end) >= GAP_BOUNDARY_MS and (i - start + 1) >= GAP_MIN_WORDS)
            or (i - start + 1) >= chunk_size
            or i in forced_breaks
            or i == split_at
        )
        if close:
            chunk = words[start: i + 1]
            segments.append({
                "startMs": chunk[0].start,
                "endMs": chunk[-1].end,
                "wordStart": start,
                "wordEnd": i + 1,
                "text": " ".join(x.text for x in chunk),
            })
            start = None
    return segments
