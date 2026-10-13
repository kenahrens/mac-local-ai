# ai-sandbox

Create a clean Docker Sandbox for a Speedscale recording session. Run one command from the directory you want mounted. The launcher selects one language runtime, installs Claude Code and Codex, copies the public mock-lab source into the guest, and records each terminal session locally with asciinema.

Proxymock and its testing skills are installed during the demonstration by following the [Speedscale installation instructions](https://docs.speedscale.com/proxymock/#getting-started-in-30-seconds). The source package contains no agent credentials or Speedscale configuration files.

## Requirements

Use macOS with Python 3.12 or newer, Docker Desktop, Docker's `sbx` CLI, Git and asciinema on PATH. MP4 export also needs `agg` and ffmpeg. Claude and Codex require separate account sign-ins inside each fresh guest. The launcher reads an existing Speedscale configuration file and supplies its active key at runtime; it does not register an account.

## Start a recording

Add the executable `ai-sandbox` to your PATH. From the root of this repository, the following creates the link without overwriting an existing command:

```sh
mkdir -p "$HOME/.local/bin"
ln -s "$PWD/ai-sandbox/ai-sandbox" "$HOME/.local/bin/ai-sandbox"
```

Make sure `~/.local/bin` is on PATH, then run from your app directory. The launcher resolves its location through the symlink.

The defaults use `~/.speedscale/dev.yaml` and `dev.speedscale.com`. Select your own configuration file and API hostname with `AI_SANDBOX_CONFIG` and `AI_SANDBOX_APP_URL`. Both JSON and YAML configurations are supported. Use a hostname without a URL scheme. The selected file and hostname are retained in session metadata for reopening that session.

```sh
export AI_SANDBOX_CONFIG="$HOME/.speedscale/dev.yaml"
export AI_SANDBOX_APP_URL=dev.speedscale.com
ai-sandbox
```

The current directory is mounted read-write. The selected configuration file is mounted read-only. The launcher creates a fresh Node sandbox and starts terminal recording immediately. Setup may open Docker sign-in in your browser. A clean mock-lab copy is stored inside the guest; enter its selected app and start your agent:

```sh
cd "$MOCK_LAB"
claude
```

You can also run `codex`. Follow the official installation prompt to install proxymock. Claude uses a strict guest-local MCP configuration; after installation, populate it with `proxymock mcp json > "$HOME/.ai-sandbox-mcp.json"`. Restart the agent to load its new skills and MCP server. Source `~/.demo-sandbox.bashrc` to refresh the existing shell's certificate environment after initialization.

The recording captures terminal output and timing. Use your screen recorder and microphone for narration, browser activity or webcam video. Type `exit` to finish the terminal recording; the launcher prints its saved location. Avoid printing credentials or dumping the environment while recording.

## Existing sessions

```sh
ai-sandbox terminal
ai-sandbox claude
ai-sandbox codex
ai-sandbox ports
ai-sandbox stop
ai-sandbox list
```

`terminal` opens another recorded shell in the newest recording session, including a stopped session. Add a session ID to select an older one. Sessions marked as validation are excluded from the default selection. Stopping retains the guest state and its account sign-ins. `ai-sandbox remove` deletes the guest while retaining host recordings and mounted workspace files. After removing the newest session, create another or supply an older session ID.

The app, capture ingress and proxymock web ports are published to random loopback ports on the host. `ports` shows the mapping. Guest terminals use their normal localhost ports.

## Other runtimes and video export

```sh
ai-sandbox --language python
ai-sandbox --language go
ai-sandbox --language java
ai-sandbox video /absolute/path/to/recording.cast
```

Each runtime creates a separate sandbox. The image includes only the selected runtime and basic shell utilities, including make. Rebuild an image with `ai-sandbox build node` or the relevant runtime name. The first build requires downloads and available Docker disk space. Node is the validated runtime; the other profiles have not completed end-to-end sandbox validation.

The `.cast` playback and `.txt` transcript are retained under the launcher's local `runs` directory. `video` exports a silent H.264 MP4 beside the cast. Record narration separately. Nothing is uploaded automatically.

## Validation and licensing

The original Node launcher was checked with fresh sandbox creation, current-directory mounting, read-only configuration, authenticated Claude installation of proxymock, dev traffic capture, native mocking and replay, terminal playback, transcript conversion and MP4 export. Authenticated Codex inference remains untested. The portable source export adds configuration selection and a relative launcher. It passed local JSON/YAML checks and a fresh Node sandbox launch from a directory containing spaces, including agent installation, clean-start verification, recorded terminal output and reopening with the saved dev configuration despite conflicting host overrides. Other API hosts have not been exercised end to end. The exact unmodified Speedscale documentation prompt has not been qualified by those earlier custom-prompt tests.

The launcher and environment setup use this repository's [MIT license](../LICENSE). The copied public credential helper retains Apache-2.0; see [NOTICE](NOTICE) and [LICENSE-APACHE-2.0](LICENSE-APACHE-2.0). Docker, runtime images, coding agents and proxymock have their own licenses and account requirements. They are obtained separately from their official sources.
