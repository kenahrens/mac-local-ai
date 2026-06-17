# recipes

Self-contained recipes you can pull onto a Mac, run, and see something work. Each recipe is a single directory with a setup script, the code that exercises it, and a benchmark that produces real numbers on your machine.

## What's here

| Recipe | What it does | Target hardware |
|---|---|---|
| [`qa-judge/`](qa-judge/) | Triage a fake drift report with a small local model. Decides per-field REGRESSION vs NOISE, writes a one-line ticket title. Reports tok/s. | Apple Silicon, 16 GB or more |

## Why recipes

Each recipe answers one question on your actual hardware:

- Will this model fit?
- How fast is it on my chip?
- Is the output good enough for the job I have in mind?

You clone the repo, `cd recipes/<name>/`, run `./setup.sh`, then run the bench. You get real numbers and a real verdict. No guessing.
