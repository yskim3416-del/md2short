# MD2Short

마크다운 1개 → 한국어 9:16 숏폼 MP4. ElevenLabs(TTS + Scribe) 음성 타이밍을 기준으로 Remotion이 자막·호랑이 이미지·숫자 카드를 합성한다.

- 제품 요구사항: [`docs/PRD.md`](docs/PRD.md) · 설계: [`docs/architecture.md`](docs/architecture.md) · 작업 원칙: [`AGENTS.md`](AGENTS.md)
- v1 범위: 한국어, emoticon(호랑이) 비주얼 모드. photo 모드는 아직 구현되지 않았다 (`--visual-mode photo`는 에러).

## 1. 설치 (Windows 기준)

필요: Python 3.12+, [uv](https://docs.astral.sh/uv/), Node.js 20+ (npx), ffmpeg/ffprobe.

```powershell
winget install astral-sh.uv
winget install Gyan.FFmpeg
winget install OpenJS.NodeJS.LTS
# 설치 후 새 터미널을 열어야 PATH가 갱신된다
```

```bash
uv sync                       # Python 의존성
cd remotion && npm install    # Remotion 의존성
```

## 2. API 키 (`.env`)

프로젝트 루트의 `.env`에 넣는다. git에는 절대 커밋하지 않는다 (`.gitignore`에 포함).

```dotenv
ELEVENLABS_API_KEY=...   # 필수 — TTS + Scribe
OPENAI_API_KEY=...       # 권장 — 대본 생성. 없으면 마크다운 원문 추출 fallback
```

> **무료 플랜 주의**: 기본 voice(`v1jVu1Ky28piIPEJqRrm`, Voice Library 음성)는 ElevenLabs 유료 플랜(Creator 이상) 또는 구매 크레딧이 있어야 API로 쓸 수 있다. 무료 플랜이면 `HTTP 402 paid_plan_required`로 실패하므로 premade 음성을 지정한다:
> `uv run md2short run sample.md --voice onwK4e9ZLuTAKqWW03F9` (Daniel, 방송 톤). API 키 권한은 Text to Speech · Speech to Text 접근이 필요하다.

## 3. 실행

```bash
uv run md2short run sample.md
```

결과:

| 경로 | 내용 |
| --- | --- |
| `output/ret.mp4` | 최종 영상 사본 (`-o` 로 변경, `-o ""` 로 끔) |
| `jobs/<job_id>/edit/final.mp4` | Remotion 렌더 원본 |
| `jobs/<job_id>/status.json` | 상태 전이 기록 |
| `jobs/<job_id>/qc_report.json` | QC 결과 + 비용 추정 |
| `jobs/<job_id>/logs/` | TTS 입력, Scribe/OpenAI 원본 응답, Remotion 로그 |

주요 옵션 (`uv run md2short run --help`):

| 옵션 | 기본값 | 설명 |
| --- | --- | --- |
| `--voice` | `v1jVu1Ky28piIPEJqRrm` | ElevenLabs voice id |
| `--speed` | `1.0` | TTS 속도 0.7~1.2 |
| `--bg` | `0xFFFFFF` | 가운데 섹션 배경색 |
| `--chunk-size` | `14` | 자막 segment 최대 단어 수 (1~24) |
| `--model` | `gpt-5-mini` | OpenAI 대본 생성 모델 |
| `--no-opening` | off | "M월 D일 데이브리핑" 오프닝 끄기 |
| `--outro` | off | 마지막 구독 CTA overlay |
| `--no-audio-post` | off | TTS 무음 압축(0.35s↑ → 0.24s)·음량 정규화(-14 LUFS) 끄기 |
| `--jobs-root` | `jobs` | job 산출물 루트 |

### 스토리보드 입력

`### N컷` 형식이면 OpenAI를 거치지 않고 `자막`만 내레이션으로 쓴다. `화면 연출`은 호랑이 이미지 선택 힌트로만 쓰인다.

```markdown
### 1컷
- 자막: 미국 증시가 5주 연속 상승했습니다.
- 화면 연출: 호랑이가 로켓을 타고 상승
### 2컷
- 자막: 로블록스는 18% 급락했습니다.
- 화면 연출: 패닉
```

예시: [`samples/storyboard.md`](samples/storyboard.md)

### Job 관리

```bash
uv run md2short status <job_id>
uv run md2short clean --older-than 7d --dry-run
uv run md2short clean --older-than 24h
```

종료 코드: `0` 성공 · `1` 입력 검증/키 누락 · `2` 실행 중 예외 (`status.json` = `failed`).

## 4. 브랜드 자산 교체

| 경로 | 기본 | 교체 방법 |
| --- | --- | --- |
| `img/header_logo.png` | "타이거살구브리핑" 로고 (976×255, 투명 배경) | 같은 이름의 PNG로 덮어쓰기 (권장 600×220, 투명 배경) |
| `font/` | 시스템 한글 폰트(맑은 고딕) | `font/README.md` 참고, SeoulNotice/SeoulAlrim 파일 추가 |
| `company/` | 비어 있음 → 로고 cue 없음 | `company/<회사명>.png` 추가 시 대본에 그 회사명이 나오면 로고 표시 (예: `company/애플.png`) |
| `bgm/` | 비어 있음 → BGM 없음 | 오디오 파일 1개(`.mp3`/`.wav`/`.m4a`) 추가 시 내레이션 아래 낮은 볼륨으로 반복 재생 (사용 권한 있는 음원만) |
| `emoticon/` | 호랑이 PNG 60종 | 키워드 매핑은 `md2short/emoticon_map.py` |

## 5. 테스트

```bash
uv run pytest -q                 # 전체 (오프라인 E2E 렌더 포함, 외부 API는 mock)
uv run pytest -q -m "not render" # 렌더 제외 빠른 단위 테스트
bash remotion/scripts/render-fixture.sh   # Remotion 단독 fixture 렌더
```

## 6. 실패 기록

새로 겪은 실패는 `memory/_daily/YYYY-MM-DD.md`에 기록한다. 규칙: [`docs/memory.md`](docs/memory.md).
