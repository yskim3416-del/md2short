"""단일 job 오케스트레이션 (docs/architecture.md §2.1)."""

from __future__ import annotations

import json
import shutil
from datetime import date, datetime
from pathlib import Path
from typing import Callable

import httpx

from md2short import audio_post, caption_plan, data_extract, emoticon_map, opening, render, script_engine, storyboard, transcript, voice
from md2short.numeric_display import align_display_words
from md2short.qc import estimate_cost, run_qc
from md2short.schema import CTA_TEXT, JobConfig, WordsDoc
from md2short.state import JobStatus, new_job_id, now_iso
from md2short.timeutil import ms_to_frames
from md2short.tts_text import prepare_tts_text

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_OUTPUT_COPY = Path("output/ret.mp4")
JOB_SUBDIRS = ("inputs", "audio", "transcripts", "edit", "logs", "thumbs")


def _dump(path: Path, data) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _cut_breaks(cuts: list[storyboard.Cut], src: list[int | None], token_offset: int) -> tuple[set[int], list[int]]:
    """(컷 경계 word index 집합, word별 컷 번호). 대본 토큰 index → 컷 번호로 환산한다.

    token_offset: 컷 앞에 붙은 오프닝 문구의 토큰 수 (오프닝 토큰은 0번 컷으로 취급).
    """
    token_cut: list[int] = [0] * token_offset
    for ci, cut in enumerate(cuts):
        token_cut.extend([ci] * len(cut.caption.split()))
    word_cut: list[int] = []
    current = 0
    for s in src:
        if s is not None and s < len(token_cut):
            current = token_cut[s]
        word_cut.append(current)
    breaks = {i for i in range(len(word_cut) - 1) if word_cut[i] != word_cut[i + 1]}
    return breaks, word_cut


def _find_bgm(root: Path) -> str:
    """`bgm/`의 첫 오디오 파일(이름순). 없으면 "" → BGM 없이 렌더."""
    files = sorted(p for p in (root / "bgm").glob("*") if p.suffix.lower() in (".mp3", ".wav", ".m4a"))
    return f"bgm/{files[0].name}" if files else ""


def run_job(
    markdown_path: Path,
    config: JobConfig,
    *,
    elevenlabs_key: str,
    openai_key: str | None,
    jobs_root: Path = Path("jobs"),
    output_copy: Path | None = DEFAULT_OUTPUT_COPY,
    root: Path = PROJECT_ROOT,
    http_client: httpx.Client | None = None,
    today: date | None = None,
    on_stage: Callable[[str], None] = lambda _s: None,
) -> tuple[str, Path]:
    """반환: (job_id, job_dir). QC 실패도 정상 반환(status=qc_failed), 예외는 status=failed 후 재발생."""
    if config.visual_mode != "emoticon":
        raise NotImplementedError("visual_mode=photo is deferred (not implemented in this build)")
    render.ensure_ffmpeg_available()
    render.ensure_remotion_available(root)

    today = today or date.today()
    job_id = new_job_id(datetime.combine(today, datetime.min.time()))
    job_dir = jobs_root / job_id
    for sub in JOB_SUBDIRS:
        (job_dir / sub).mkdir(parents=True, exist_ok=True)
    status = JobStatus(job_dir)
    status.write(
        "created",
        job_id=job_id,
        config=config.model_dump(),
        started_at=now_iso(),
        markdown_input=str(markdown_path.resolve()),
        engine=config.engine,
    )
    on_stage("created")

    client = http_client or httpx.Client()
    try:
        return job_id, _run_stages(markdown_path, config, job_id, job_dir, status, client,
                                   elevenlabs_key, openai_key, output_copy, root, today, on_stage)
    except BaseException as exc:
        status.write("failed", error=f"{type(exc).__name__}: {exc}"[:2000])
        on_stage("failed")
        raise
    finally:
        if http_client is None:
            client.close()


