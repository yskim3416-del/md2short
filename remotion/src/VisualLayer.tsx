import React from 'react';
import {Img, interpolate, Sequence, spring, staticFile, useCurrentFrame, useVideoConfig} from 'remotion';
import {msToFrames} from './time';
import {EmoticonCue, LAYOUT} from './types';

const CONTENT_H = LAYOUT.height - LAYOUT.contentTop - LAYOUT.bottomHeight;

// 정지 화면이 길게 이어지지 않도록: 등장 pop + 느린 zoom-in + 가벼운 상하 흔들림
const Cue: React.FC<{cue: EmoticonCue; frames: number}> = ({cue, frames}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const enter = spring({frame, fps, config: {damping: 14, stiffness: 160}});
  const zoom = interpolate(frame, [0, Math.max(1, frames)], [1.0, 1.1], {
    extrapolateRight: 'clamp',
  });
  const scale = (0.9 + 0.1 * enter) * zoom;
  const bob = Math.sin((frame / fps) * Math.PI) * 8;
  const isPhoto = cue.visualMode === 'photo' || cue.assetKind === 'photo';
  return (
    <div
      style={{
        position: 'absolute',
        left: 0,
        top: LAYOUT.contentTop,
        width: LAYOUT.width,
        height: CONTENT_H,
        overflow: 'hidden',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
      }}
    >
      <Img
        src={staticFile(cue.emoticonFileName)}
        style={{
          width: isPhoto ? LAYOUT.width : Math.min(LAYOUT.width, CONTENT_H),
          height: isPhoto ? CONTENT_H : Math.min(LAYOUT.width, CONTENT_H),
          objectFit: isPhoto ? 'cover' : 'contain',
          transform: `translateY(${bob}px) scale(${scale})`,
          opacity: Math.min(1, frame / 4),
        }}
      />
    </div>
  );
};

export const VisualLayer: React.FC<{cues: EmoticonCue[]}> = ({cues}) => (
  <>
    {cues.map((cue, i) => {
      const frames = Math.max(1, msToFrames(cue.durationMs));
      return (
        <Sequence key={i} from={msToFrames(cue.startMs)} durationInFrames={frames}>
          <Cue cue={cue} frames={frames} />
        </Sequence>
      );
    })}
  </>
);
