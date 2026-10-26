export type Tone = 'up' | 'down' | 'neutral';

export type Word = {text: string; start: number; end: number};

export type WordsDoc = {
  language_code?: string;
  audio_duration_ms?: number;
  text?: string;
  words: Word[];
};

export type EmoticonCue = {
  startMs: number;
  durationMs: number;
  emoticonFileName: string;
  keyword?: string;
  assetKind?: 'emoticon' | 'photo';
  visualMode?: 'emoticon' | 'photo';
};

export type CaptionSegment = {
  startMs: number;
  endMs: number;
  wordStart: number;
  wordEnd: number;
};

export type CompanyLogoCue = {
  startMs: number;
  durationMs: number;
  logoFileName: string;
  name?: string;
};

export type NumberCardCue = {
  startMs: number;
  durationMs: number;
  text: string;
  label?: string;
  tone?: Tone;
};

export type CueProps = {
  audioFileName: string;
  wordsFileName: string;
  bgColor: string;
  chunkSize: number;
  headerLogoFileName: string;
  emoticonCues: EmoticonCue[];
  captionSegments: CaptionSegment[];
  companyLogoCues: CompanyLogoCue[];
  numberCards: NumberCardCue[];
  highlightKeywords: string[];
  keywordTones?: Record<string, Tone>;
  bgmFileName?: string;
  openingText: string;
  openingDurationMs: number;
  showOpening: boolean;
  ctaText: string;
  showOutro: boolean;
  durationInFrames: number;
};

export const LAYOUT = {
  width: 1080,
  height: 1920,
  headerHeight: 470,
  bottomHeight: 520,
  // header 안 logo 슬롯 (250px safe margin 아래 220px) — 로고 전용
  slotTop: 250,
  slotHeight: 220,
  // header 바로 아래 강조 띠: 평소엔 날짜 배지, 수치가 나오면 숫자 카드 (이미지·로고와 겹치지 않음)
  badgeTop: 470,
  badgeHeight: 160,
  contentTop: 630,
} as const;

// 한국 증시 색 규칙: 상승=빨강, 하락=파랑
export const TONE_COLOR: Record<Tone, string> = {up: '#FF3B3B', down: '#2F7BFF', neutral: '#FFE600'};

export const FONT_STACK =
  "'SeoulNotice','SeoulAlrim','Malgun Gothic','Apple SD Gothic Neo','Noto Sans KR',sans-serif";
