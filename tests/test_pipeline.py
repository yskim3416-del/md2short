"""오프라인 E2E: OpenAI/ElevenLabs는 MockTransport, Remotion 렌더는 실제로 수행한다."""

import json
import re
from datetime import date

import pytest
from conftest import ROOT, FakeApis, render_available

from md2short import pipeline
from md2short.schema import JobConfig

pytestmark = pytest.mark.render

REQUIRED = [
    "status.json", "qc_report.json",
    "inputs/source.md", "inputs/script.md", "inputs/script.json",
    "audio/narration.mp3", "audio/narration_raw.mp3", "logs/tts_input.txt",
    "transcripts/words.json", "logs/scribe_raw.json",
    "edit/caption_segments.json", "edit/emoticon_cues.json",
    "edit/final.mp4", "logs/remotion.log",
]


@pytest.fixture
def need_render():
    if not render_available():
        pytest.skip("ffmpeg / remotion node_modules not available")


def _run(tmp_path, md_text, apis, openai_key=None, output=True):
    md = tmp_path / "in.md"
    md.write_text(md_text, encoding="utf-8")
    out = tmp_path / "output" / "ret.mp4" if output else None
    job_id, job_dir = pipeline.run_job(
        md, JobConfig(), elevenlabs_key="ek", openai_key=openai_key,
        jobs_root=tmp_path / "jobs", output_copy=out, http_client=apis.client(), today=date(2026, 10, 26),
    )
    return job_id, job_dir, out


def test_offline_e2e_markdown(tmp_path, need_render):
    apis = FakeApis(tmp_path, openai_script={
        "hook": "미국 증시가 5주 연속 상승했습니다.",
        "body": "S&P 500 종가 7,230 기록했습니다.\n로블록스는 18% 급락했습니다.",
        "cta": "내일도 핵심만 전해드리겠습니다.",
    })
    job_id, job_dir, out = _run(tmp_path, "# 증시\n- 상승", apis, openai_key="ok")
    assert re.fullmatch(r"sf_20261026_[0-9a-f]{6}", job_id)
    for rel in REQUIRED:
        assert (job_dir / rel).exists(), rel
    assert (ROOT / "remotion" / "public" / "jobs" / job_id / "props.json").exists()
    assert (job_dir / "edit" / "props.json").exists()  # staging 정리 후에도 job 폴더로 재현 가능
    assert out.exists()

    status = json.loads((job_dir / "status.json").read_text(encoding="utf-8"))
    assert status["status"] == "qc_passed"
    assert [h["status"] for h in status["history"]] == [
        "created", "script_generated", "voice_generated", "transcribed", "subtitled", "final_rendered", "qc_passed"]
    qc = json.loads((job_dir / "qc_report.json").read_text(encoding="utf-8"))
    assert qc["passed"] and {c["name"] for c in qc["checks"]} == {"sync_last_word_vs_audio", "final_mp4_vs_audio"}
    assert qc["duration_policy"]["source"] == "tts_audio_duration"

    words = json.loads((job_dir / "transcripts" / "words.json").read_text(encoding="utf-8"))["words"]
    texts = [w["text"] for w in words]
    assert "7,230" in texts and "18%" in texts  # 표시형 복원
    props = json.loads((ROOT / "remotion" / "public" / "jobs" / job_id / "props.json").read_text(encoding="utf-8"))
    assert props["openingText"] == "26년 10월 26일\n데이브리핑" and props["openingDurationMs"] > 0
    assert props["captionSegments"][0]["startMs"] >= props["openingDurationMs"]
    assert any(c["text"] == "7,230" for c in props["numberCards"])
    tts = (job_dir / "logs" / "tts_input.txt").read_text(encoding="utf-8")
    assert "칠천이백삼십" in tts


