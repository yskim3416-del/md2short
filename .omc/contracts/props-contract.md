# props.json contract (Python md2short.render ↔ Remotion TechExplainer)

Staged at `remotion/public/jobs/<job_id>/props.json`. All times are integer **ms**; Remotion converts with its single `msToFrames` helper (`remotion/src/time.ts`, fps=30, `Math.round(ms * fps / 1000)`).

```jsonc
{
  "audioFileName": "jobs/<job_id>/narration.mp3",      // staticFile() path
  "wordsFileName": "jobs/<job_id>/words.json",         // staticFile() path, WordsDoc below
  "bgColor": "#FFFFFF",
  "chunkSize": 14,                                      // 1..24 caption safety cap
  "headerLogoFileName": "img/header_logo.png",
  "emoticonCues": [
    {"startMs": 2800, "durationMs": 3100, "emoticonFileName": "emoticon/09_가즈아_상승.png",
     "keyword": "상승", "assetKind": "emoticon", "visualMode": "emoticon"}
  ],
  "captionSegments": [
    {"startMs": 2800, "endMs": 5200, "wordStart": 3, "wordEnd": 8}   // word index range [wordStart, wordEnd) into words[]
  ],
  "companyLogoCues": [
    {"startMs": 9000, "durationMs": 2000, "logoFileName": "company/apple.png", "name": "애플"}
  ],
  "numberCards": [
    {"startMs": 6100, "durationMs": 1800, "text": "7,230", "label": "S&P 500", "tone": "neutral"}
  ],
  "highlightKeywords": ["상승", "급락"],
  "keywordTones": {"상승": "up", "급락": "down"},
  "bgmFileName": "",
  "openingText": "26년 10월 26일\n데이브리핑",
  "openingDurationMs": 2800,
  "showOpening": true,
  "ctaText": "구독과 알림 설정 부탁드립니다",
  "showOutro": false,
  "durationInFrames": 900
}
```

WordsDoc (`words.json`): `{"language_code":"kor","audio_duration_ms":30000,"text":"...","words":[{"text":"금일","start":0,"end":320}]}` — `start`/`end` int ms. Word `text` is already display-corrected (numeric_display); never re-time.

## Caption rule (identical in Python `caption_plan` and Remotion `Captions.tsx` fallback)
1. Candidate words = all words; if `showOpening`, drop words with `start < openingDurationMs`.
2. Walk words in order, appending to current chunk. Close the chunk **after** word *w* when any holds:
   - `w.text` ends with one of `. ! ? 。 ！ ？ …` (ignoring trailing quotes/brackets `"'”’)」』`)
   - next word exists and `next.start - w.end >= 600` and the open chunk already has >= 5 words
   - chunk length reached `chunkSize`
   - the text from the chunk's first word to its sentence end (`total`) is longer than 28 chars and *w* is the split point: among words whose chunk prefix is ≤ 28 chars, minimize `|prefix - total/ceil(total/28)| + (0 if w ends with a comma or particle 은|는|이|가|을|를|에|에서|로|으로|와|과|고|며|면|서|도|만|이후|이전|동안|때문에 else 10)`
3. Segment `startMs` = first word start, `endMs` = last word end; display persists until next segment start (or audio end).
4. If `captionSegments` is non-empty, Remotion uses it verbatim instead of recomputing.

## Layout (1080×1920)
- BrandHeader: top 470px black band (250px safe margin + 220px logo area), logo centered from the first frame.
- Badge strip y 470..630 (`bgColor`): DateBadge (`openingText` on one line) for the whole video when `showOpening`; NumberCard covers it while active (1.8s pop-in + tilt, number color by `tone`: up red, down blue).
- Image area y 630..1400 (`bgColor`): VisualLayer (emoticon contain, enter pop + zoom 1.0→1.1 + ±8px bob), company logo small badge.
- BottomBar: bottom 520px black band (y 1400..1920); captions sit near its top (30px padding), max 2 lines with an explicit break chosen to minimize the longer line (penalty for breaking after a word that does not end with a comma/particle), white text, active word pop scale, ≤1 highlight keyword per chunk colored by `keywordTones` (up red, down blue, else yellow).
- Optional BGM: `bgmFileName` non-empty → looped `<Audio>` at volume 0.08.
- Outro: only when `showOutro`, last 2600ms full-screen CTA.
- Fonts: `staticFile("font/font.css")`; family stack `'SeoulNotice','SeoulAlrim','Malgun Gothic','Apple SD Gothic Neo','Noto Sans KR',sans-serif`.
