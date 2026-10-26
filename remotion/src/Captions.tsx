import React from 'react';
import {interpolate, useCurrentFrame} from 'remotion';
import {framesToMs, msToFrames} from './time';
import {CaptionSegment, FONT_STACK, Tone, TONE_COLOR, Word} from './types';

const END_PUNCT = ['.', '!', '?', '。', '！', '？', '…'];
const TRAILING_QUOTES = '"\'”’)」』]）';
const GAP_MS = 600;
const GAP_MIN_WORDS = 5;
const MAX_SEGMENT_CHARS = 28;

const endsSentence = (text: string): boolean => {
  let t = text;
  while (t.length > 0 && TRAILING_QUOTES.includes(t[t.length - 1])) {
    t = t.slice(0, -1);
  }
  return END_PUNCT.some((p) => t.endsWith(p));
};

const GOOD_BREAK = /(,|은|는|이|가|을|를|에|에서|로|으로|와|과|고|며|면|서|도|만|이후|이전|동안|때문에)$/;
const BREAK_PENALTY = 10;

// Mirrors Python `_balanced_end`: where to end this chunk of an over-28-char sentence
// (near the equal-split length, preferring words that end with a particle or comma).
const balancedEnd = (words: Word[], start: number): number | undefined => {
  let end = start;
  while (end < words.length - 1 && !endsSentence(words[end].text)) end += 1;
  const join = (from: number, to: number) =>
    words
      .slice(from, to + 1)
      .map((w) => w.text)
      .join(' ').length;
  const total = join(start, end);
  if (total <= MAX_SEGMENT_CHARS) return undefined;
  const target = total / Math.ceil(total / MAX_SEGMENT_CHARS);
  let best: [number, number] | undefined;
  for (let j = start; j < end; j += 1) {
    const prefix = join(start, j);
    if (prefix > MAX_SEGMENT_CHARS) break;
    const cost = Math.abs(prefix - target) + (GOOD_BREAK.test(words[j].text) ? 0 : BREAK_PENALTY);
    if (best === undefined || cost < best[0]) best = [cost, j];
  }
  return best ? best[1] : start;
};

/**
 * Contract caption rule (mirrors Python `caption_plan`).
 * Close chunk after word w if: sentence-ending punctuation, next gap >= 600ms (chunk >= 5 words),
 * chunk length reached chunkSize, or the word is the `balancedEnd` split point of an over-28-char sentence. Words before openingDurationMs are dropped when showOpening.
 */
export const planCaptionSegments = (
  words: Word[],
  opts: {chunkSize: number; showOpening: boolean; openingDurationMs: number},
): CaptionSegment[] => {
  const size = Math.max(1, Math.min(24, Math.floor(opts.chunkSize) || 14));
  const idx: number[] = [];
  words.forEach((w, i) => {
    if (!(opts.showOpening && w.start < opts.openingDurationMs)) idx.push(i);
  });
  const segs: CaptionSegment[] = [];
  let cur: number[] = [];
  let splitAt: number | undefined;
  const close = () => {
    if (cur.length === 0) return;
    const first = cur[0];
    const last = cur[cur.length - 1];
    segs.push({
      startMs: words[first].start,
      endMs: words[last].end,
      wordStart: first,
      wordEnd: last + 1,
    });
    cur = [];
  };
  idx.forEach((wi, k) => {
    const w = words[wi];
    if (cur.length === 0) splitAt = balancedEnd(words, wi);
    cur.push(wi);
    const next = k + 1 < idx.length ? words[idx[k + 1]] : undefined;
    if (
      endsSentence(w.text) ||
      (next !== undefined && next.start - w.end >= GAP_MS && cur.length >= GAP_MIN_WORDS) ||
      cur.length >= size ||
      wi === splitAt
    ) {
      close();
    }
  });
  close();
  return segs;
};

const LINE_WIDTH = 900;
const MAX_FONT = 68;
const MIN_FONT = 34;
const LINE_BREAK_PENALTY = 4; // 글자 폭(1px 폰트 기준) 환산 — 한글 약 4자

const textWidth = (text: string, fs: number): number => {
  let w = 0;
  for (const ch of text) {
    w += ch === ' ' ? fs * 0.3 : ch.charCodeAt(0) < 128 ? fs * 0.58 : fs * 0.98;
  }
  return w;
};

