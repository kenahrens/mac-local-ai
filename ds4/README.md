# ds4

Runs [antirez's DeepSeek build (`ds4`)](https://github.com/antirez/ds4) as a local inference server on port 38011, managed as a macOS LaunchAgent so it survives reboots and crashes (`KeepAlive` + `RunAtLoad`). The server itself is antirez's; this is the launchd wrapper I run it with.

## Files

- `com.antirez.ds4-server.plist.template` — the launchd spec
- `com.antirez.ds4-caffeinate.plist.template` — keeps the machine awake while serving
- `install.sh` — renders the templates, writes them to `~/Library/LaunchAgents/`, and (re)loads the service

## Install / refresh

```sh
./install.sh
```

Idempotent. Re-run any time you change a tunable, the template, or pick up a new build of `ds4-server`. It expects the `ds4-server` binary and a `ds4flash.gguf` symlink in the ds4 repo (`make` it and `./download_model.sh` first).

## Tunables (env overrides)

| Var | Default | Notes |
|---|---|---|
| `DS4_REPO` | `~/go/src/github.com/antirez/ds4` | Where the binary and `ds4flash.gguf` symlink live |
| `DS4_PORT` | `38011` | The OpenAI-compatible endpoint port |
| `DS4_CTX` | `200000` | Max context window. The KV cache competes with model weights for RAM, so bump it carefully |
| `DS4_KV_DIR` | `~/.cache/ds4-kv` | On-disk KV cache spillover |
| `DS4_KV_MB` | `51200` | Disk KV cache budget (50 GB) |

## Swapping quants

The plist points at the `ds4flash.gguf` symlink, so changing models is zero plist edits: download a new quant (`./download_model.sh` retargets the symlink), then re-run `./install.sh` to restart the service.

## Gotcha

`ds4` defaults to a thinking mode that only streams `reasoning_content`. A client that ignores those deltas shows a blank response while the model thinks. Use the non-thinking variant if you want visible streaming.
