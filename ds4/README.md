# ds4

Runs [antirez's DeepSeek build (`ds4`)](https://github.com/antirez/ds4) as a local inference server on port 38011. Two modes: an always-on LaunchAgent install (see below), or on-demand start/stop helpers. The server itself is antirez's; this is the wrapper I run it with.

## Heads up

DS4 holds ~80GB resident once weights are warm. That is fine on its own, but on a 128GB machine it can crowd out other large models. If you also run an always-on oMLX with big models loaded, prefer the on-demand mode below over the LaunchAgent install.

## Files

- `com.antirez.ds4-server.plist.template`: the launchd spec for always-on mode
- `install.sh`: renders the template, writes it to `~/Library/LaunchAgents/`, and (re)loads the service
- `ds4-on.sh` / `ds4-off.sh`: on-demand start and stop helpers

A general keep-the-machine-awake LaunchAgent (caffeinate) lives in [`../launchd/keep-awake.plist`](../launchd/keep-awake.plist). It's decoupled from DS4 since it's just `caffeinate -s` and useful regardless of which models are running.

## Always-on install / refresh

```sh
./install.sh
```

Idempotent. Re-run any time you change a tunable, the template, or pick up a new build of `ds4-server`. It expects the `ds4-server` binary and a `ds4flash.gguf` symlink in the ds4 repo (`make` it and `./download_model.sh` first).

## On-demand mode

```sh
./ds4-on.sh    # spawn ds4-server, warm weights, listen on :38011
./ds4-off.sh   # kill it and free the memory
```

No LaunchAgent involved, so it never auto-starts at login. Use this when DS4 is too memory-hungry to leave running with the rest of your stack. `ds4-on.sh` is a no-op if something is already listening on :38011, so it's safe to run twice.

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
