import React from 'react';
import {Composition} from 'remotion';
import {TechExplainer} from './TechExplainer';
import {FPS} from './time';
import {CueProps, LAYOUT} from './types';

const defaultProps: CueProps = {
  audioFileName: 'jobs/fixture/narration.mp3',
  wordsFileName: 'jobs/fixture/words.json',
  bgColor: '#FFFFFF',
  chunkSize: 14,
  headerLogoFileName: 'img/header_logo.png',
  emoticonCues: [],
  captionSegments: [],
  companyLogoCues: [],
  numberCards: [],
  highlightKeywords: [],
  keywordTones: {},
  bgmFileName: '',
  openingText: '',
  openingDurationMs: 0,
  showOpening: false,
  ctaText: '',
  showOutro: false,
  durationInFrames: 150,
};

export const RemotionRoot: React.FC = () => (
  <Composition
    id="TechExplainer"
    component={TechExplainer}
    width={LAYOUT.width}
    height={LAYOUT.height}
    fps={FPS}
    durationInFrames={defaultProps.durationInFrames}
    defaultProps={defaultProps}
    calculateMetadata={({props}) => ({durationInFrames: Math.max(1, props.durationInFrames)})}
  />
);
