from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import httpx
import pytest

from md2short.schema import CaptionWord

ROOT = Path(__file__).resolve().parent.parent


def words_from_text(text: str, start_ms: int = 0, step_ms: int = 400, gap_ms: int = 40) -> list[CaptionWord]:
    out = []
    t = start_ms
    for tok in text.split():
        out.append(CaptionWord(text=tok, start=t, end=t + step_ms - gap_ms))
        t += step_ms
    return out


def make_mp3(path: Path, seconds: float) -> bytes:
    subprocess.run(
        ["ffmpeg", "-y", "-loglevel", "error", "-f", "lavfi", "-i", f"sine=frequency=330:duration={seconds}",
         "-ac", "1", "-ar", "44100", "-b:a", "128k", str(path)],
        check=True,
    )
    return path.read_bytes()


class FakeApis:
    """OpenAI/ElevenLabs mock. TTS 입력 텍스트 단어 수로 오디오 길이를 정하고 Scribe는 그 단어를 균등 배치한다."""

    STEP_MS = 400

    def __init__(self, tmp: Path, openai_script: dict | None = None):
        self.tmp = tmp
        self.openai_script = openai_script
        self.tts_text = ""
        self.calls: list[str] = []

    def handler(self, request: httpx.Request) -> httpx.Response:
        url = str(request.url)
        self.calls.append(url)
        if "api.openai.com" in url:
            if self.openai_script is None:
                return httpx.Response(500, text="boom")
            return httpx.Response(200, json={"output": [{"content": [{"type": "output_text", "text": json.dumps(self.openai_script, ensure_ascii=False)}]}]})
        if "text-to-speech" in url:
            self.tts_text = json.loads(request.content)["text"]
            seconds = len(self.tts_text.split()) * self.STEP_MS / 1000 + 0.3
            return httpx.Response(200, content=make_mp3(self.tmp / "tts.mp3", seconds))
        if "speech-to-text" in url:
            words = [
                {"text": w.text, "start": w.start / 1000, "end": w.end / 1000, "type": "word"}
                for w in words_from_text(self.tts_text, step_ms=self.STEP_MS)
            ]
            return httpx.Response(200, json={"language_code": "kor", "text": self.tts_text, "words": words})
        return httpx.Response(404)

    def client(self) -> httpx.Client:
        return httpx.Client(transport=httpx.MockTransport(self.handler))


@pytest.fixture
def fake_apis(tmp_path):
    return FakeApis(tmp_path)


def render_available() -> bool:
    return bool(shutil.which("ffmpeg") and shutil.which("npx") and (ROOT / "remotion" / "node_modules").exists())
