"""TTS 전용 텍스트 보정.

자막(표시) 대본은 그대로 두고, ElevenLabs에 보내는 텍스트만 숫자·약어를 한국어 발음형으로 바꾸고
pause가 과한 구두점을 평탄화한다. `to_spoken()`은 numeric_display 정렬에서도 같은 규칙으로 재사용된다.
"""

from __future__ import annotations

import re

_DIGITS = "영일이삼사오육칠팔구"
_SMALL_UNITS = ["", "십", "백", "천"]
_BIG_UNITS = ["", "만", "억", "조", "경"]

_NATIVE_ONES = ["", "한", "두", "세", "네", "다섯", "여섯", "일곱", "여덟", "아홉"]
_NATIVE_TENS = ["", "열", "스물", "서른", "마흔", "쉰", "예순", "일흔", "여든", "아흔"]
# 고유어 수사를 쓰는 단위 (1~99만 고유어로 읽음)
_NATIVE_COUNTERS = ("개", "명", "시간", "시", "번째", "번", "살", "가지", "마리", "곳", "차례")

# 약어 → 발음. 긴 키부터 매칭한다.
ACRONYM_READINGS: dict[str, str] = {
    "S&P": "에스앤피",
    "AI": "에이아이",
    "AMD": "에이엠디",
    "ETF": "이티에프",
    "CPI": "씨피아이",
    "PCE": "피씨이",
    "GDP": "지디피",
    "IPO": "아이피오",
    "CEO": "씨이오",
    "FOMC": "에프오엠씨",
    "Fed": "연준",
    "IT": "아이티",
    "EV": "이브이",
    "UAE": "유에이이",
    "TSMC": "티에스엠씨",
    "NVIDIA": "엔비디아",
}
_LETTER_NAMES = {
    "A": "에이", "B": "비", "C": "씨", "D": "디", "E": "이", "F": "에프", "G": "지", "H": "에이치",
    "I": "아이", "J": "제이", "K": "케이", "L": "엘", "M": "엠", "N": "엔", "O": "오", "P": "피",
    "Q": "큐", "R": "알", "S": "에스", "T": "티", "U": "유", "V": "브이", "W": "더블유", "X": "엑스",
    "Y": "와이", "Z": "지",
}


def _read_under_10000(n: int) -> str:
    out = []
    for pos in range(3, -1, -1):
        d = (n // 10**pos) % 10
        if d == 0:
            continue
        digit = "" if (d == 1 and pos > 0) else _DIGITS[d]
        out.append(digit + _SMALL_UNITS[pos])
    return "".join(out)


def read_sino(n: int) -> str:
    """정수를 한자어 수사로 읽는다. 7230 → 칠천이백삼십."""
    if n == 0:
        return "영"
    parts = []
    group = 0
    while n > 0:
        chunk = n % 10000
        if chunk:
            word = _read_under_10000(chunk)
            if group == 1 and chunk == 1:
                word = ""  # 10000 → 만 (일만 아님)
            parts.append(word + _BIG_UNITS[group])
        n //= 10000
        group += 1
    return "".join(reversed(parts))


def read_number(token: str) -> str:
    """'7,230' / '0.94' / '3.2' → 한자어 발음."""
    token = token.replace(",", "")
    if "." in token:
        whole, frac = token.split(".", 1)
        return read_sino(int(whole or "0")) + "점" + "".join(_DIGITS[int(c)] for c in frac)
    return read_sino(int(token))


def read_native(n: int) -> str | None:
    if not 1 <= n <= 99:
        return None
    if n == 20:
        return "스무"
    return _NATIVE_TENS[n // 10] + _NATIVE_ONES[n % 10]


_NUM = r"\d{1,3}(?:,\d{3})+(?:\.\d+)?|\d+(?:\.\d+)?"
_PERCENT_RE = re.compile(rf"({_NUM})\s*(%|퍼센트|프로)")
# 개월·개국은 한자어 수사로 읽는다 (2개월 → 이개월)
_COUNTER_RE = re.compile(rf"(\d+)\s*({'|'.join(_NATIVE_COUNTERS)})(?!월|국)")
_NUMBER_RE = re.compile(_NUM)
# 연도는 "천구백오십 년"처럼 수와 단위를 띄워 한 덩어리로 몰아 읽지 않게 한다
_YEAR_RE = re.compile(r"(?<![\d,.])(\d{4})\s*년")
_ACRONYM_RE = re.compile("|".join(re.escape(k) for k in sorted(ACRONYM_READINGS, key=len, reverse=True)))
_CAPS_RE = re.compile(r"\b[A-Z]{2,6}\b")


def _spell(word: str) -> str:
    return "".join(_LETTER_NAMES.get(c, c) for c in word)


def to_spoken(text: str) -> str:
    """숫자·약어를 발음형으로 바꾼다 (구두점은 유지)."""
    text = _ACRONYM_RE.sub(lambda m: ACRONYM_READINGS[m.group(0)], text)
    text = _CAPS_RE.sub(lambda m: _spell(m.group(0)), text)
    text = _PERCENT_RE.sub(lambda m: read_number(m.group(1)) + " 퍼센트", text)

    def counter(m: re.Match[str]) -> str:
        native = read_native(int(m.group(1)))
        if m.group(2) == "번째" and m.group(1) == "1":
            native = "첫"
        return f"{native or read_number(m.group(1))} {m.group(2)}"

    text = _YEAR_RE.sub(lambda m: read_sino(int(m.group(1))) + " 년", text)
    text = _COUNTER_RE.sub(counter, text)
    return _NUMBER_RE.sub(lambda m: read_number(m.group(0)), text)


_PAUSE_MAP = [
    (re.compile(r"[‘’“”\"'「」『』]"), ""),
    (re.compile(r"\s*[—–]\s*"), ", "),
    (re.compile(r"…+|\.{3,}"), ","),
    (re.compile(r"[·•]"), " "),
    (re.compile(r"[ \t]+"), " "),
]


def prepare_tts_text(display_script: str) -> str:
    """ElevenLabs 입력 텍스트. 문단 줄바꿈은 문장 사이 공백으로 평탄화한다."""
    text = to_spoken(display_script)
    for pattern, repl in _PAUSE_MAP:
        text = pattern.sub(repl, text)
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    return " ".join(lines)