// 한 줄에 안 들어가면 가운데에 가까우면서 조사·쉼표로 끝나는 단어 뒤에서 줄을 바꾼다 (브라우저 임의 줄바꿈 대신).
// 반환: [줄바꿈할 단어 index(-1이면 한 줄), 두 줄 모두 들어가는 최대 폰트].
const layoutLines = (texts: string[]): [number, number] => {
  const full = texts.join(' ');
  if (texts.length < 2 || textWidth(full, MAX_FONT) <= LINE_WIDTH) {
    for (let fs = MAX_FONT; fs > MIN_FONT; fs -= 2) {
      if (textWidth(full, fs) <= LINE_WIDTH) return [-1, fs];
    }
    return [-1, MIN_FONT];
  }
  // 긴 줄이 짧을수록 글자가 커진다: 긴 줄 폭 + (의미 단위가 아닌 곳이면 벌점)
  let best: [number, number] = [Infinity, 0];
  for (let j = 0; j < texts.length - 1; j += 1) {
    const longest = Math.max(textWidth(texts.slice(0, j + 1).join(' '), 1), textWidth(texts.slice(j + 1).join(' '), 1));
    const cost = longest + (GOOD_BREAK.test(texts[j]) ? 0 : LINE_BREAK_PENALTY);
    if (cost < best[0]) best = [cost, j];
  }
  const br = best[1];
  const longest = Math.max(
    textWidth(texts.slice(0, br + 1).join(' '), 1),
    textWidth(texts.slice(br + 1).join(' '), 1),
  );
  const fs = Math.max(MIN_FONT, Math.min(MAX_FONT, Math.floor(LINE_WIDTH / longest / 2) * 2));
  return [br, fs];
};

export const Captions: React.FC<{
  words: Word[];
  captionSegments: CaptionSegment[];
  chunkSize: number;
  highlightKeywords: string[];
  keywordTones?: Record<string, Tone>;
  showOpening: boolean;
  openingDurationMs: number;
}> = ({words, captionSegments, chunkSize, highlightKeywords, keywordTones, showOpening, openingDurationMs}) => {
  const frame = useCurrentFrame();
  const t = framesToMs(frame);

  const segments = React.useMemo(
    () =>
      captionSegments.length > 0
        ? captionSegments
        : planCaptionSegments(words, {chunkSize, showOpening, openingDurationMs}),
    [captionSegments, words, chunkSize, showOpening, openingDurationMs],
  );

  // Segment persists until the next segment starts.
  let active: CaptionSegment | undefined;
  for (const s of segments) {
    if (s.startMs <= t) active = s;
    else break;
  }
  if (!active) return null;

  const chunk = words.slice(active.wordStart, active.wordEnd);
  if (chunk.length === 0) return null;

  const [lineBreak, fontSize] = layoutLines(chunk.map((w) => w.text));
  const kwIndex = chunk.findIndex((w) => highlightKeywords.some((k) => k && w.text.includes(k)));
  const kw = kwIndex >= 0 ? highlightKeywords.find((k) => k && chunk[kwIndex].text.includes(k)) : undefined;
  const kwColor = TONE_COLOR[(kw && keywordTones?.[kw]) || 'neutral'];

  return (
    <div
      style={{
        width: 920,
        maxHeight: 380,
        overflow: 'hidden',
        textAlign: 'center',
        fontFamily: FONT_STACK,
        fontWeight: 700,
        fontSize,
        lineHeight: 1.3,
        color: '#fff',
        wordBreak: 'keep-all',
      }}
    >
      {chunk.map((w, i) => {
        const started = w.start <= t;
        const isActive = started && t < w.end + 100;
        const sinceFrames = frame - msToFrames(w.start);
        const pop = isActive
          ? interpolate(sinceFrames, [0, 3, 8], [1, 1.14, 1.06], {
              extrapolateLeft: 'clamp',
              extrapolateRight: 'clamp',
            })
          : 1;
        return (
          <React.Fragment key={active!.wordStart + i}>
            <span
              style={{
                display: 'inline-block',
                transform: `scale(${pop})`,
                color: i === kwIndex ? kwColor : '#fff',
                opacity: started ? 1 : 0.55,
                textShadow: '0 2px 8px rgba(0,0,0,0.6)',
              }}
            >
              {w.text}
            </span>
            {i === lineBreak ? <br /> : i < chunk.length - 1 ? ' ' : null}
          </React.Fragment>
        );
      })}
    </div>
  );
};
