"""자동 QC + 비용 추정 (docs/architecture.md §5.6)."""

from __future__ import annotations

TAIL_TOLERANCE_MS = 1000
RENDER_TOLERANCE_MS = 100

ELEVENLABS_TTS_USD_PER_1K_CHARS = 0.30
ELEVENLABS_STT_USD_PER_HOUR = 0.40
# OpenAI 텍스트 모델 근사 단가 (USD / 1M tokens). 모델별 가격표가 아니라 상한 근사치다. 토큰 수는 응답 usage 실측값.
OPENAI_TEXT_INPUT_USD_PER_1M = 1.25
OPENAI_TEXT_OUTPUT_USD_PER_1M = 10.0


def estimate_cost(tts_chars: int, audio_ms: int, openai_input_tokens: int, openai_output_tokens: int) -> dict:
    tts = tts_chars / 1000 * ELEVENLABS_TTS_USD_PER_1K_CHARS
    stt = audio_ms / 1000 / 3600 * ELEVENLABS_STT_USD_PER_HOUR
    llm = openai_input_tokens / 1e6 * OPENAI_TEXT_INPUT_USD_PER_1M + openai_output_tokens / 1e6 * OPENAI_TEXT_OUTPUT_USD_PER_1M
    return {
        "elevenlabs_tts_usd": round(tts, 4),
        "elevenlabs_stt_usd": round(stt, 4),
        "openai_text_usd": round(llm, 4),
        "total_usd": round(tts + stt + llm, 4),
        "note": "TTS/STT/텍스트 LLM 근사치. 실제 청구서 기준으로 대조할 것.",
    }


def run_qc(*, audio_ms: int, last_word_end_ms: int, final_mp4_ms: int, cost: dict) -> dict:
    checks = [
        {
            "name": "sync_last_word_vs_audio",
            "audio_ms": audio_ms,
            "last_word_end_ms": last_word_end_ms,
            "delta_ms": audio_ms - last_word_end_ms,
            "tolerance_ms": TAIL_TOLERANCE_MS,
            "passed": abs(audio_ms - last_word_end_ms) <= TAIL_TOLERANCE_MS,
        },
        {
            "name": "final_mp4_vs_audio",
            "audio_ms": audio_ms,
            "final_mp4_ms": final_mp4_ms,
            "delta_ms": final_mp4_ms - audio_ms,
            "tolerance_ms": RENDER_TOLERANCE_MS,
            "passed": abs(final_mp4_ms - audio_ms) <= RENDER_TOLERANCE_MS,
        },
    ]
    return {
        "passed": all(c["passed"] for c in checks),
        "checks": checks,
        "duration_policy": {"source": "tts_audio_duration", "duration_ms": audio_ms},
        "cost_estimate": cost,
    }
