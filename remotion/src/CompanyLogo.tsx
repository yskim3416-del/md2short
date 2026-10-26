import React from 'react';
import {Img, Sequence, staticFile} from 'remotion';
import {msToFrames} from './time';
import {CompanyLogoCue, LAYOUT} from './types';

// Small badge in the content area's top-right corner. Renders nothing when there are no cues.
export const CompanyLogos: React.FC<{cues: CompanyLogoCue[]}> = ({cues}) => {
  if (cues.length === 0) return null;
  return (
    <>
      {cues.map((cue, i) => (
        <Sequence key={i} from={msToFrames(cue.startMs)} durationInFrames={Math.max(1, msToFrames(cue.durationMs))}>
          <div
            style={{
              position: 'absolute',
              right: 40,
              top: LAYOUT.contentTop + 20,
              width: 200,
              height: 120,
              background: '#fff',
              borderRadius: 20,
              boxShadow: '0 6px 16px rgba(0,0,0,0.3)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              padding: 12,
            }}
          >
            <Img src={staticFile(cue.logoFileName)} style={{maxWidth: '100%', maxHeight: '100%', objectFit: 'contain'}} />
          </div>
        </Sequence>
      ))}
    </>
  );
};
