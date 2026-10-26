"""ElevenLabs Scribe 단어 타임스탬프 (docs/architecture.md §5.3)."""

from __future__ import annotations

import json
from pathlib import Path

import httpx

from md2short._retry import DEFAULT_TIMEOUT, post_with_retry
from md2short.schema import SCRIBE_LANG, CaptionWord, WordsDoc

STT_URL = "https://api.elevenlabs.io/v1/speech-to-text"
STT_MODEL = "scribe_v1"


def parse_scribe(payload: dict, audio_duration_ms: int, language: str = "ko") -> WordsDoc:
    words = [
        CaptionWord(text=w["text"].strip(), start=round(float(w["start"]) * 1000), end=round(float(w["end"]) * 1000))
        for w in payload.get("words", [])
        if w.get("type", "word") == "word" and w.get("text", "").strip()
    ]
    return WordsDoc(
        language_code=SCRIBE_LANG[language],
        audio_duration_ms=audio_duration_ms,
        text=payload.get("text", ""),
        words=words,
    )


def transcribe(
    audio_path: Path,
    *,
    api_key: str,
    audio_duration_ms: int,
    client: httpx.Client,
    raw_log: Path,
    language: str = "ko",
) -> WordsDoc:
    with audio_path.open("rb") as fh:
        resp = post_with_retry(
            client,
            STT_URL,
            headers={"xi-api-key": api_key},
            data={
                "model_id": STT_MODEL,
                "language_code": SCRIBE_LANG[language],
                "timestamps_granularity": "word",
                "tag_audio_events": "false",
            },
            files={"file": (audio_path.name, fh.read(), "audio/mpeg")},
            timeout=DEFAULT_TIMEOUT,
        )
    payload = resp.json()
    raw_log.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    doc = parse_scribe(payload, audio_duration_ms, language)
    if not doc.words:
        raise RuntimeError("Scribe returned no words")
    return doc
