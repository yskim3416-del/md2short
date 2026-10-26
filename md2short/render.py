"""Remotion staging/props/render subprocess + ffprobe duration (docs/architecture.md §5.5).

ffmpeg/ffprobe는 길이 측정·QC 보조용이다. 자막·오버레이 합성은 Remotion만 한다.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path

COMPOSITION_ID = "TechExplainer"
SHARED_ASSET_DIRS = ("emoticon", "img", "company", "bgm")
RENDER_TIMEOUT_S = 60 * 30


class RenderError(RuntimeError):
    pass


def ensure_ffmpeg_available() -> None:
    missing = [b for b in ("ffmpeg", "ffprobe") if shutil.which(b) is None]
    if missing:
        raise RenderError(f"{', '.join(missing)} not found on PATH — install ffmpeg (e.g. `winget install Gyan.FFmpeg`)")


def _npx() -> str:
    npx = shutil.which("npx")
    if npx is None:
        raise RenderError("npx not found on PATH — install Node.js")
    return npx


def ensure_remotion_available(root: Path) -> None:
    remotion = root / "remotion"
    if not (remotion / "package.json").exists():
        raise RenderError(f"{remotion} missing — Remotion project not found")
    if not (remotion / "node_modules").exists():
        raise RenderError(f"{remotion / 'node_modules'} missing — run `npm install` in remotion/")
    _npx()


def get_audio_duration_ms(path: Path) -> int:
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=nw=1:nk=1", str(path)],
        capture_output=True, text=True, check=True,
    ).stdout.strip()
    return round(float(out) * 1000)


def _link_or_copy(src: Path, dst: Path) -> None:
    """remotion/public/<name> → 루트 자산 폴더. Windows에서 symlink 권한이 없으면 복사한다."""
    if dst.is_symlink() or (dst.exists() and dst.resolve() == src.resolve()):
        return
    if not dst.exists():
        try:
            os.symlink(src.resolve(), dst, target_is_directory=True)
            return
        except OSError:
            pass
    shutil.copytree(src, dst, dirs_exist_ok=True)


def stage_shared_assets(root: Path) -> None:
    public = root / "remotion" / "public"
    public.mkdir(parents=True, exist_ok=True)
    for name in SHARED_ASSET_DIRS:
        src = root / name
        src.mkdir(exist_ok=True)
        _link_or_copy(src, public / name)


def stage_job(root: Path, job_id: str, narration: Path, words_json: Path, props: dict) -> Path:
    stage = root / "remotion" / "public" / "jobs" / job_id
    stage.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(narration, stage / "narration.mp3")
    shutil.copyfile(words_json, stage / "words.json")
    props_path = stage / "props.json"
    props_path.write_text(json.dumps(props, ensure_ascii=False, indent=2), encoding="utf-8")
    return props_path


def render_remotion(root: Path, job_id: str, out_path: Path, log_path: Path, timeout_s: int = RENDER_TIMEOUT_S) -> Path:
    remotion = root / "remotion"
    cmd = [
        _npx(), "remotion", "render", "src/index.ts", COMPOSITION_ID, str(out_path.resolve()),
        f"--props=public/jobs/{job_id}/props.json",
        "--codec=h264", "--width=1080", "--height=1920", "--log=warn", "--overwrite",
    ]
    proc = subprocess.run(cmd, cwd=remotion, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=timeout_s)
    log_path.write_text(
        f"$ {' '.join(cmd)}\n\n--- stdout ---\n{proc.stdout}\n--- stderr ---\n{proc.stderr}\nexit={proc.returncode}\n",
        encoding="utf-8",
    )
    if proc.returncode != 0 or not out_path.exists():
        tail = (proc.stderr or proc.stdout)[-800:]
        raise RenderError(f"remotion render failed (exit {proc.returncode}); see {log_path}\n{tail}")
    return out_path
