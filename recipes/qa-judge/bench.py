#!/usr/bin/env python3
"""bench.py — run the judge prompt several times, report tok/s stats.

Includes one warm-up pass that's discarded (cold-cache JIT / model load can
skew the first call). Then prints per-run timings and a small summary.
"""
import os, statistics, sys
from pathlib import Path
from judge import SYSTEM, TEMPLATE, call, DEFAULTS

HERE = Path(__file__).resolve().parent

def main():
    url   = os.environ.get("OMLX_URL",   DEFAULTS["url"])
    model = os.environ.get("OMLX_MODEL", DEFAULTS["model"])
    drift = (HERE / "sample-drift.json").read_text()
    user  = TEMPLATE.format(drift=drift)
    runs  = int(os.environ.get("BENCH_RUNS", "5"))

    print(f"benchmarking {model} via {url}")
    print(f"warm-up (discarded): ", end="", flush=True)
    _, dt, u = call(url, model, SYSTEM, user, max_tokens=300)
    print(f"{u.get('completion_tokens', 0)} tok in {dt:.1f}s")

    rates = []
    for i in range(1, runs + 1):
        _, dt, u = call(url, model, SYSTEM, user, max_tokens=300)
        ct = u.get("completion_tokens") or 0
        tps = ct / dt if dt > 0 and ct else 0
        rates.append(tps)
        print(f"run {i}: {ct} tok in {dt:.1f}s = {tps:.1f} tok/s")

    if rates:
        print(f"\nover {runs} runs: avg {statistics.mean(rates):.1f} tok/s, "
              f"min {min(rates):.1f}, max {max(rates):.1f}")

if __name__ == "__main__":
    main()
