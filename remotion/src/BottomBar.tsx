import React from 'react';
import {LAYOUT} from './types';

// Bottom 520px black band; captions sit in its upper part so platform UI (title, buttons) at the very bottom doesn't cover them.
export const BottomBar: React.FC<{children?: React.ReactNode}> = ({children}) => (
  <div
    style={{
      position: 'absolute',
      left: 0,
      top: LAYOUT.height - LAYOUT.bottomHeight,
      width: LAYOUT.width,
      height: LAYOUT.bottomHeight,
      background: '#000',
      display: 'flex',
      alignItems: 'flex-start',
      justifyContent: 'center',
      paddingTop: 30,
      boxSizing: 'border-box',
    }}
  >
    {children}
  </div>
);