def test_offline_e2e_storyboard(tmp_path, need_render):
    sb = "### 1컷\n자막: 미국 증시가 올랐습니다.\n화면 연출: 로켓 급등\n### 2컷\n자막: 로블록스는 18% 급락했습니다.\n화면 연출: 패닉\n"
    apis = FakeApis(tmp_path)
    _, job_dir, _ = _run(tmp_path, sb, apis, output=False)
    assert not any("openai" in c for c in apis.calls)
    script = (job_dir / "inputs" / "script.md").read_text(encoding="utf-8")
    assert "화면" not in script and "로켓" not in script
    segs = json.loads((job_dir / "edit" / "storyboard_segments.json").read_text(encoding="utf-8"))
    assert [s["cut"] for s in segs] == [1, 2]
    cues = json.loads((job_dir / "edit" / "emoticon_cues.json").read_text(encoding="utf-8"))
    assert cues[0]["emoticonFileName"].endswith("26_반도체급등_로켓상승.png")
    assert cues[1]["emoticonFileName"].endswith("28_폭락_패닉하락.png")
    assert json.loads((job_dir / "status.json").read_text(encoding="utf-8"))["status"] == "qc_passed"


def test_render_fails_when_words_json_missing(tmp_path, need_render):
    """words.json 로드 실패 시 자막 없는 영상이 나오지 않고 렌더가 실패해야 한다 (cancelRender)."""
    from conftest import make_mp3

    from md2short import render

    job_id = "sf_test_missing_words"
    mp3 = tmp_path / "n.mp3"
    make_mp3(mp3, 1.0)
    words = tmp_path / "w.json"
    words.write_text('{"audio_duration_ms":1000,"words":[]}', encoding="utf-8")
    props = {
        "audioFileName": f"jobs/{job_id}/narration.mp3", "wordsFileName": f"jobs/{job_id}/does_not_exist.json",
        "bgColor": "#FFFFFF", "chunkSize": 14, "headerLogoFileName": "img/header_logo.png",
        "emoticonCues": [], "captionSegments": [], "companyLogoCues": [], "numberCards": [], "highlightKeywords": [],
        "openingText": "", "openingDurationMs": 0, "showOpening": False, "ctaText": "", "showOutro": False,
        "durationInFrames": 30,
    }
    render.stage_shared_assets(ROOT)
    render.stage_job(ROOT, job_id, mp3, words, props)
    try:
        with pytest.raises(render.RenderError):
            render.render_remotion(ROOT, job_id, tmp_path / "out.mp4", tmp_path / "remotion.log")
    finally:
        import shutil
        shutil.rmtree(ROOT / "remotion" / "public" / "jobs" / job_id, ignore_errors=True)


def test_failure_marks_status_failed(tmp_path, need_render, monkeypatch):
    apis = FakeApis(tmp_path)

    def boom(*a, **k):
        raise RuntimeError("tts down")

    monkeypatch.setattr(pipeline.voice, "synthesize", boom)
    with pytest.raises(RuntimeError, match="tts down"):
        _run(tmp_path, "증시가 올랐습니다.", apis)
    job_dir = next((tmp_path / "jobs").iterdir())
    status = json.loads((job_dir / "status.json").read_text(encoding="utf-8"))
    assert status["status"] == "failed" and "tts down" in status["error"]


def test_audio_post_compresses_long_silence(tmp_path, need_render):
    import subprocess

    from md2short import audio_post, render

    src = tmp_path / "raw.mp3"
    subprocess.run(
        ["ffmpeg", "-y", "-loglevel", "error",
         "-f", "lavfi", "-i", "sine=frequency=330:duration=1", "-f", "lavfi", "-i", "anullsrc=r=44100:cl=mono:d=1",
         "-f", "lavfi", "-i", "sine=frequency=330:duration=1",
         "-filter_complex", "[0][1][2]concat=n=3:v=0:a=1", "-ar", "44100", "-b:a", "128k", str(src)],
        check=True,
    )
    info = audio_post.postprocess(src, tmp_path / "out.mp3")
    assert info["cuts"] == 1 and 0.55 < info["removed_s"] < 0.65
    assert 2300 < render.get_audio_duration_ms(tmp_path / "out.mp3") < 2500  # 문장 끝급 1s 쉼 → 0.4s
