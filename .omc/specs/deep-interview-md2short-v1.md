# Deep Interview Spec: MD2Short v1 (emoticon mode) 구현

## Metadata
- Interview ID: di-md2short-20261026
- Rounds: 5 (+ Round 0 topology)
- Final Ambiguity Score: 14%
- Type: brownfield (docs-only — 설계 문서 존재, 소스 코드 0줄)
- Generated: 2026-10-26
- Threshold: 0.2
- Threshold Source: default
- Initial Context Summarized: no
- Status: PASSED — pending approval

## Clarity Breakdown
| Dimension | Score | Weight | Weighted |
|-----------|-------|--------|----------|
| Goal Clarity | 0.88 | 0.35 | 0.308 |
| Constraint Clarity | 0.82 | 0.25 | 0.205 |
| Success Criteria | 0.88 | 0.25 | 0.220 |
| Context Clarity | 0.85 | 0.15 | 0.128 |
| **Total Clarity** | | | **0.861** |
| **Ambiguity** | | | **0.139** |

## Topology
| Component | Status | Description | Coverage / Deferral Note |
|-----------|--------|-------------|--------------------------|
| 기반/환경 | active | uv 프로젝트, README, .env 검증, memory/, git init, .gitignore, uv·ffmpeg 설치, Remotion npm install | AC-1, AC-2 |
| 음성·대본 파이프라인 | active | Typer CLI(run/status/clean), JobConfig, 상태 머신, script_engine(OpenAI+fallback), script, tts_text, voice(TTS), transcript(Scribe), _retry | AC-3, AC-5, AC-6 |
| 편집 판단(planner) | active | numeric_display, caption_plan, emoticon_map(60 PNG), data_extract, storyboard(### N컷), opening | AC-3, AC-6 |
| Remotion 합성 | active | TechExplainer(Root, Captions, VisualLayer, NumberCard, BrandHeader, BottomBar, OpeningBriefing, Outro, types) | AC-5, AC-6, AC-7 |
| QC·출력 | active | qc_report.json(sync 2종 + 비용 추정), output/ret.mp4 복사, status/clean 명령 | AC-4, AC-5 |
| Photo mode | deferred | gpt-image-2 실사 이미지 + moderation retry + emoticon fallback | 사용자 확정(2026-10-26): emoticon 경로 우선 완성, photo는 후속 단계. `--visual-mode photo`는 명확한 "미구현" 에러로 거부 |

## Goal
`docs/PRD.md`·`docs/architecture.md`를 구현 기준(SSOT)으로 삼아, 마크다운 1개(일반 또는 `### N컷` 스토리보드)를 `uv run md2short run <file.md>`로 입력하면 한국어 9:16 MP4(`jobs/<job_id>/edit/final.mp4`, `output/ret.mp4`)를 emoticon mode로 생성하는 로컬 Python CLI + Remotion 프로젝트를 처음부터 구현한다.

## Constraints
- AGENTS.md §3 원칙 위반 금지: 레이어 분리(JSON 산출물로만 통신), `words.json` 단일 시간 진실원, 실제 TTS 길이 기준 타임라인, 자막은 Remotion 단독(FFmpeg subtitles/burn-in/overlay 금지).
- ms↔frame 변환은 단일 헬퍼만 사용 (Python 1곳, Remotion 1곳).
- 산출물 경로·Job ID(`sf_YYYYMMDD_<6hex>`)·상태 머신·`status.json`은 architecture.md §3~4 그대로.
- 외부 API 호출: 재시도(429/5xx/timeout 3회, 0.5/1.0/2.0s), 타임아웃, 원본 응답 `logs/` 저장. 키 누락 시 즉시 명확한 에러.
- 시크릿은 `.env`만, git 제외. 환경 변수 prefix `MD2SHORT_*` (API 키 제외).
- **Docs 지위**: 구조·원칙은 엄수. 동작하지 않거나 검증 불가한 세부값(임계값, 사전 항목, 모델명 등)은 작동하는 값으로 바꾸고 **같은 변경에서 docs 갱신**.
- **브랜드 자산**: `img/header_logo.png`는 placeholder 자동 생성, 폰트(SeoulAlrim/SeoulNotice) 없으면 시스템 한글 폰트 fallback, `company/`는 빈 폴더 — 파일을 넣으면 그대로 교체/활성화. 로고 파일 없으면 company logo cue 생략.
- **환경**: 에이전트가 winget으로 uv·ffmpeg 설치, `git init`, `remotion/` npm install, `.gitignore`(.env, jobs/, output/, node_modules, remotion/public/jobs) 수행. 커밋은 사용자 요청 시에만, `docs/commit.md` 양식.
- 플랫폼: Windows 11 (Git Bash/PowerShell) — symlink 실패 시 copy fallback 필수.
- 새 실패는 `memory/_daily/YYYY-MM-DD.md`에 기록 (`docs/memory.md` 규칙).

## Non-Goals
- Photo mode (deferred), 다국어(en/ja), batch/variant, 부분 재렌더링, HTTP API/SaaS, SNS 업로드, BGM, ffmpeg 렌더 엔진.

## Acceptance Criteria
- [ ] AC-1: `uv sync` 성공, `uv run md2short --help`가 run/status/clean 노출. ffmpeg/ffprobe/npx pre-flight 통과.
- [ ] AC-2: README에 설치·.env·실행·테스트 방법 기재; `memory/`(`_template.md`, `_daily/`, `topics/` 5종) 생성; `.gitignore`에 .env 포함.
- [ ] AC-3 (a): 모듈별 pytest 전부 통과 — 외부 API(OpenAI/ElevenLabs)는 mock. 최소: 상태 전이 검증, job_id 포맷, ms↔frame 헬퍼, caption_plan segment, emoticon_map 매칭, data_extract 숫자 추출, numeric_display 복원(S&P500·퍼센트), storyboard 파싱, tts_text 보정, _retry 동작, qc 판정, 키 누락 에러.
- [ ] AC-4: 키 누락/잘못된 인자 → 종료코드 1, 실행 중 예외 → 종료코드 2 + `status.json` = `failed`.
- [ ] AC-5 (b): 실제 API로 `uv run md2short run sample.md` → `jobs/<id>/` 필수 산출물 전부(architecture §3.3) + `output/ret.mp4` + `status=qc_passed` (tail ±1000ms, final vs audio ±100ms).
- [ ] AC-6 (c): `### N컷` 스토리보드 샘플 1개 작성 → 실제 E2E `qc_passed`, `자막` 필드만 내레이션에 포함.
- [ ] AC-7 (d): 두 결과 영상에서 ffmpeg로 프레임 추출 → 자막(최대 2줄, 하단 띠 내), 호랑이 cue, 숫자 카드, 오프닝 박스, 헤더가 깨지지 않고 표시되는지 육안 검수 후 캡처와 함께 보고.
- [ ] AC-8: docs와 달라진 세부값은 docs에 반영되어 있음.

## Assumptions Exposed & Resolved
| Assumption | Challenge | Resolution |
|------------|-----------|------------|
| docs의 6개 기능 영역 모두 이번 범위 | Round 0 topology | Photo mode 연기, 1~5 진행 |
| "완료" = 테스트 통과 | Round 1 | 실제 API E2E + mock 단위 테스트 |
| docs가 참조하는 자산이 존재 | Round 2 (img/, company/, font 부재 확인) | placeholder + 교체 구조 |
| 실행 환경 준비됨 | Round 3 (uv·ffmpeg 미설치, git 미초기화 확인) | 에이전트가 설치·초기화 |
| docs 세부값은 정확 (Contrarian) | Round 4 — 문서는 과거 구현 기록이라 검증 불가 | 구조 엄수, 세부값은 작동값 우선 + docs 갱신 |
| 자동 QC만으로 품질 판정 충분 | Round 5 | 스토리보드 E2E + 프레임 육안 검수 추가 |

## Technical Context
- 존재: `docs/`(PRD v0.6, architecture, voice, memory, commit), `emoticon/` 60 PNG(`NN_키워드_설명.png`), `sample.md`(미국 증시 브리핑), 빈 `.env`.
- 부재: `md2short/`, `remotion/`, `img/`, `company/`, 폰트, 루트 `README.md`, `memory/`, git.
- 환경: Node + npx, Python 3.12 설치됨; uv·ffmpeg·ffprobe 미설치.
- 스택: Python(Typer, Pydantic, httpx, python-dotenv, pytest), Remotion 4.x(1080×1920, 30fps, composition `TechExplainer`), OpenAI Responses API(script, Structured Outputs), ElevenLabs TTS `eleven_multilingual_v2` + Scribe `scribe_v1`, voice `v1jVu1Ky28piIPEJqRrm`.

## Ontology (Key Entities)
| Entity | Type | Fields | Relationships |
|--------|------|--------|---------------|
| Job | core domain | job_id, status, config, started_at | has JobConfig, produces all artifacts |
| JobConfig | core domain | voice_id, speed, chunk_size, bg_color, visual_mode, show_opening/outro | configures Job |
| Script | core domain | hook, body, cta, full_text, plan.engine | derived from source.md / Storyboard |
| WordsDoc (words.json) | core domain | audio_duration_ms, words[start,end,text] | SSOT for all Cue timing |
| Cue | supporting | startMs, durationMs, emoticonFileName / number / caption segment | timed by WordsDoc, consumed via Props |
| Props (props.json) | supporting | audio/words file, cues, opening, durationInFrames | input to Remotion |
| QcReport | supporting | checks, cost estimate, duration_policy | terminal status of Job |
| Asset | supporting | emoticon PNG, header logo, company logo, font | placeholder/override, referenced by Cue/Props |

## Ontology Convergence
| Round | Entity Count | New | Changed | Stable | Stability Ratio |
|-------|-------------|-----|---------|--------|----------------|
| 1 | 7 | 7 | - | - | N/A |
| 2 | 8 | 1 | 0 | 7 | 88% |
| 3 | 8 | 0 | 0 | 8 | 100% |
| 4 | 8 | 0 | 0 | 8 | 100% |
| 5 | 8 | 0 | 0 | 8 | 100% |

## Interview Transcript
<details>
<summary>Full Q&A (Round 0 + 5 rounds)</summary>

### Round 0
**Q:** 6개 컴포넌트(기반, 음성·대본, 편집 판단, Remotion, QC·출력, Photo) 모두 범위?
**A:** 1~5 진행, 6 Photo mode 연기.

### Round 1
**Q:** 완료 기준 = 실제 API 키로 sample.md → ret.mp4 + qc_passed?
**A:** 실제 API E2E (+ mock 단위 테스트).
**Ambiguity:** 30%

### Round 2
**Q:** 없는 브랜드 자산은 placeholder + 교체 구조, 로고 없으면 cue 생략?
**A:** Placeholder + 교체 구조.
**Ambiguity:** 26%

### Round 3
**Q:** 환경 준비(winget uv·ffmpeg, git init, npm install, .gitignore)를 에이전트가?
**A:** 모두 진행.
**Ambiguity:** 23%

### Round 4 (Contrarian)
**Q:** docs는 SSOT, 단 검증 불가 세부값은 작동값으로 바꾸고 docs 갱신?
**A:** Docs 기준 + 불일치 시 docs 갱신.
**Ambiguity:** 17%

### Round 5
**Q:** 수용 기준 (a) pytest mock (b) sample.md E2E (c) 스토리보드 E2E (d) 프레임 육안 검수?
**A:** a~d 전부.
**Ambiguity:** 14%
</details>
