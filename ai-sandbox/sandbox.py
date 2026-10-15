#!/usr/bin/env python3
"""Create disposable mock-lab takes and record each terminal locally."""

import argparse
from datetime import datetime
import json
from pathlib import Path
import re
import shlex
import shutil
import subprocess
import sys
import tempfile
import tarfile
import uuid
import os
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parent
RUNS = ROOT / "runs"
SPEEDSCALE_CONFIG = Path(os.environ.get("AI_SANDBOX_CONFIG", str(Path.home() / ".speedscale" / "dev.yaml"))).expanduser().resolve()
APP_URL = os.environ.get("AI_SANDBOX_APP_URL", "dev.speedscale.com")
PROFILES = {
    "node": "node:24-bookworm-slim",
    "python": "python:3.12-slim-bookworm",
    "go": "golang:1.26-bookworm",
    "java": "eclipse-temurin:21-jdk-jammy",
}
GUEST_MOCK_LAB = Path("/home/agent/mock-lab")
SHELL_SETUP = 8
AGENTS = ("claude", "codex", "opencode", "pi", "kilo")
AGENT_HOSTS = (
    "claude.ai:443,claude.com:443,downloads.claude.ai:443,api.anthropic.com:443,"
    "platform.claude.com:443,console.anthropic.com:443,"
    "chatgpt.com:443,auth.openai.com:443,api.openai.com:443,releases.openai.com:443,"
    "nodejs.org:443,registry.npmjs.org:443,opencode.ai:443,api.opencode.ai:443,"
    "models.dev:443,openrouter.ai:443,api.github.com:443,kilo.ai:443,api.kilo.ai:443,app.kilo.ai:443,auth.kilo.ai:443"
)


def run(*args, **kwargs):
    return subprocess.run([str(arg) for arg in args], check=True, **kwargs)


def output(*args):
    return run(*args, stdout=subprocess.PIPE, text=True).stdout.strip()


def image(language):
    return f"speedscale-ai-sandbox:{language}-v2"


