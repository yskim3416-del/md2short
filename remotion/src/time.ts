// The ONLY ms <-> frame conversion helper. Do not write `* 30 / 1000` anywhere else.
export const FPS = 30;

export const msToFrames = (ms: number, fps: number = FPS): number =>
  Math.round((ms * fps) / 1000);

export const framesToMs = (frames: number, fps: number = FPS): number =>
  Math.round((frames * 1000) / fps);
