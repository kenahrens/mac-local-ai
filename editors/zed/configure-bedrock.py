#!/usr/bin/env python3
"""Merge native Bedrock model settings into an existing Zed configuration."""

import argparse
import json
import os
from pathlib import Path
import stat
import tempfile


MANTLE_LABELS = {
    "gpt-5.6-sol": "GPT-5.6 Sol",
    "gpt-5.6-terra": "GPT-5.6 Terra",
    "gpt-5.6-luna": "GPT-5.6 Luna",
}


MODEL_SETTINGS = (
    "default_model",
    "inline_assistant_model",
    "commit_message_model",
    "thread_summary_model",
    "compaction_model",
    "subagent_model",
)


def configure(settings, profile, region, model):
    providers = settings.setdefault("language_models", {})
    bedrock = providers.setdefault("bedrock", {})
    bedrock.update(
        authentication_method="named_profile", profile=profile, region=region
    )
    native_id = model.removeprefix("openai.")
    selection = {"provider": "amazon-bedrock", "model": model}
    if native_id in MANTLE_LABELS:
        model = f"openai.{native_id}"
        models = bedrock.setdefault("mantle_available_models", [])
        entry = next((item for item in models if item.get("name") == model), None)
        if entry is None:
            entry = {"name": model}
            models.append(entry)
        entry.update(
            display_name=f"AWS Bedrock - {MANTLE_LABELS[native_id]}",
            max_tokens=1_000_000,
            max_output_tokens=128_000,
            protocol="responses",
            supports_tools=True,
            supports_images=True,
            supports_thinking=True,
        )
        selection.update(model=model, enable_thinking=True, effort="medium")
    agent = settings.setdefault("agent", {})
    for key in MODEL_SETTINGS:
        agent[key] = selection.copy()
    favorites = agent.setdefault("favorite_models", [])
    if native_id in MANTLE_LABELS:
        favorites[:] = [item for item in favorites if not (
            item.get("provider") == "amazon-bedrock" and item.get("model") == native_id
        )]
    favorite = next((item for item in favorites if
                     item.get("provider") == "amazon-bedrock" and item.get("model") == model), None)
    if favorite is None:
        favorites.append(selection.copy())
    else:
        favorite.update(selection)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profile", required=True, help="Existing AWS SSO profile")
    parser.add_argument("--region", required=True, help="Bedrock model's AWS region")
    parser.add_argument("--model", default="gpt-5.6-sol")
    parser.add_argument("--settings", type=Path,
                        default=Path.home() / ".config/zed/settings.json")
    parser.add_argument("--apply", action="store_true", help="Write the merged settings")
    args = parser.parse_args()
    path = args.settings.expanduser().resolve()
    try:
        original = path.read_bytes()
        settings = json.loads(original)
        configure(settings, args.profile, args.region, args.model)
    except json.JSONDecodeError:
        parser.error("Settings must be valid JSON; JSONC comments/trailing commas are not rewritten.")
    except (OSError, TypeError, AttributeError) as error:
        parser.error(str(error))

    updated = (json.dumps(settings, indent=2) + "\n").encode()
    if args.apply and updated != original:
        mode = stat.S_IMODE(path.stat().st_mode)
        fd, temporary = tempfile.mkstemp(prefix=".zed-bedrock-", dir=path.parent)
        try:
            with os.fdopen(fd, "wb") as output:
                output.write(updated)
                output.flush()
                os.fsync(output.fileno())
            os.chmod(temporary, mode)
            if path.read_bytes() != original:
                parser.error("Settings changed while configuring Bedrock; rerun against the new file.")
            os.replace(temporary, path)
        finally:
            if os.path.exists(temporary):
                os.unlink(temporary)

    print(f"{'Applied' if args.apply else 'Preview'}: {path}")
    selected_model = settings["agent"]["default_model"]["model"]
    print(f"AWS profile: {args.profile}; region: {args.region}; model: {selected_model}")
    native_id = args.model.removeprefix("openai.")
    if native_id in MANTLE_LABELS:
        print(f"Picker label: AWS Bedrock - {MANTLE_LABELS[native_id]}")
    print("Zed agent and helper models use Bedrock; existing providers and MCP settings are preserved.")
    if not args.apply:
        print("Add --apply to save these settings.")


if __name__ == "__main__":
    main()
