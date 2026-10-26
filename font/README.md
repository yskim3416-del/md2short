# Fonts

Drop the Seoul font files here (SeoulNotice / SeoulAlrim, `.ttf` or `.otf`), named:

- `SeoulNotice.ttf` or `SeoulNotice.otf`
- `SeoulAlrim.ttf` or `SeoulAlrim.otf`

Then copy them to `remotion/public/font/` (next to `font.css`). `remotion/public/font/font.css` declares the `@font-face` entries.
Rendering works without them: the stack falls back to `'Malgun Gothic','Apple SD Gothic Neo','Noto Sans KR',sans-serif`.
