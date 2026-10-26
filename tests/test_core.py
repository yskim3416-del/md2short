import re
from datetime import datetime

import httpx
import pytest
from pydantic import ValidationError

from md2short import _retry
from md2short.qc import estimate_cost, run_qc
from md2short.schema import JobConfig
from md2short.state import JobStatus, new_job_id, validate_transition
from md2short.timeutil import frames_to_ms, ms_to_frames


def test_ms_frame_helpers():
    assert ms_to_frames(1000) == 30
    assert ms_to_frames(2800) == 84
    assert ms_to_frames(16) == 0 and ms_to_frames(17) == 1
    assert frames_to_ms(30) == 1000
    assert frames_to_ms(ms_to_frames(30000)) == 30000


def test_job_id_format():
    jid = new_job_id(datetime(2026, 10, 26))
    assert re.fullmatch(r"sf_20261026_[0-9a-f]{6}", jid)


def test_state_happy_path(tmp_path):
    st = JobStatus(tmp_path)
    for s in ["created", "script_generated", "voice_generated", "transcribed", "subtitled", "final_rendered", "qc_passed"]:
        st.write(s)
    data = st.read()
    assert data["status"] == "qc_passed"
    assert [h["status"] for h in data["history"]][-1] == "qc_passed"


@pytest.mark.parametrize("cur,new", [
    (None, "script_generated"),
    ("created", "voice_generated"),
    ("transcribed", "final_rendered"),
    ("qc_passed", "failed"),
    ("failed", "created"),
    ("subtitled", "qc_passed"),
])
def test_state_rejects_invalid(cur, new):
    with pytest.raises(ValueError):
        validate_transition(cur, new)


@pytest.mark.parametrize("cur", ["created", "script_generated", "voice_generated", "transcribed", "subtitled", "final_rendered"])
def test_any_non_terminal_can_fail(cur):
    validate_transition(cur, "failed")


def test_jobconfig_locks():
    cfg = JobConfig()
    assert cfg.language == "ko" and cfg.visual_mode == "emoticon" and cfg.bg_css == "#FFFFFF"
    assert JobConfig(bg_color="#1a2b3c").bg_css == "#1A2B3C"
    for bad in ({"language": "en"}, {"chunk_size": 25}, {"voice_speed": 2.0}, {"bg_color": "red"}):
        with pytest.raises(ValidationError):
            JobConfig(**bad)


@pytest.mark.parametrize("tail,render,ok_tail,ok_render", [
    (1000, 100, True, True),
    (1001, 100, False, True),
    (-1000, -100, True, True),
    (0, 101, True, False),
    (0, -101, True, False),
])
def test_qc_tolerance_boundaries(tail, render, ok_tail, ok_render):
    audio = 30000
    report = run_qc(audio_ms=audio, last_word_end_ms=audio - tail, final_mp4_ms=audio + render, cost=estimate_cost(0, audio, 0, 0))
    checks = {c["name"]: c["passed"] for c in report["checks"]}
    assert checks == {"sync_last_word_vs_audio": ok_tail, "final_mp4_vs_audio": ok_render}
    assert report["passed"] is (ok_tail and ok_render)


def test_cost_estimate_uses_tokens():
    cost = estimate_cost(tts_chars=1000, audio_ms=3_600_000, openai_input_tokens=1_000_000, openai_output_tokens=0)
    assert cost["elevenlabs_tts_usd"] == 0.30 and cost["elevenlabs_stt_usd"] == 0.40
    assert cost["openai_text_usd"] == 1.25 and cost["total_usd"] == 1.95


def _client(responses):
    seq = iter(responses)

    def handler(request):
        r = next(seq)
        if isinstance(r, Exception):
            raise r
        return r

    return httpx.Client(transport=httpx.MockTransport(handler))


def test_retry_recovers_after_429_and_timeout():
    sleeps = []
    client = _client([
        httpx.Response(429), httpx.ReadTimeout("slow"), httpx.Response(503), httpx.Response(200, text="ok"),
    ])
    resp = _retry.post_with_retry(client, "https://x.test", sleep=sleeps.append)
    assert resp.text == "ok"
    assert sleeps == [0.5, 1.0, 2.0]


def test_retry_gives_up_after_three_retries():
    sleeps = []
    client = _client([httpx.Response(500)] * 4)
    with pytest.raises(_retry.ApiError, match="after 3 retries"):
        _retry.post_with_retry(client, "https://x.test", sleep=sleeps.append)
    assert sleeps == [0.5, 1.0, 2.0]


def test_retry_does_not_retry_4xx():
    sleeps = []
    client = _client([httpx.Response(401, text="bad key")])
    with pytest.raises(_retry.ApiError) as exc:
        _retry.post_with_retry(client, "https://x.test", sleep=sleeps.append)
    assert exc.value.status_code == 401 and sleeps == []
