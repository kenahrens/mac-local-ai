# omlx

Scripts to run [oMLX](https://github.com/jundot/omlx) as an always-on local inference server. oMLX is someone else's open-source project — an OpenAI-compatible server for MLX models on Apple Silicon. These are just the wrappers I run it with.

## Install oMLX

oMLX is distributed as a Homebrew formula and a menu-bar app. See [jundot/omlx](https://github.com/jundot/omlx). The scripts here assume the Homebrew install at `/opt/homebrew/opt/omlx`.

## Scripts

| Script | What it does |
|---|---|
| `start-omlx.sh` | Starts the server. Run it directly, or point a Homebrew service / LaunchAgent at it so it auto-starts at login. |
| `status-omlx.sh` | Shows whether the LaunchAgent is loaded, whether the port is listening, and what models are loaded. |
| `download-model.sh <hf-model-id> [revision]` | Pulls an MLX model from Hugging Face into the model dir. |

## The flags, and why

`start-omlx.sh` runs `omlx serve` with these, all overridable via env vars:

- `--max-process-memory 90%` — let it use most of the unified memory. On a 128GB machine that headroom is the point: an inference server, a transcription model, and warm caches all stay resident.
- `--hot-cache-max-size 20GB` — the RAM tier of the KV cache before it spills to SSD.
- `--paged-ssd-cache-dir` — the cold tier. This is the feature I came for: a returning prompt prefix restores from disk instead of recomputing, dropping time-to-first-token on long contexts from tens of seconds to a couple.
- `--max-concurrent-requests 1` — I'm one person. Batching buys nothing; serial requests keep latency predictable.

## Environment

All paths/ports are env-overridable (`OMLX_HOME`, `OMLX_PORT`, `OMLX_MODEL_DIR`, `OMLX_SSD_CACHE_DIR`, ...). Defaults put everything under `~/.omlx` on port `38010`.

```bash
./download-model.sh mlx-community/Qwen2.5-0.5B-Instruct-4bit   # smoke-test model
./start-omlx.sh                                                # serve on :38010
./status-omlx.sh                                               # check it
curl http://127.0.0.1:38010/v1/models                          # OpenAI-compatible
```
