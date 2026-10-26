import React from 'react';
import {interpolate, useCurrentFrame, useVideoConfig} from 'remotion';
import {msToFrames} from './time';
import {FONT_STACK, LAYOUT} from './types';

const OUTRO_MS = 2600;

// Full-screen CTA over the last 2600ms. Mount only when showOutro is true.
export const Outro: React.FC<{text: string}> = ({text}) => {
  const frame = useCurrentFrame();
  const {durationInFrames} = useVideoConfig();
  const start = Math.max(0, durationInFrames - msToFrames(OUTRO_MS));
  if (frame < start) return null;
  const opacity = interpolate(frame, [start, start + 8], [0, 1], {extrapolateRight: 'clamp'});
  return (
    <div
      style={{
        position: 'absolute',
        left: 0,
        top: 0,
        width: LAYOUT.width,
        height: LAYOUT.height,
        background: 'rgba(0,0,0,0.88)',
        opacity,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        color: '#fff',
        fontFamily: FONT_STACK,
        fontWeight: 900,
        fontSize: 72,
        textAlign: 'center',
        padding: 80,
        wordBreak: 'keep-all',
      }}
    >
      {text}
    </div>
  );
};
