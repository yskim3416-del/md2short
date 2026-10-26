#!/usr/bin/env bash
# Render the fixture job (jobs/fixture) to remotion/out/fixture.mp4.
set -euo pipefail
cd "$(dirname "$0")/.."
ROOT="$(cd .. && pwd)"

JOB_DIR=public/jobs/fixture
mkdir -p "$JOB_DIR" out

ffmpeg -y -loglevel error -f lavfi -i "sine=frequency=440:duration=5" -c:a libmp3lame "$JOB_DIR/narration.mp3"
cp fixtures/words.json "$JOB_DIR/words.json"
cp fixtures/props.json "$JOB_DIR/props.json"

# Shared asset folders: symlink is not reliable on Windows, so copy.
for d in emoticon img company; do
  mkdir -p "$ROOT/$d"
  if [ ! -e "public/$d" ]; then
    cp -r "$ROOT/$d" "public/$d"
  fi
done

npx remotion render src/index.ts TechExplainer out/fixture.mp4 \
  --props=public/jobs/fixture/props.json --codec=h264 --log=warn --overwrite
