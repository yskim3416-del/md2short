import React from 'react';
import {Audio, AbsoluteFill, cancelRender, continueRender, delayRender, staticFile} from 'remotion';
import {BottomBar} from './BottomBar';
import {BrandHeader} from './BrandHeader';
import {Captions} from './Captions';
import {CompanyLogos} from './CompanyLogo';
import {NumberCards} from './NumberCard';
import {DateBadge} from './DateBadge';
import {Outro} from './Outro';
import {CueProps, LAYOUT, Word, WordsDoc} from './types';
import {VisualLayer} from './VisualLayer';

const FONT_CSS_ID = 'md2short-font-css';
const BGM_VOLUME = 0.08; // 내레이션(-14 LUFS) 아래로 깔리는 수준

export const TechExplainer: React.FC<CueProps> = (props) => {
  const [words, setWords] = React.useState<Word[]>([]);
  const [handle] = React.useState(() => delayRender('load words.json'));

  React.useEffect(() => {
    let cancelled = false;
    fetch(staticFile(props.wordsFileName))
      .then((r) => {
        if (!r.ok) throw new Error(`words.json fetch failed: ${r.status}`);
        return r.json() as Promise<WordsDoc>;
      })
      .then((doc) => {
        if (!cancelled) setWords(doc.words ?? []);
        continueRender(handle);
      })
      .catch((e) => {
        // 자막 없는 영상이 qc_passed 되지 않도록 렌더 자체를 실패시킨다
        cancelRender(e);
      });
    return () => {
      cancelled = true;
    };
  }, [props.wordsFileName, handle]);

  // Optional Seoul fonts: font.css lists @font-face entries; missing files fall back to the stack.
  React.useEffect(() => {
    if (document.getElementById(FONT_CSS_ID)) return;
    const link = document.createElement('link');
    link.id = FONT_CSS_ID;
    link.rel = 'stylesheet';
    link.href = staticFile('font/font.css');
    document.head.appendChild(link);
  }, []);

  return (
    <AbsoluteFill style={{background: props.bgColor, width: LAYOUT.width, height: LAYOUT.height}}>
      <Audio src={staticFile(props.audioFileName)} />
      {props.bgmFileName ? <Audio src={staticFile(props.bgmFileName)} volume={BGM_VOLUME} loop /> : null}
      <VisualLayer cues={props.emoticonCues} />
      <CompanyLogos cues={props.companyLogoCues} />
      <BrandHeader logoFileName={props.headerLogoFileName} />
      {props.showOpening ? <DateBadge text={props.openingText} /> : null}
      <NumberCards cards={props.numberCards} bgColor={props.bgColor} />
      <BottomBar>
        <Captions
          words={words}
          captionSegments={props.captionSegments}
          chunkSize={props.chunkSize}
          highlightKeywords={props.highlightKeywords}
          keywordTones={props.keywordTones}
          showOpening={props.showOpening}
          openingDurationMs={props.openingDurationMs}
        />
      </BottomBar>
      {props.showOutro ? <Outro text={props.ctaText} /> : null}
    </AbsoluteFill>
  );
};
