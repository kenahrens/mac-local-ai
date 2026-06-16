# How a scheduled local-AI job works

The `make-job.sh` helper schedules a job; this is the shape of the job itself. It's the pattern I use for things like a morning digest: gather some data, let a local model make one judgment call, deliver it, on a timer. Nothing here needs a cloud agent or a workflow builder.

## The shape

1. **Gather deterministically in code.** Pull from each source with a plain CLI or SDK call. No agent loop deciding what to fetch.
2. **Call the model once, for judgment only.** And only where judgment is actually needed (prioritizing, summarizing). Most of the job is plumbing the model never touches.
3. **Assemble once, render per channel.** One function turns the gathered data into whatever formats you ship — markdown, HTML email, a chat payload — so they never drift.
4. **Deliver, then drop a marker.** Write a dated marker file after a successful send so a retry never double-delivers.
5. **Schedule with launchd.** See [`make-job.sh`](make-job.sh) and the [README](README.md) for why launchd over cron.

That's the whole idea: the script drives the tools, the model only judges.

## The gotchas (the part that actually costs you time)

These bit me; they'll bite you too.

- **Network on wake.** launchd fires a job the moment the machine wakes, often before Wi-Fi reconnects. Every API call fails, and any OAuth token *refresh* fails with it. Poll DNS (ping a known host) for a couple minutes before doing anything, then proceed anyway and let the next run catch up.

- **launchd gives the job almost no environment.** The plist only passes `HOME` and `PATH` — none of your shell's exported keys. If your job needs API tokens from `~/.zshrc` or an env file, launch it through a login shell that sources them:

  ```bash
  /bin/zsh -ic 'set -a; source ~/.config/yourapp/env; set +a; exec node your-job.mjs'
  ```

  `zsh -ic` runs an interactive shell so `~/.zshrc` loads. `set -a` before sourcing matters if your env file uses bare `KEY=VAL` lines (not `export`) — without it the vars stay shell-local and never reach the child process.

- **Marker idempotency.** Drop a `job-YYYY-MM-DD.done` file after success and check for it at the top. Now a retry (or a heartbeat watchdog re-firing a missed job) is safe — it exits instead of redoing the work or sending twice.

- **Don't use a thinking model for scheduled work.** A reasoning/"thinking" model can drop into a multi-minute pass that blows your client timeout, and the job silently never finishes. Use the non-thinking variant for unattended jobs where you only need the answer.

- **Fault-isolate every source.** Each gather step should return an error object, not throw. One dead API degrades one section of the output instead of killing the whole job.

## Why local

Cost and privacy. A digest that runs every morning calling a frontier API adds up, and it's reading your calendar and your metrics. Pointed at a local model ([`../omlx/`](../omlx/), [`../ds4/`](../ds4/)) it's free to run as often as you like and nothing leaves the machine.
