#!/usr/bin/env bash
# transcribe.sh — transcribe an audio file using local Whisper
# Usage: transcribe.sh <audio.m4a> [output_dir]
# Output: <output_dir>/<basename>.txt

set -euo pipefail

AUDIO="${1:-}"
OUTPUT_DIR="${2:-$(dirname "${1:-/tmp/x}")}"

if [[ -z "$AUDIO" ]]; then
  echo "Usage: transcribe.sh <audio.m4a> [output_dir]"
  exit 1
fi

if [[ ! -f "$AUDIO" ]]; then
  echo "File not found: $AUDIO"
  exit 1
fi

if ! command -v whisper &>/dev/null; then
  echo "whisper not found — install with: pip install openai-whisper"
  exit 1
fi

echo "Transcribing: $AUDIO"
echo "Model: turbo | Device: mps | Language: en"
echo ""

whisper "$AUDIO" \
  --model turbo \
  --language en \
  --device mps \
  --output_format txt \
  --output_dir "$OUTPUT_DIR"

BASENAME=$(basename "$AUDIO")
BASENAME="${BASENAME%.*}"
OUTFILE="$OUTPUT_DIR/${BASENAME}.txt"

echo ""
echo "Transcript: $OUTFILE"
echo "Next:  node $(dirname "$0")/blog-from-transcript.mjs $OUTFILE"
