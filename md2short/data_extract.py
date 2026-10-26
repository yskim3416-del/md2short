"""숫자·지표 NumberCard cue (docs/architecture.md §5.9).

표시 정렬된 words.json 단어에서 직접 숫자를 찾으므로 timing은 해당 단어의 실측 start를 쓴다.
"""

from __future__ import annotations

import re

from md2short.caption_plan import ends_sentence
from md2short.schema import CaptionWord

MAX_CARDS = 6
COOLDOWN_MS = 2500
CARD_DURATION_MS = 1800
INDEX_LOOKAHEAD_WORDS = 3

INDEX_NAMES = ["S&P 500", "S&P500", "코스피", "코스닥", "나스닥", "다우", "니케이", "항셍"]

_NUM = r"[+-]?\d{1,3}(?:,\d{3})+(?:\.\d+)?|[+-]?\d+(?:\.\d+)?"
_PERCENT = re.compile(rf"^({_NUM})\s*(%|퍼센트|프로)")
_POINT = re.compile(rf"^({_NUM})\s*(포인트|p\b|P\b)")
_MONEY = re.compile(rf"^({_NUM})\s*(조|억|만)?\s*(원|달러)")
# 날짜·횟수 단위가 붙은 숫자(4월, 5주, 2024년)는 지수 값이 아니다
_BARE = re.compile(rf"^({_NUM})(?![\d.,]|월|일|년|주|거래일|번째|개월|분기|시간)")


_PARTICLE = re.compile(r"(으로|에서|까지|부터|이|가|은|는|을|를|의|로|도|와|과)$")


def strip_particle(word: str) -> str:
    """카드 라벨용: 끝 조사 1개 제거 (로블록스가 → 로블록스). 2글자 이하 단어는 그대로 둔다."""
    stripped = _PARTICLE.sub("", word)
    return stripped if len(stripped) >= 2 else word


def _index_label(words: list[CaptionWord], i: int) -> tuple[str, int] | None:
    """i 위치(포함)부터 지수명이면 (라벨, 지수명이 차지한 단어 수)."""
    joined = words[i].text
    for name in INDEX_NAMES:
        if " " in name and joined.startswith(name):  # 표시 정렬이 "S&P 500은"처럼 한 단어로 합친 경우
            return name, 1
        if joined.startswith(name.split()[0]):
            parts = name.split()
            if len(parts) == 2 and i + 1 < len(words) and words[i + 1].text.startswith(parts[1]):
                return name, 2
            if len(parts) == 1:
                return name, 1
    return None


_SUBJECT = re.compile(r"(은|는|이|가)$")
_UP = ("급등", "상승", "올랐", "오른", "강세", "증가", "개선", "호실적", "랠리")
_DOWN = ("급락", "폭락", "하락", "내렸", "내린", "떨어", "약세", "감소", "부진")


def _sentence_bounds(words: list[CaptionWord], i: int) -> tuple[int, int]:
    """i가 속한 문장의 [시작, 끝) word index."""
    start = i
    while start > 0 and not ends_sentence(words[start - 1].text):
        start -= 1
    end = i
    while end < len(words) - 1 and not ends_sentence(words[end].text):
        end += 1
    return start, end + 1


def _subject_label(words: list[CaptionWord], i: int) -> str:
    """같은 문장에서 수치 앞의 가장 가까운 주어(은/는/이/가) — "애플은 호실적으로 3.2%" → 애플. 없으면 직전 단어."""
    start, _ = _sentence_bounds(words, i)
    for k in range(i - 1, start - 1, -1):
        text = re.sub(r"[,.]$", "", words[k].text)
        if _SUBJECT.search(text) and not re.match(r"[+-]?\d", text):
            return strip_particle(text)
    return strip_particle(re.sub(r"[,.]$", "", words[i - 1].text)) if i > 0 else ""


def sentence_tone(text: str) -> str:
    """'up' | 'down' | 'neutral' — 상승=빨강, 하락=파랑 색상 규칙용."""
    down = any(k in text for k in _DOWN)
    up = any(k in text for k in _UP)
    if up == down:
        return "neutral"
    return "up" if up else "down"


def _card_at(words: list[CaptionWord], i: int) -> str | None:
    """i번째 단어에서 시작하는 수치 표현. 단위가 뒤 단어로 떨어진 경우(`2,650` `포인트`, `3조` `원`)까지 본다."""
    if not re.match(r"[+-]?\d", words[i].text):
        return None
    for span in (1, 2, 3):
        text = " ".join(w.text for w in words[i: i + span])
        for pat in (_PERCENT, _POINT, _MONEY):
            m = pat.match(text)
            if m:
                return re.sub(r"[,.]$", "", m.group(0).strip())
    return None


def _tone_at(words: list[CaptionWord], i: int) -> str:
    start, end = _sentence_bounds(words, i)
    return sentence_tone(" ".join(w.text for w in words[start:end]))


def plan_number_cards(words: list[CaptionWord], skip_before_ms: int = 0) -> list[dict]:
    candidates: list[dict] = []
    i = 0
    while i < len(words):
        w = words[i]
        if w.start < skip_before_ms:
            i += 1
            continue
        idx = _index_label(words, i)
        if idx:
            label, span = idx
            for j in range(i + span, min(len(words), i + span + INDEX_LOOKAHEAD_WORDS)):
                if ends_sentence(words[j - 1].text):
                    break  # 지수명과 값은 같은 문장 안에 있어야 한다
                m = _BARE.match(words[j].text)
                if m:
                    candidates.append({"startMs": words[j].start, "text": _card_at(words, j) or m.group(1), "label": label,
                                       "tone": _tone_at(words, j)})
                    break
            i += span
            continue
        card = _card_at(words, i)
        if card:
            candidates.append({"startMs": w.start, "text": card, "label": _subject_label(words, i), "tone": _tone_at(words, i)})
        i += 1

    cards: list[dict] = []
    last = -COOLDOWN_MS
    for c in candidates:
        if len(cards) >= MAX_CARDS:
            break
        if c["startMs"] - last < COOLDOWN_MS:
            continue
        if any(c["text"] == k["text"] and c["label"] == k["label"] for k in cards):
            continue  # CTA 등에서 같은 수치를 다시 말할 때 카드 반복 방지
        cards.append({**c, "durationMs": CARD_DURATION_MS})
        last = c["startMs"]
    return cards