def credential_env(config=None, app_url=None):
    # Keep credentials out of command arguments and recordings.
    config = Path(config) if config else SPEEDSCALE_CONFIG
    app_url = app_url or APP_URL
    env = dict(os.environ)
    env.pop("SPEEDSCALE_API_KEY", None)
    env.pop("SPEEDSCALE_CONTEXT", None)
    with tempfile.TemporaryDirectory(prefix="ai-sandbox-key-") as scratch:
        (Path(scratch) / ("config.json" if config.suffix == ".json" else "config.yaml")).symlink_to(config)
        env["SPEEDSCALE_HOME"] = scratch
        result = subprocess.run(["sh", str(ROOT / "speedscale-apikey.sh")],
                                env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    key = result.stdout.strip()
    if result.returncode or not key or "\n" in key:
        raise ValueError(f"Could not read the active API key from {config}")
    env = dict(os.environ)
    env["SPEEDSCALE_API_KEY"] = key
    env["SPEEDSCALE_APP_URL"] = app_url
    return env


def build(language):
    if subprocess.run(["docker", "image", "inspect", PROFILES[language]],
                      stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).returncode == 0:
        space = subprocess.run(["docker", "run", "--rm", "--read-only", "--entrypoint", "df",
                                PROFILES[language], "-Pk", "/"], capture_output=True, text=True)
        if space.returncode == 0:
            available_kib = int(space.stdout.splitlines()[-1].split()[3])
            if available_kib < 1024 * 1024:
                raise ValueError("Docker's internal disk needs at least 1 GiB free to build the template. "
                                 "Increase its disk allocation in Docker Desktop > Settings > Resources, "
                                 "or free unused Docker data before retrying.")
    run("docker", "build", "--build-arg", f"RUNTIME_IMAGE={PROFILES[language]}",
        "--tag", image(language), ROOT)
    load_image(language)


def load_image(language):
    with tempfile.TemporaryDirectory(prefix="demo-image-", dir=ROOT) as scratch:
        archive = Path(scratch) / "image.tar"
        run("docker", "image", "save", "--output", archive, image(language))
        run("sbx", "template", "load", archive)


def take_path(identifier):
    if identifier == "latest":
        candidates = sorted(RUNS.glob("*/session.json")) if RUNS.exists() else []
        candidates = [path for path in candidates
                      if json.loads(path.read_text()).get("purpose") != "validation"
                      and json.loads(path.read_text()).get("status") != "failed"]
        if not candidates:
            raise ValueError("No sandbox yet. Run: ai-sandbox")
        return candidates[-1].parent
    if not re.fullmatch(r"[a-z0-9-]+", identifier):
        raise ValueError("Invalid take ID")
    path = RUNS / identifier
    if not (path / "session.json").exists():
        raise ValueError(f"Unknown take: {identifier}")
    return path


def session(identifier, allow_failed=False):
    path = take_path(identifier)
    data = json.loads((path / "session.json").read_text())
    if data["status"] == "removed":
        raise ValueError("This sandbox was removed. Its workspace and recordings are retained.")
    if data["status"] == "failed" and not allow_failed:
        raise ValueError("Setup for this sandbox failed. Run ai-sandbox to create a new one.")
    return path, data


def save(path, data):
    (path / "session.json").write_text(json.dumps(data, indent=2) + "\n")


def configure(identifier):
    path, data = session(identifier)
    run("sbx", "policy", "allow", "network", "--sandbox", data["sandbox"],
        f"{data.get('app_url', APP_URL)}:443,demo-api.trafficreplay.com:443,demo-api-dev.trafficreplay.com:443,downloads.speedscale.com:443,"
        "raw.githubusercontent.com:443,github.com:443,codeload.github.com:443,docs.speedscale.com:443,"
        "deb.debian.org:443,security.debian.org:443,archive.ubuntu.com:443,ports.ubuntu.com:443,security.ubuntu.com:443",
        stdout=subprocess.DEVNULL)
    command = r'''set -eu
test -r "$1"
if ! command -v make >/dev/null || ! command -v ps >/dev/null; then
    for source in /etc/apt/sources.list /etc/apt/sources.list.d/*.list /etc/apt/sources.list.d/*.sources; do
        if [[ -f "$source" ]]; then
            sudo sed -i 's|http://|https://|g' "$source"
        fi
    done
    for attempt in {1..12}; do
        if sudo apt-get -o Acquire::https::Proxy="${HTTPS_PROXY:-DIRECT}" -o Acquire::https::Timeout=20 update -qq; then
            break
        fi
        [[ "$attempt" != 12 ]] || exit 1
        sleep 5
    done
    sudo apt-get -o DPkg::Lock::Timeout=60 -o Acquire::https::Proxy="${HTTPS_PROXY:-DIRECT}" install -y --no-install-recommends make procps
    sudo rm -rf /var/lib/apt/lists/*
fi
if [[ ! -f "$HOME/.ai-sandbox-mcp.json" ]]; then
    printf '%s\n' '{"mcpServers":{}}' > "$HOME/.ai-sandbox-mcp.json"
fi
cat > "$HOME/.demo-sandbox.bashrc" <<'RC'
source /etc/demo.bashrc
export BASH_ENV="$HOME/.demo-sandbox.bashrc"
export DISABLE_NONESSENTIAL_TRAFFIC=1
export DISABLE_AUTOUPDATER=1
if [[ "${ANTHROPIC_API_KEY:-}" == *proxy-managed* ]]; then
    unset ANTHROPIC_API_KEY
fi
if [[ "${OPENAI_API_KEY:-}" == *proxy-managed* ]]; then
    unset OPENAI_API_KEY
fi
alias claude='claude --strict-mcp-config --mcp-config ~/.ai-sandbox-mcp.json'
export PS1='\[\e[32m\]sandbox\[\e[0m\]:\[\e[36m\]\w\[\e[0m\] $ '
RC
'''
    command = command.replace("source /etc/demo.bashrc\n", (ROOT / "demo.bashrc").read_text(), 1)
    run("sbx", "exec", data["sandbox"], "bash", "-c", command, "bash", data["speedscale_config"],
        stdout=subprocess.DEVNULL)
    print("The configured API key will be provided at runtime as SPEEDSCALE_API_KEY. Proxymock setup belongs to the agent.", flush=True)
    if data["status"] != "initializing":
        data["status"] = "ready"
    data["shell_setup"] = SHELL_SETUP
    save(path, data)


def ensure_agents(identifier):
    path, data = session(identifier)
    run("sbx", "policy", "allow", "network", "--sandbox", data["sandbox"], AGENT_HOSTS,
        stdout=subprocess.DEVNULL)
    print("Preparing Claude Code, Codex, OpenCode 2.x, Pi and Kilo Code inside the sandbox...", flush=True)
    command = (ROOT / "install-agents.sh").read_text()
    run("sbx", "exec", data["sandbox"], "bash", "-c", command)
    data["agents"] = list(AGENTS)
    save(path, data)


def agent(identifier, name):
    ensure_agents(identifier)
    configure(identifier)
    if name == "claude":
        command = "exec claude --strict-mcp-config --mcp-config ~/.ai-sandbox-mcp.json"
    elif name == "codex":
        command = "codex login status >/dev/null 2>&1 || codex login --device-auth || exit $?\nexec codex"
    else:
        command = "exec " + name
    terminal(identifier, command=command)


def export_mock_lab(destination):
    commit = output("git", "ls-remote", "https://github.com/speedscale/mock-lab.git", "refs/heads/main").split()[0]
    if not re.fullmatch(r"[0-9a-f]{40}", commit):
        raise ValueError("Could not resolve mock-lab main")
    with tempfile.TemporaryDirectory(prefix="demo-source-", dir=ROOT) as scratch:
        archive = Path(scratch) / "source.tar.gz"
        with urlopen(f"https://codeload.github.com/speedscale/mock-lab/tar.gz/{commit}", timeout=60) as response:
            with archive.open("wb") as target:
                shutil.copyfileobj(response, target)
        with tarfile.open(archive) as source:
            source.extractall(scratch, filter="data")
        shutil.move(str(Path(scratch) / f"mock-lab-{commit}"), destination)
    return commit


def seed_mock_lab(sandbox):
    # Transfer the clean source into the guest without mounting launcher files.
    with tempfile.TemporaryDirectory(prefix="demo-source-", dir=ROOT) as scratch:
        source = Path(scratch) / "mock-lab"
        commit = export_mock_lab(source)
        archive = Path(scratch) / "mock-lab.tar"
        with tarfile.open(archive, "w") as target:
            target.add(source, arcname="mock-lab")
        with archive.open("rb") as stream:
            run("sbx", "exec", "-i", sandbox, "tar", "-xf", "-", "-C", "/home/agent", stdin=stream)
    return commit


def ensure_login():
    # Interactive sbx commands can start login; don't capture its confirmation code.
    check = subprocess.run(["sbx", "ls"], stdin=subprocess.DEVNULL, capture_output=True, text=True)
    if check.returncode == 0:
        return
    if "not signed in" in check.stderr.lower():
        print("Complete the Docker sign-in in your browser; setup will continue here.", flush=True)
        run("sbx", "login")
        return
    raise ValueError(check.stderr.strip() or "Could not connect to Docker Sandboxes")


def new(language, no_open):
    if not SPEEDSCALE_CONFIG.is_file() or not os.access(SPEEDSCALE_CONFIG, os.R_OK):
        raise ValueError(f"Missing or unreadable Speedscale config: {SPEEDSCALE_CONFIG}. Set AI_SANDBOX_CONFIG to select a file.")
    credential_env()
    ensure_login()
    if subprocess.run(["docker", "image", "inspect", image(language)],
                      stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).returncode:
        build(language)
    else:
        templates = json.loads(output("sbx", "template", "ls", "--json"))["images"]
        if not any(f"{entry['repository'].rsplit('/', 1)[-1]}:{entry['tag']}" == image(language)
                   for entry in templates):
            load_image(language)
    identifier = f"{datetime.now().strftime('%Y%m%d-%H%M%S')}-{language}-{uuid.uuid4().hex[:6]}"
    path = RUNS / identifier
    workspace = Path.cwd().resolve()
    (path / "recordings").mkdir(parents=True)
    name = "speedscale-ai-sandbox-" + identifier
    data = {"id": identifier, "sandbox": name, "language": language,
            "purpose": "recording",
            "workspace": str(workspace), "app": str(GUEST_MOCK_LAB / "languages" / language),
            "image": image(language),
            "speedscale_config": str(SPEEDSCALE_CONFIG), "app_url": APP_URL,
            "proxymock_setup": "agent-installed",
            "status": "initializing"}
    check = r'''set -eu
if command -v proxymock >/dev/null || [[ -e /usr/local/bin/proxymock-real ]]; then
    echo "The template contains proxymock; rebuild the clean template." >&2
    exit 1
fi
test ! -e "$HOME/.speedscale/config.json"
test ! -e "$HOME/.speedscale/config.yaml"
for skills in "$HOME/.claude/skills" "$HOME/.agents/skills" "$HOME/.codex/skills"; do
    if [[ -d "$skills" ]] && [[ -n "$(find "$skills" -name SKILL.md -print -quit)" ]]; then
        echo "The new sandbox contains preinstalled skills." >&2
        exit 1
    fi
done
'''
    create_started = False
    try:
        save(path, data)
        create_started = True
        run("sbx", "create", "--name", name, "--template", image(language),
            "--pull", "never", "--skills", "off", "--cpus", "2", "--memory", "4g",
            "--publish", "8080", "--publish", "4143", "--publish", "7788", "shell", workspace,
            str(SPEEDSCALE_CONFIG) + ":ro")
        data["image_id"] = output("docker", "image", "inspect", image(language), "--format", "{{.Id}}")
        data["mock_lab_commit"] = seed_mock_lab(name)
        save(path, data)
        run("sbx", "exec", name, "bash", "-c", "test -d \"$1\"", "bash", data["app"])
        configure(identifier)
        ensure_agents(identifier)
        run("sbx", "exec", name, "bash", "-c", check)
        data = json.loads((path / "session.json").read_text())
        data["clean_start_verified"] = True
        data["status"] = "ready"
        save(path, data)
    except BaseException:
        # Exclude failed setup from "latest" even if guest removal fails.
        data["status"] = "failed"
        try:
            save(path, data)
        except OSError as error:
            print(f"Could not save failed session {identifier}: {error}", file=sys.stderr)
        if create_started:
            try:
                cleanup = subprocess.run(["sbx", "rm", "--force", name], capture_output=True, text=True)
                if cleanup.returncode:
                    raise ValueError(cleanup.stderr.strip() or cleanup.stdout.strip()
                                     or f"sbx rm exited with status {cleanup.returncode}")
            except (OSError, subprocess.SubprocessError, ValueError) as error:
                print(f"Could not remove sandbox {name}: {error}\n"
                      f"Retry with: ai-sandbox remove {identifier}", file=sys.stderr)
        raise
    print(f"Ready: {identifier}\nWorkspace: {workspace}\nMock-lab: {data['app']}\nRecordings: {path / 'recordings'}", flush=True)
    run("sbx", "ports", name)
    print("Run " + ", ".join(AGENTS) + " inside the recorded shell to start an agent.", flush=True)
    print("Proxymock is not installed. Ask the agent to install the current CLI and skills.", flush=True)
    if not no_open:
        open_terminal(identifier)
    return identifier


def open_terminal(identifier):
    path, _ = session(identifier)
    launcher = path / f"Terminal-{uuid.uuid4().hex[:6]}.command"
    launcher.write_text("#!/bin/bash\nexec " + shlex.join([sys.executable, str(ROOT / "sandbox.py"),
                                                           "terminal", path.name]) + "\n")
    launcher.chmod(0o755)
    run("open", "-a", "Terminal", launcher)


def terminal(identifier, command=None, headless=False):
    path, data = session(identifier)
    if data.get("proxymock_setup") != "agent-installed":
        print("This take uses an older template. Run ai-sandbox for a clean installation demo.", flush=True)
    if data.get("agents") != list(AGENTS):
        ensure_agents(identifier)
        configure(identifier)
    elif data.get("shell_setup") != SHELL_SETUP:
        configure(identifier)
    recording = path / "recordings" / f"{datetime.now().strftime('%Y%m%d-%H%M%S')}-{uuid.uuid4().hex[:6]}.cast"
    argv = ["sbx", "exec", "-t"]
    if not headless:
        argv.append("-i")
    argv += ["--env", "SPEEDSCALE_API_KEY", "--env", f"SPEEDSCALE_APP_URL={data.get('app_url', APP_URL)}",
             "--env", f"DEMO_LANGUAGE={data['language']}", "--env", f"MOCK_LAB={data['app']}",
             "--workdir", data["workspace"], data["sandbox"]]
    if command:
        argv += ["bash", "-c", "source ~/.demo-sandbox.bashrc\n" + command]
    else:
        argv += ["bash", "--noprofile", "--rcfile", "/home/agent/.demo-sandbox.bashrc", "-i"]
    finish = "Close the agent to finish this recording." if command else "Type exit when the take is finished."
    print(f"Recording: {recording}\n{finish}", flush=True)
    env = credential_env(data["speedscale_config"], data.get("app_url", APP_URL))
    env.pop("DEV_SPEEDSCALE_API_KEY", None)
    rec_args = ["asciinema", "record", "--return", "--output-format", "asciicast-v2",
                "--idle-time-limit", "2", "--title", f"Speedscale {data['language']} {path.name}",
                "--command", shlex.join(argv)]
    if headless:
        rec_args += ["--headless", "--window-size", "120x32"]
    try:
        result = subprocess.run(rec_args + [str(recording)], env=env)
    finally:
        if recording.exists():
            run("asciinema", "convert", recording, recording.with_suffix(".txt"))
            print(f"Saved playback and transcript in {recording.parent}")
    if result.returncode:
        raise subprocess.CalledProcessError(result.returncode, rec_args)


def video(recording):
    recording = Path(recording).resolve()
    if not recording.is_file() or recording.suffix != ".cast":
        raise ValueError("Supply a local .cast recording")
    for executable in ("agg", "ffmpeg"):
        if not shutil.which(executable):
            raise ValueError(f"Missing video prerequisite: {executable}")
    target = recording.with_suffix(".mp4")
    if target.exists():
        raise ValueError(f"Video already exists: {target}")
    with tempfile.TemporaryDirectory(prefix="demo-video-", dir=recording.parent) as scratch:
        gif = Path(scratch) / "terminal.gif"
        run("agg", "--theme", "dracula", "--font-size", "22", "--idle-time-limit", "2",
            recording, gif)
        run("ffmpeg", "-hide_banner", "-loglevel", "error", "-n", "-i", gif,
            "-vf", "scale=trunc(iw/2)*2:trunc(ih/2)*2", "-c:v", "libx264", "-crf", "16",
            "-pix_fmt", "yuv420p", "-movflags", "+faststart", target)
    print("Saved terminal video:", target)


def main():
    parser = argparse.ArgumentParser(prog="ai-sandbox", description="Run ai-sandbox to create a fresh Node take in this terminal. Other commands manage existing takes.")
    parser.add_argument("--language", choices=PROFILES, default="node",
                        help="runtime for a new sandbox (default: node)")
    commands = parser.add_subparsers(dest="action")
    for action in ("build", "new"):
        p = commands.add_parser(action)
        p.add_argument("language", choices=PROFILES, nargs="?", default="node")
        if action == "new":
            p.add_argument("--no-open", action="store_true")
    for action in ("open", "terminal", "auth", "ports", "stop", "remove", *AGENTS):
        p = commands.add_parser(action)
        p.add_argument("take", nargs="?", default="latest")
        if action == "terminal":
            p.add_argument("--command")
            p.add_argument("--headless", action="store_true")
    commands.add_parser("list")
    p = commands.add_parser("video")
    p.add_argument("recording")
    args = parser.parse_args()
    for executable in ("docker", "sbx", "git", "asciinema"):
        if not shutil.which(executable):
            raise ValueError(f"Missing prerequisite: {executable}")
    if args.action is None:
        identifier = new(args.language, no_open=True)
        terminal(identifier)
    elif args.action == "video":
        video(args.recording)
    elif args.action == "build":
        build(args.language)
    elif args.action == "new":
        new(args.language, args.no_open)
    elif args.action == "open":
        open_terminal(args.take)
    elif args.action == "terminal":
        terminal(args.take, args.command, args.headless)
    elif args.action in AGENTS:
        agent(args.take, args.action)
    elif args.action == "auth":
        configure(args.take)
    elif args.action == "ports":
        _, data = session(args.take)
        run("sbx", "ports", data["sandbox"])
    elif args.action == "list":
        for state in sorted(RUNS.glob("*/session.json")):
            data = json.loads(state.read_text())
            print(f"{data['id']}  {data['status']}  {data['sandbox']}")
    else:
        path, data = session(args.take, allow_failed=args.action == "remove")
        run("sbx", "stop" if args.action == "stop" else "rm", data["sandbox"])
        data["status"] = "stopped" if args.action == "stop" else "removed"
        save(path, data)
        print("Workspace and recordings retained:", path)


if __name__ == "__main__":
    try:
        main()
    except (ValueError, subprocess.CalledProcessError) as error:
        print(f"Error: {error}", file=sys.stderr)
        sys.exit(1)
    except KeyboardInterrupt:
        sys.exit(130)
