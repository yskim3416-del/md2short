"""파일 기반 Job 상태 머신 (docs/architecture.md §3)."""

from __future__ import annotations

import json
import secrets
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SEQUENCE = [
    "created",
    "script_generated",
    "voice_generated",
    "transcribed",
    "subtitled",
    "final_rendered",
]
TERMINAL = {"qc_passed", "qc_failed", "failed"}

_ALLOWED: dict[str, set[str]] = {s: {SEQUENCE[i + 1], "failed"} for i, s in enumerate(SEQUENCE[:-1])}
_ALLOWED["final_rendered"] = {"qc_passed", "qc_failed", "failed"}


def validate_transition(current: str | None, new: str) -> None:
    if current is None:
        if new != "created":
            raise ValueError(f"first status must be 'created', got {new!r}")
        return
    if current in TERMINAL:
        raise ValueError(f"cannot transition from terminal status {current!r} to {new!r}")
    if new not in _ALLOWED.get(current, set()):
        raise ValueError(f"invalid transition {current!r} -> {new!r}")


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def new_job_id(today: datetime | None = None) -> str:
    day = (today or datetime.now()).strftime("%Y%m%d")
    return f"sf_{day}_{secrets.token_hex(3)}"


class JobStatus:
    """`jobs/<job_id>/status.json` 읽기·쓰기. 모든 전이는 validate_transition을 거친다."""

    def __init__(self, job_dir: Path):
        self.path = job_dir / "status.json"

    def read(self) -> dict[str, Any]:
        if not self.path.exists():
            return {}
        return json.loads(self.path.read_text(encoding="utf-8"))

    def write(self, status: str, **fields: Any) -> dict[str, Any]:
        data = self.read()
        validate_transition(data.get("status"), status)
        data.update(fields)
        data["status"] = status
        data["updated_at"] = now_iso()
        history = data.setdefault("history", [])
        history.append({"status": status, "at": data["updated_at"]})
        self.path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        return data
