import React from 'react';
import {Img, staticFile} from 'remotion';
import {LAYOUT} from './types';

// Top 470px black band = 250px safe margin + 220px logo area.
export const BrandHeader: React.FC<{logoFileName: string}> = ({logoFileName}) => (
  <div
    style={{
      position: 'absolute',
      left: 0,
      top: 0,
      width: LAYOUT.width,
      height: LAYOUT.headerHeight,
      background: '#000',
    }}
  >
    <div
      style={{
        position: 'absolute',
        left: 0,
        top: 250,
        width: LAYOUT.width,
        height: 220,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
      }}
    >
      <Img src={staticFile(logoFileName)} style={{maxHeight: 220, maxWidth: 800, objectFit: 'contain'}} />
    </div>
  </div>
);
