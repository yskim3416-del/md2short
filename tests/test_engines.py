import json

import httpx

from md2short import script_engine, transcript, voice
from md2short.script_engine import _looks_korean


def _client(handler):
    return httpx.Client(transport=httpx.MockTransport(handler))


def test_looks_korean():
    assert _looks_korean("S&P 500 종가 7,230 기록했습니다. AI 시장이 커졌습니다.")
    assert _looks_korean("AMD와 NVIDIA가 상승했습니다.")
    assert not _looks_korean("The market closed higher on Friday after strong earnings.")
    assert not _looks_korean("증시가 上昇했습니다.")
    assert not _looks_korean("주가가 올랐습니다 and the market was very strong today.")


def test_generate_script_openai_success():
    seen = {}

    def handler(req):
        seen["body"] = json.loads(req.content)
        seen["auth"] = req.headers["authorization"]
        out = {"hook": "미국 증시가 상승했습니다.", "body": "나스닥은 0.94% 올랐습니다.", "cta": "내일도 전해드리겠습니다."}
        return httpx.Response(200, json={
            "output": [{"type": "message", "content": [{"type": "output_text", "text": json.dumps(out, ensure_ascii=False)}]}],
            "usage": {"input_tokens": 620, "output_tokens": 2107},
        })

    script, plan = script_engine.generate_script("# 증시\n상승", api_key="k", client=_client(handler))
    assert plan == {"engine": "openai", "model": "gpt-5-mini", "usage": {"input_tokens": 620, "output_tokens": 2107}}
    assert script["body"] == "나스닥은 0.94% 올랐습니다."
    assert seen["auth"] == "Bearer k"
    user = seen["body"]["input"][1]["content"]
    assert user.startswith("<user_content>") and user.endswith("</user_content>")
    assert seen["body"]["text"]["format"]["type"] == "json_schema"
    assert seen["body"]["text"]["format"]["schema"]["required"] == ["hook", "body", "cta"]


def test_generate_script_fallbacks():
    md = "# 제목\n- 나스닥이 올랐습니다\n- 다우는 내렸습니다"
    script, plan = script_engine.generate_script(md, api_key=None, client=_client(lambda r: httpx.Response(500)))
    assert plan["engine"] == "fallback_extract" and "OPENAI_API_KEY" in plan["fallback_reason"]
    assert script["hook"] == "제목."

    def english(req):
        out = {"hook": "The market rallied strongly today.", "body": "Stocks went up a lot this week.", "cta": ""}
        return httpx.Response(200, json={"output_text": json.dumps(out)})

    _, plan = script_engine.generate_script(md, api_key="k", client=_client(english))
    assert plan["engine"] == "fallback_extract" and "non-Korean" in plan["fallback_reason"]

    _, plan = script_engine.generate_script(md, api_key="k", client=_client(lambda r: httpx.Response(401, text="bad")))
    assert plan["engine"] == "fallback_extract" and "401" in plan["fallback_reason"]


def test_voice_synthesize(tmp_path):
    seen = {}

    def handler(req):
        seen["url"] = str(req.url)
        seen["key"] = req.headers["xi-api-key"]
        seen["body"] = json.loads(req.content)
        return httpx.Response(200, content=b"ID3fake")

    out = voice.synthesize("안녕하세요", voice_id="vid", speed=1.1, api_key="ek", out_path=tmp_path / "n.mp3", client=_client(handler))
    assert out.read_bytes() == b"ID3fake"
    assert "/v1/text-to-speech/vid" in seen["url"] and "output_format=mp3_44100_128" in seen["url"]
    assert seen["key"] == "ek"
    assert seen["body"]["model_id"] == "eleven_multilingual_v2"
    assert seen["body"]["voice_settings"]["speed"] == 1.1


def test_transcribe(tmp_path):
    audio = tmp_path / "n.mp3"
    audio.write_bytes(b"ID3fake")
    seen = {}

    def handler(req):
        seen["url"] = str(req.url)
        seen["body"] = req.content
        return httpx.Response(200, json={
            "language_code": "kor", "text": "금일 미국",
            "words": [
                {"text": "금일", "start": 0.0, "end": 0.3204, "type": "word"},
                {"text": " ", "start": 0.3204, "end": 0.33, "type": "spacing"},
                {"text": "미국", "start": 0.3305, "end": 0.59, "type": "word"},
            ],
        })

    raw = tmp_path / "scribe_raw.json"
    doc = transcript.transcribe(audio, api_key="ek", audio_duration_ms=900, client=_client(handler), raw_log=raw)
    assert seen["url"].endswith("/v1/speech-to-text")
    assert b"scribe_v1" in seen["body"] and b"kor" in seen["body"]
    assert [(w.text, w.start, w.end) for w in doc.words] == [("금일", 0, 320), ("미국", 330, 590)]
    assert doc.audio_duration_ms == 900 and doc.language_code == "kor"
    assert json.loads(raw.read_text(encoding="utf-8"))["text"] == "금일 미국"
