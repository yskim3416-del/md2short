import os

import pytest
from typer.testing import CliRunner

from md2short.cli import app, parse_age

runner = CliRunner()


@pytest.fixture
def md(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)  # .env 미존재 디렉터리
    monkeypatch.delenv("ELEVENLABS_API_KEY", raising=False)
    p = tmp_path / "in.md"
    p.write_text("미국 증시가 상승했습니다.", encoding="utf-8")
    return p


def test_help_lists_commands():
    out = runner.invoke(app, ["--help"]).output
    for cmd in ("run", "status", "clean"):
        assert cmd in out


def test_missing_elevenlabs_key_exit_1(md):
    r = runner.invoke(app, ["run", str(md)])
    assert r.exit_code == 1
    assert "ELEVENLABS_API_KEY" in r.output


@pytest.mark.parametrize("args,needle", [
    (["--visual-mode", "photo"], "not implemented"),
    (["--lang", "en"], "not supported"),
    (["--chunk-size", "30"], "chunk-size"),
    (["--engine", "ffmpeg"], "remotion only"),
])
def test_invalid_args_exit_1(md, monkeypatch, args, needle):
    monkeypatch.setenv("ELEVENLABS_API_KEY", "x")
    r = runner.invoke(app, ["run", str(md), *args])
    assert r.exit_code == 1
    assert needle in r.output


def test_run_exception_exit_2(md, monkeypatch):
    monkeypatch.setenv("ELEVENLABS_API_KEY", "x")

    def boom(*a, **k):
        raise RuntimeError("render exploded")

    monkeypatch.setattr("md2short.pipeline.run_job", boom)
    r = runner.invoke(app, ["run", str(md)])
    assert r.exit_code == 2
    assert "render exploded" in r.output


def test_parse_age():
    assert parse_age("90") == 90
    assert parse_age("30m") == 1800
    assert parse_age("24h") == 86400
    assert parse_age("7d") == 7 * 86400
    with pytest.raises(ValueError):
        parse_age("week")


def test_status_and_clean_dry_run(tmp_path):
    job = tmp_path / "jobs" / "sf_20200101_abcdef"
    job.mkdir(parents=True)
    (job / "status.json").write_text('{"job_id":"sf_20200101_abcdef","status":"qc_passed"}', encoding="utf-8")
    old = 1_000_000_000
    os.utime(job, (old, old))
    r = runner.invoke(app, ["status", "sf_20200101_abcdef", "--jobs-root", str(tmp_path / "jobs")])
    assert r.exit_code == 0 and "qc_passed" in r.output
    r = runner.invoke(app, ["clean", "--older-than", "7d", "--dry-run", "--jobs-root", str(tmp_path / "jobs")])
    assert r.exit_code == 0 and "would delete" in r.output
    assert job.exists()
