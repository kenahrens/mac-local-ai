# launchd

A small helper for scheduling local jobs on macOS with launchd, and the reasoning for using it over cron.

## Why launchd instead of cron

The short answer: **cron silently skips a job if the machine is asleep at the scheduled time. launchd runs the missed job when the machine wakes up.**

For anything scheduled while a laptop is usually closed (a 7am digest, a 2am backup), cron just skips it with no indication anything was missed. launchd with `StartCalendarInterval` checks at wake time whether a run was missed and runs it immediately.

Three other practical advantages on macOS:

- **Keychain access** — LaunchAgents run in your GUI login session and have reliable access to the macOS Keychain. cron runs in a stripped-down environment where Keychain access is flaky.
- **Explicit environment** — cron inherits a minimal shell, so Homebrew binaries are `command not found` unless you hardcode `PATH` everywhere. launchd plists declare `EnvironmentVariables` explicitly.
- **Native to macOS** — launchd is the macOS process supervisor (PID 1), what Apple uses for all system services. cron is a compatibility layer.

The one thing cron is simpler for: ad-hoc one-liners. For anything that runs more than occasionally, launchd is worth the plist.

## Usage

```bash
# every 15 minutes
./make-job.sh --label com.me.heartbeat --interval 900 -- /full/path/to/job.sh

# every day at 7:00am
./make-job.sh --label com.me.morning --daily 07:00 -- /full/path/to/job.sh
```

`make-job.sh` writes a plist to `~/Library/LaunchAgents/<label>.plist`, sends stdout/stderr to `~/.local/share/<label>/`, and loads it. Use a reverse-DNS label and an absolute path to the command.

Remove a job:

```bash
launchctl bootout gui/$(id -u)/<label> && rm ~/Library/LaunchAgents/<label>.plist
```

## Try it

[`examples/hello-job.sh`](examples/hello-job.sh) appends a timestamp to a log. Wire it up on a short interval to watch it fire:

```bash
./make-job.sh --label com.example.hello --interval 60 -- "$PWD/examples/hello-job.sh"
sleep 65 && cat ~/.local/share/com.example.hello/stdout.log
```
