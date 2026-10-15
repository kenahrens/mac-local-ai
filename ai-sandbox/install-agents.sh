#!/usr/bin/env bash
set -euo pipefail
source "$HOME/.demo-sandbox.bashrc"
export PATH="$HOME/.local/bin:$PATH"
export npm_config_prefix="$HOME/.local"
export npm_config_update_notifier=false
scratch=$(mktemp -d)
trap 'rm -rf "$scratch"' EXIT

if ! command -v node >/dev/null || ! node -e '
    const [major, minor] = process.versions.node.split(".").map(Number);
    process.exit(major > 22 || (major === 22 && minor >= 19) ? 0 : 1);
' || ! command -v npm >/dev/null; then
    case "$(uname -m)" in
        aarch64|arm64) arch=arm64 ;;
        x86_64) arch=x64 ;;
        *) echo "Unsupported Node architecture: $(uname -m)" >&2; exit 1 ;;
    esac
    curl --fail --location --silent --show-error --retry 3 \
        https://nodejs.org/dist/latest-v24.x/SHASUMS256.txt -o "$scratch/SHASUMS256.txt"
    checksum=$(awk -v arch="$arch" '$2 ~ "^node-v24[.][0-9]+[.][0-9]+-linux-" arch "[.]tar[.]gz$" {print}' "$scratch/SHASUMS256.txt")
    test -n "$checksum"
    archive=$(printf '%s\n' "$checksum" | awk '{print $2}')
    curl --fail --location --silent --show-error --retry 3 \
        "https://nodejs.org/dist/latest-v24.x/$archive" -o "$scratch/$archive"
    printf '%s\n' "$checksum" | (cd "$scratch" && sha256sum --check -)
    mkdir -p "$HOME/.local"
    tar -xzf "$scratch/$archive" --strip-components=1 -C "$HOME/.local"
fi

if ! command -v claude >/dev/null; then
    curl --fail --location --silent --show-error --retry 3 https://claude.ai/install.sh -o "$scratch/claude.sh"
    bash "$scratch/claude.sh" stable
fi
if ! command -v codex >/dev/null; then
    curl --fail --location --silent --show-error --retry 3 https://chatgpt.com/codex/install.sh -o "$scratch/codex.sh"
    CODEX_NON_INTERACTIVE=1 sh "$scratch/codex.sh"
fi
opencode_v2() {
    command -v opencode >/dev/null || return
    local version
    version=$(opencode --version) || return
    [[ "$version" == 2.* || "$version" == "opencode v2."* ]]
}
if ! opencode_v2; then
    npm install --global --no-audit --no-fund --allow-scripts=@opencode/cli '@opencode/cli@2'
fi
if ! command -v pi >/dev/null; then
    npm install --global --no-audit --no-fund --ignore-scripts @earendil-works/pi-coding-agent
fi
if ! command -v kilo >/dev/null; then
    npm install --global --no-audit --no-fund --allow-scripts=@kilocode/cli @kilocode/cli
fi

opencode_v2 || { echo 'OpenCode 2.x is required.' >&2; exit 1; }
for agent in claude codex opencode pi kilo; do
    printf '%s: ' "$agent"
    "$agent" --version
done
