# qa-judge

A small bounded judgement task you can run on modest Apple Silicon hardware to see whether a small local model is good enough for it. Triage a list of "this field changed during a replay" entries into REGRESSION or NOISE, and write a short ticket title.

## The use case

When you replay recorded traffic against a build, some response fields will differ from the recording. Most differences are noise (timestamps, request IDs, dates). A few are real regressions (status codes, money fields zeroed out, missing keys). A small local model is enough to read the diff and call it. You don't need a frontier model for this.

## What this recipe does

1. Installs [oMLX](https://github.com/jundot/omlx) via Homebrew if you don't have it.
2. Downloads `mlx-community/gemma-4-12B-it-4bit` (about 6.3 GB on disk, similar in RAM).
3. Sends a sample drift report at the model and prints its verdicts.
4. Runs the same prompt several times and reports tokens-per-second.

The whole thing runs locally. Nothing leaves your machine.

## Hardware target

Designed for the small end of Apple Silicon. The 12B 4-bit weights need around 6 GB of memory, plus headroom for the KV cache and the OS:

- M1 / M2 / M3 / M4 with **16 GB**: should fit, but close to the edge. Quit Chrome before you run it.
- M1 / M2 / M3 / M4 with **32 GB**: comfortable.
- Anything bigger: also fine, but you could just use a 27B+ model.

If you want a smaller model, edit `setup.sh` and swap `gemma-4-12B-it-4bit` for `Qwen2.5-7B-Instruct-4bit` (around 4 GB). The judge code doesn't care which model is loaded as long as oMLX is serving it.

## Running it

```bash
cd recipes/qa-judge
./setup.sh            # install + download model + start oMLX (one time)
./judge.py            # run the sample drift through the model, show verdicts
./bench.py            # 5 runs, report avg / min / max tok/s
```

## What "good enough" looks like

The sample drift has two clear regressions and three clear noise items. A model that gets this right will say:

- `balance_cents` zeroed: **REGRESSION**, the field is money
- HTTP 200 → 500: **REGRESSION**, status code changed
- `Date` header changed: **NOISE**, expected per request
- `Content-Length` differs: **NOISE**, follows from body changes
- request UUID differs: **NOISE**, expected per request

If your model misses one, it might still be useful with a more rigid prompt. If it misses several, try the bigger sibling.

## Scope

This recipe is the judge step in isolation. You give the model a fixed drift report, see what it does, and measure tok/s. The replay pipeline that produces real drift reports lives elsewhere. Once you've decided whether this size of model handles the judge well enough, you can wire it into that pipeline.
