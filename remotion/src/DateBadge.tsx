import React from 'react';
import {spring, useCurrentFrame, useVideoConfig} from 'remotion';
import {FONT_STACK, LAYOUT} from './types';

// 날짜 배지: 첫 프레임부터 끝까지 header 아래 강조 띠의 같은 자리에 표시 (숫자 카드가 뜨는 동안만 가려짐).
export const DateBadge: React.FC<{text: string}> = ({text}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const pop = spring({frame, fps, config: {damping: 14}});
  return (
    <div
      style={{
        position: 'absolute',
        left: 0,
        top: LAYOUT.badgeTop,
        width: LAYOUT.width,
        height: LAYOUT.badgeHeight,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
      }}
    >
      <div
        style={{
          transform: `scale(${pop})`,
          background: '#111',
          color: '#fff',
          borderRadius: 999,
          padding: '14px 44px',
          fontFamily: FONT_STACK,
          fontWeight: 800,
          fontSize: 52,
          border: '5px solid #FFE600',
        }}
      >
        {text.replace(/\n/g, ' ')}
      </div>
    </div>
  );
};
