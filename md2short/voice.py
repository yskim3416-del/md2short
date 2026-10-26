"""ElevenLabs TTS (docs/architecture.md §5.2)."""

from __future__ import annotations

from pathlib import Path

import httpx

from md2short._retry import DEFAULT_TIMEOUT, post_with_retry

TTS_URL = "https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
TTS_MODEL = "eleven_multilingual_v2"
OUTPUT_FORMAT = "mp3_44100_128"


def synthesize(
    text: str,
    *,
    voice_id: str,
    speed: float,
    api_key: str,
    out_path: Path,
    client: httpx.Client,
) -> Path:
    resp = post_with_retry(
        client,
        TTS_URL.format(voice_id=voice_id),
        params={"output_format": OUTPUT_FORMAT},
        headers={"xi-api-key": api_key, "Accept": "audio/mpeg"},
        json={
            "text": text,
            "model_id": TTS_MODEL,
            "voice_settings": {"stability": 0.5, "similarity_boost": 0.75, "speed": speed},
        },
        timeout=DEFAULT_TIMEOUT,
    )
    if not resp.content:
        raise RuntimeError("ElevenLabs TTS returned empty audio")
    out_path.write_bytes(resp.content)
    return out_path
