import React from 'react';
import {interpolate, Sequence, spring, useCurrentFrame, useVideoConfig} from 'remotion';
import {msToFrames} from './time';
import {FONT_STACK, LAYOUT, NumberCardCue} from './types';

// 숫자 색: 상승=빨강, 하락=파랑 (노란 카드 위 가독성 위해 TONE_COLOR보다 진한 톤)
const NUMBER_COLOR = {up: '#E0001B', down: '#0047D6', neutral: '#111'} as const;

// header 아래 강조 띠에 날짜 배지를 덮어 표시 — 로고·이미지와 겹치지 않는 고정 위치.
const Card: React.FC<{card: NumberCardCue; bgColor: string}> = ({card, bgColor}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const pop = spring({frame, fps, config: {damping: 12, stiffness: 180}});
  const tilt = interpolate(frame, [0, 10], [-5, -2], {extrapolateRight: 'clamp'});
  return (
    <div
      style={{
        position: 'absolute',
        left: 0,
        top: LAYOUT.badgeTop,
        width: LAYOUT.width,
        height: LAYOUT.badgeHeight,
        background: bgColor,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
      }}
    >
      <div
        style={{
          transform: `scale(${pop}) rotate(${tilt}deg)`,
          background: '#FFE600',
          border: '5px solid #111',
          borderRadius: 26,
          padding: '6px 40px',
          display: 'flex',
          alignItems: 'baseline',
          gap: 24,
          fontFamily: FONT_STACK,
          color: '#111',
        }}
      >
        {card.label ? <div style={{fontSize: 50, fontWeight: 800}}>{card.label}</div> : null}
        <div style={{fontSize: 100, fontWeight: 900, lineHeight: 1.1, color: NUMBER_COLOR[card.tone ?? 'neutral']}}>
          {card.text}
        </div>
      </div>
    </div>
  );
};

export const NumberCards: React.FC<{cards: NumberCardCue[]; bgColor: string}> = ({cards, bgColor}) => (
  <>
    {cards.map((card, i) => (
      <Sequence key={i} from={msToFrames(card.startMs)} durationInFrames={Math.max(1, msToFrames(card.durationMs))}>
        <Card card={card} bgColor={bgColor} />
      </Sequence>
    ))}
  </>
);
