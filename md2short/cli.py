"""md2short CLI — run / status / clean (docs/architecture.md §6).

종료 코드: 0 성공, 1 입력 검증·필수 env 누락, 2 run_job 실행 중 예외.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import time
from pathlib import Path

import typer
from dotenv import load_dotenv
from pydantic import ValidationError

from md2short.schema import DEFAULT_VOICES, JobConfig

app = typer.Typer(add_completion=False, help="마크다운 → 한국어 9:16 숏폼 MP4")


def _fail(msg: str, code: int = 1) -> None:
    typer.secho(f"error: {msg}", fg=typer.colors.RED, err=True)
    raise typer.Exit(code)


@app.command()
def run(
    markdown_file: Path = typer.Argument(..., help="입력 마크다운 (일반 또는 ### N컷 스토리보드)"),
    lang: str = typer.Option("ko", "--lang", "-l", help="출력 언어 (v1: ko 고정)"),
    voice: str = typer.Option(DEFAULT_VOICES["ko"], "--voice", "-v", help="ElevenLabs voice id"),
    speed: float = typer.Option(1.0, "--speed", help="TTS 속도 0.7~1.2"),
    template: str = typer.Option("tech_explainer", "--template", "-t", help="템플릿 (현재 TechExplainer 1종)"),
    chunk_size: int = typer.Option(14, "--chunk-size", help="자막 segment 최대 단어 수 1~24"),
    bg: str = typer.Option("0xFFFFFF", "--bg", help="가운데 섹션 배경색"),
    jobs_root: Path = typer.Option(Path("jobs"), "--jobs-root", help="job 산출물 루트"),
    engine: str = typer.Option("remotion", "--engine", help="렌더 엔진 (remotion만 지원)"),
    visual_mode: str = typer.Option("emoticon", "--visual-mode", help="emoticon (photo는 미구현)"),
    model: str = typer.Option("gpt-5-mini", "--model", help="OpenAI 대본 생성 모델"),
    no_opening: bool = typer.Option(False, "--no-opening", help="날짜 오프닝 끄기"),
    outro: bool = typer.Option(False, "--outro", help="마지막 구독 CTA overlay 표시"),
    no_audio_post: bool = typer.Option(False, "--no-audio-post", help="TTS 무음 압축·음량 정규화 끄기"),
    output: str = typer.Option("output/ret.mp4", "--output", "-o", help="final MP4 사본 경로, 빈 문자열이면 비활성화"),
) -> None:
    """마크다운 1개로 숏폼 영상 1편을 생성한다."""
    load_dotenv(Path.cwd() / ".env")
    if not markdown_file.is_file():
        _fail(f"markdown file not found: {markdown_file}")
    if lang != "ko":
        _fail(f"--lang {lang!r} is not supported in v1 (Korean only: ko)")
    if engine != "remotion":
        _fail(f"--engine {engine!r} is not supported (remotion only)")
    if visual_mode == "photo":
        _fail("--visual-mode photo is not implemented yet (deferred to a later stage); use emoticon")
    if visual_mode != "emoticon":
        _fail(f"--visual-mode must be emoticon, got {visual_mode!r}")
    if not 1 <= chunk_size <= 24:
        _fail(f"--chunk-size must be 1..24, got {chunk_size}")
    elevenlabs_key = os.environ.get("ELEVENLABS_API_KEY", "").strip()
    if not elevenlabs_key:
        _fail("ELEVENLABS_API_KEY is not set — add it to .env (required for TTS and Scribe)")
    openai_key = os.environ.get("OPENAI_API_KEY", "").strip() or None
    if openai_key is None:
        typer.secho("warning: OPENAI_API_KEY not set — using markdown extract fallback for the script", fg=typer.colors.YELLOW, err=True)
    try:
        config = JobConfig(
            voice_id=voice, voice_speed=speed, template_id=template, bg_color=bg, chunk_size=chunk_size,
            visual_mode=visual_mode, show_opening=not no_opening, show_outro=outro, model=model,
            audio_post=not no_audio_post,
        )
    except ValidationError as exc:
        _fail(str(exc))

    from md2short.pipeline import run_job  # 무거운 import는 검증 통과 후

    try:
        job_id, job_dir = run_job(
            markdown_file, config, elevenlabs_key=elevenlabs_key, openai_key=openai_key,
            jobs_root=jobs_root, output_copy=Path(output) if output else None,
            on_stage=lambda s: typer.echo(f"[stage] {s}"),
        )
    except Exception as exc:  # noqa: BLE001 — 모든 실행 예외는 exit 2
        _fail(f"job failed: {type(exc).__name__}: {exc}", code=2)
    data = json.loads((job_dir / "status.json").read_text(encoding="utf-8"))
    typer.echo(f"job_id: {job_id}\nstatus: {data['status']}\nfinal: {job_dir / 'edit' / 'final.mp4'}")
    if output:
        typer.echo(f"output: {output}")


@app.command()
def status(job_id: str, jobs_root: Path = typer.Option(Path("jobs"), "--jobs-root")) -> None:
    """status.json + qc_report.json 요약."""
    job_dir = jobs_root / job_id
    path = job_dir / "status.json"
    if not path.exists():
        _fail(f"job not found: {path}")
    data = json.loads(path.read_text(encoding="utf-8"))
    for key in ("job_id", "status", "started_at", "updated_at", "script_chars", "error"):
        if key in data:
            typer.echo(f"{key}: {data[key]}")
    qc_path = job_dir / "qc_report.json"
    if qc_path.exists():
        qc = json.loads(qc_path.read_text(encoding="utf-8"))
        for c in qc["checks"]:
            typer.echo(f"  [{'PASS' if c['passed'] else 'FAIL'}] {c['name']} delta={c['delta_ms']}ms (±{c['tolerance_ms']})")
        typer.echo(f"  cost_estimate_usd: {qc['cost_estimate']['total_usd']}")


def parse_age(value: str) -> float:
    m = re.fullmatch(r"(\d+(?:\.\d+)?)([smhd]?)", value.strip())
    if not m:
        raise ValueError(f"invalid duration {value!r} (use e.g. 3600, 30m, 24h, 7d)")
    return float(m.group(1)) * {"": 1, "s": 1, "m": 60, "h": 3600, "d": 86400}[m.group(2)]


@app.command()
def clean(
    older_than: str = typer.Option(..., "--older-than", help="예: 24h, 7d, 3600"),
    dry_run: bool = typer.Option(False, "--dry-run"),
    jobs_root: Path = typer.Option(Path("jobs"), "--jobs-root"),
) -> None:
    """오래된 job 디렉터리를 삭제한다."""
    try:
        age_s = parse_age(older_than)
    except ValueError as exc:
        _fail(str(exc))
    if not jobs_root.is_dir():
        typer.echo("no jobs")
        return
    cutoff = time.time() - age_s
    staging = Path(__file__).resolve().parent.parent / "remotion" / "public" / "jobs"
    for job_dir in sorted(p for p in jobs_root.iterdir() if p.is_dir() and p.name.startswith("sf_")):
        if job_dir.stat().st_mtime >= cutoff:
            continue
        typer.echo(f"{'would delete' if dry_run else 'delete'}: {job_dir}")
        if not dry_run:
            shutil.rmtree(job_dir)
            shutil.rmtree(staging / job_dir.name, ignore_errors=True)


if __name__ == "__main__":
    app()
