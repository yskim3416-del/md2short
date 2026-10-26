"""ms ↔ frame 변환 단일 헬퍼 (AGENTS.md §4.2). Python 쪽 변환은 이 모듈만 사용한다."""

FPS = 30


def ms_to_frames(ms: int | float, fps: int = FPS) -> int:
    return round(ms * fps / 1000)


def frames_to_ms(frames: int, fps: int = FPS) -> int:
    return round(frames * 1000 / fps)
