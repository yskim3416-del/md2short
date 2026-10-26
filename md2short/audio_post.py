"""TTS 오디오 후처리: 긴 무음 압축 + 라우드니스 정규화 (docs/architecture.md §5.2).

Scribe 이전에 적용하므로 words.json은 후처리된 오디오 기준으로 측정된다 (시간 추정 없음).
"""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

SILENCE_THRESHOLD_DB = -40
MIN_SILENCE_S = 0.35  # 이보다 긴 무음만 압축
KEEP_EDGE_S = 0.12  # 압축한 무음 양끝에 남기는 길이 (총 0.24s 쉼)
# 문장 끝처럼 긴 쉼은 조금 더 남겨 리듬을 살린다 (총 0.4s)
LONG_SILENCE_S = 0.6
LONG_KEEP_EDGE_S = 0.2
TARGET_LUFS = -14  # 숏폼 플랫폼 기준 라우드니스

_SILENCE_RE = re.compile(r"silence_(start|end): ([\d.]+)")


def detect_silences(path: Path) -> list[tuple[float, float]]:
    proc = subprocess.run(
        ["ffmpeg", "-hide_banner", "-nostats", "-i", str(path),
         "-af", f"silencedetect=noise={SILENCE_THRESHOLD_DB}dB:d={MIN_SILENCE_S}", "-f", "null", "-"],
        capture_output=True, text=True, encoding="utf-8", errors="replace", check=True,
    )
    spans: list[tuple[float, float]] = []
    start: float | None = None
    for kind, value in _SILENCE_RE.findall(proc.stderr):
        if kind == "start":
            start = float(value)
        elif start is not None:
            spans.append((start, float(value)))
            start = None
    return spans


def cut_ranges(silences: list[tuple[float, float]]) -> list[tuple[float, float]]:
    """각 무음 구간의 가운데를 잘라낼 범위. 맨 앞(t=0) 무음은 앞쪽 여유 없이 자른다."""
    cuts = []
    for s, e in silences:
        edge = LONG_KEEP_EDGE_S if e - s >= LONG_SILENCE_S else KEEP_EDGE_S
        a = s + edge if s > 0.01 else 0.0
        b = e - edge
        if b - a > 0.05:
            cuts.append((round(a, 3), round(b, 3)))
    return cuts


def postprocess(src: Path, dst: Path) -> dict:
    """src(TTS 원본) → dst(무음 압축 + loudnorm mp3). 적용 내역을 반환한다."""
    cuts = cut_ranges(detect_silences(src))
    filters = []
    if cuts:
        expr = "+".join(f"between(t,{a},{b})" for a, b in cuts)
        filters += [f"aselect='not({expr})'", "asetpts=N/SR/TB"]
    filters.append(f"loudnorm=I={TARGET_LUFS}:TP=-1.5:LRA=11")
    subprocess.run(
        ["ffmpeg", "-v", "error", "-y", "-i", str(src), "-af", ",".join(filters),
         "-ar", "44100", "-c:a", "libmp3lame", "-b:a", "128k", str(dst)],
        capture_output=True, text=True, encoding="utf-8", errors="replace", check=True,
    )
    return {
        "silence_threshold_db": SILENCE_THRESHOLD_DB,
        "min_silence_s": MIN_SILENCE_S,
        "keep_edge_s": KEEP_EDGE_S,
        "long_silence_s": LONG_SILENCE_S,
        "long_keep_edge_s": LONG_KEEP_EDGE_S,
        "removed_s": round(sum(b - a for a, b in cuts), 3),
        "cuts": len(cuts),
        "target_lufs": TARGET_LUFS,
    }
