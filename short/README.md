# short

Turns a long screen recording into vertical (9:16) YouTube Shorts. A local LLM does the judgment — which moments are worth clipping, where to crop — while ffmpeg and Whisper do the deterministic work. It runs against any OpenAI-compatible endpoint (I point it at local [oMLX](../omlx/)).

```bash
short <directory>              # auto-discover files in a dated folder
short <video.mp4> --clips 3    # flat video, ask for 3 clips
```

## Pipeline

1. Extract layers from a Tella `.zip` export if present (camera + screen), else use the flat video.
2. Transcribe the full video with Whisper `large-v3`, word-level timing.
3. A local LLM proposes candidate clips from the transcript.
4. A cheap local LLM judges each candidate on hook / standalone-ness / completeness (transcript only, no rendering — fast).
5. Top N clips get extracted, re-transcribed, vision-guided cropped to vertical, stacked, and captioned.

Output: `clip_01.mp4`, `clip_02.mp4`, ... at 1080x1920.

## What's novel (and where it fails)

The interesting parts are the *judging* prompts and the vision-guided crop (sample frames, ask the model where the content is, position the crop there). It's weakest on fast cuts and reframing a moving subject.

## Dependencies

- `ffmpeg` (with libass for captions), `whisper`, `jq`, `unzip`, `curl`
- An OpenAI-compatible LLM endpoint — set `OMLX_URL` (default `http://127.0.0.1:38010/v1`) and `OMLX_MODEL`

## Configuration

Env vars: `OMLX_URL`, `OMLX_MODEL`, `WHISPER_MODEL`, `NUM_CLIPS`, `CAPTION_STYLE`, `SCREEN_FIT`.

Transcription brand-name fixes (terms Whisper mishears) live in `~/.config/short/brands.json` as `{"misheard": "Correct"}`; they extend the built-in defaults.
