#!/usr/bin/env python3
"""judge.py — ask the local model to triage a drift report.

Reads sample-drift.json from the same directory by default, sends it through
the model running on oMLX, prints the model's verdict.
"""
import argparse, json, os, sys, time, urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
DEFAULTS = {
    "url":   os.environ.get("OMLX_URL",   "http://127.0.0.1:38010/v1"),
    "model": os.environ.get("OMLX_MODEL", "gemma-4-12B-it-4bit"),
    "input": str(HERE / "sample-drift.json"),
}

SYSTEM = (
    "You are a QA engineer triaging a failed regression replay. "
    "For each drifted field, decide REGRESSION (a real behavior change "
    "that should fail the build, like a status code change or a body field "
    "with a different value) or NOISE (an environmental difference that's "
    "expected on every replay, like dates, request ids, content-length). "
    "Be terse: one line per field, then one ticket title at the end."
)

TEMPLATE = """A scheduled replay flagged drift. Triage it.

Drift report:
{drift}

Output exactly this format:

VERDICTS:
- <field>: REGRESSION|NOISE -- <one-line reason>
- ...

TICKET TITLE: <one sentence suitable as a bug ticket title>
"""

def call(url, model, system, user, max_tokens=400, timeout=180):
    body = json.dumps({
        "model": model,
        "messages": [{"role": "system", "content": system},
                     {"role": "user", "content": user}],
        "temperature": 0.2,
        "max_tokens": max_tokens,
        "stream": False,
    }).encode()
    req = urllib.request.Request(
        f"{url}/chat/completions",
        data=body,
        headers={"Content-Type": "application/json"},
    )
    t0 = time.time()
    with urllib.request.urlopen(req, timeout=timeout) as r:
        resp = json.load(r)
    dt = time.time() - t0
    msg = resp["choices"][0]["message"]["content"]
    usage = resp.get("usage", {})
    return msg, dt, usage

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--url",   default=DEFAULTS["url"])
    p.add_argument("--model", default=DEFAULTS["model"])
    p.add_argument("--input", default=DEFAULTS["input"])
    args = p.parse_args()

    drift = Path(args.input).read_text()
    user = TEMPLATE.format(drift=drift)
    msg, dt, usage = call(args.url, args.model, SYSTEM, user)
    print(msg)
    ct = usage.get("completion_tokens") or 0
    tps = ct / dt if dt > 0 and ct else 0
    print(f"\n[{ct} tokens in {dt:.1f}s = {tps:.1f} tok/s, model={args.model}]",
          file=sys.stderr)

if __name__ == "__main__":
    main()