def _run_stages(markdown_path, config, job_id, job_dir, status, client, elevenlabs_key, openai_key,
                output_copy, root, today, on_stage) -> Path:
    logs = job_dir / "logs"
    md = markdown_path.read_text(encoding="utf-8")
    (job_dir / "inputs" / "source.md").write_text(md, encoding="utf-8")

    # [1] script
    cuts: list[storyboard.Cut] = []
    if storyboard.is_storyboard(md):
        cuts = storyboard.parse_storyboard(md)
        _dump(job_dir / "inputs" / "storyboard.json", [c.to_dict() for c in cuts])
        script = {"hook": "", "body": storyboard.narration(cuts), "cta": ""}
        plan = {"engine": "storyboard" if cuts else "empty"}
    else:
        script, plan = script_engine.generate_script(
            md, api_key=openai_key, model=config.model, client=client, raw_log=logs / "openai_raw.json"
        )
        if plan["engine"] != "openai" and openai_key:
            _dump(logs / "fallback.json", {"reason": plan.get("fallback_reason"), "at": now_iso()})
    spoken_opening = opening.spoken_opening(today) if config.show_opening else ""
    narration_parts = [spoken_opening, script["hook"], script["body"], script["cta"]]
    full_text = "\n".join(p.strip() for p in narration_parts if p and p.strip())
    if not (script["hook"] + script["body"]).strip():
        raise ValueError("markdown produced an empty narration script")
    (job_dir / "inputs" / "script.md").write_text(full_text + "\n", encoding="utf-8")
    script_meta = {
        **script,
        "full_text": full_text,
        "plan": plan,
        "opening": {"show": config.show_opening, "spoken": spoken_opening, "visual": opening.opening_visual_text(today)},
        "outro": {"show": config.show_outro, "cta_text": CTA_TEXT[config.language]},
    }
    _dump(job_dir / "inputs" / "script.json", script_meta)
    status.write("script_generated", script_chars=len(full_text))
    on_stage("script_generated")

    # [2] TTS
    tts_text = prepare_tts_text(full_text)
    (logs / "tts_input.txt").write_text(tts_text, encoding="utf-8")
    narration = job_dir / "audio" / "narration.mp3"
    raw_audio = job_dir / "audio" / "narration_raw.mp3" if config.audio_post else narration
    voice.synthesize(
        tts_text, voice_id=config.voice_id, speed=config.voice_speed, api_key=elevenlabs_key,
        out_path=raw_audio, client=client,
    )
    script_meta["tts"] = {"chars": len(tts_text), "voice_id": config.voice_id, "speed": config.voice_speed}
    if config.audio_post:
        script_meta["tts"]["postprocess"] = audio_post.postprocess(raw_audio, narration)
    _dump(job_dir / "inputs" / "script.json", script_meta)
    status.write("voice_generated")
    on_stage("voice_generated")

    # [3] Scribe → [4] 표시 텍스트 정렬 (timing 불변)
    audio_ms = render.get_audio_duration_ms(narration)
    raw_doc = transcript.transcribe(
        narration, api_key=elevenlabs_key, audio_duration_ms=audio_ms, client=client, raw_log=logs / "scribe_raw.json",
    )
    words, src = align_display_words(full_text, raw_doc.words)
    doc = WordsDoc(language_code=raw_doc.language_code, audio_duration_ms=audio_ms, text=raw_doc.text, words=words)
    words_json = job_dir / "transcripts" / "words.json"
    _dump(words_json, doc.model_dump())
    status.write("transcribed")
    on_stage("transcribed")

    # [5] cue planning (모두 words.json 기반)
    opening_ms = opening.opening_duration_ms(words) if config.show_opening else 0
    breaks, word_cut = _cut_breaks(cuts, src, len(spoken_opening.split())) if cuts else (set(), [])
    segments = caption_plan.build_caption_segments(words, config.chunk_size, opening_ms, breaks)
    hints = [cuts[word_cut[s["wordStart"]]].direction for s in segments] if cuts else None
    emoticon_cues = emoticon_map.plan_cues(
        segments, audio_ms, hints, start_ms=0 if config.show_opening else None, closing_text=script["cta"],
    )
    number_cards = data_extract.plan_number_cards(words, opening_ms)
    logo_cues = emoticon_map.plan_company_logo_cues(words, root / "company", opening_ms)
    edit = job_dir / "edit"
    _dump(edit / "caption_segments.json", segments)
    _dump(edit / "emoticon_cues.json", emoticon_cues)
    if number_cards:
        _dump(edit / "number_cards.json", number_cards)
    if logo_cues:
        _dump(edit / "company_logo_cues.json", logo_cues)
    if cuts:
        _dump(edit / "storyboard_segments.json", [
            {"cut": cuts[word_cut[s["wordStart"]]].index, **s} for s in segments
        ])
    status.write("subtitled")
    on_stage("subtitled")

    # [6] render
    keywords = emoticon_map.highlight_keywords(segments)
    props = {
        "audioFileName": f"jobs/{job_id}/narration.mp3",
        "wordsFileName": f"jobs/{job_id}/words.json",
        "bgColor": config.bg_css,
        "chunkSize": config.chunk_size,
        "headerLogoFileName": "img/header_logo.png",
        "emoticonCues": emoticon_cues,
        "captionSegments": segments,
        "companyLogoCues": logo_cues,
        "numberCards": number_cards,
        "highlightKeywords": keywords,
        "keywordTones": emoticon_map.keyword_tones(keywords),
        "bgmFileName": _find_bgm(root),
        "openingText": opening.opening_visual_text(today),
        "openingDurationMs": opening_ms,
        "showOpening": config.show_opening,
        "ctaText": CTA_TEXT[config.language],
        "showOutro": config.show_outro,
        "durationInFrames": ms_to_frames(audio_ms),
    }
    _dump(edit / "props.json", props)  # job 폴더만으로 재현 가능하도록 staging과 별도 보관
    render.stage_shared_assets(root)
    render.stage_job(root, job_id, narration, words_json, props)
    final = render.render_remotion(root, job_id, edit / "final.mp4", logs / "remotion.log")
    status.write("final_rendered")
    on_stage("final_rendered")

    # [7] output copy → [8] QC
    if output_copy:
        output_copy.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(final, output_copy)
    report = run_qc(
        audio_ms=audio_ms,
        last_word_end_ms=words[-1].end,
        final_mp4_ms=render.get_audio_duration_ms(final),
        cost=estimate_cost(len(tts_text), audio_ms, plan.get("usage", {}).get("input_tokens", 0), plan.get("usage", {}).get("output_tokens", 0)),
    )
    report.update({"job_id": job_id, "output_copy": str(output_copy) if output_copy else None, "script_engine": plan["engine"]})
    _dump(job_dir / "qc_report.json", report)
    final_status = "qc_passed" if report["passed"] else "qc_failed"
    status.write(final_status, qc_report=str(job_dir / "qc_report.json"), qc_passed=report["passed"])
    on_stage(final_status)
    return job_dir
