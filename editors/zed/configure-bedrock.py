#!/usr/bin/env python3
"""Merge native Bedrock model settings into an existing Zed configuration."""

import argparse
import json
import os
from pathlib import Path
import stat
import tempfile


MODEL_CATALOG = json.loads(
    Path(__file__).with_name("bedrock-openai-models.json").read_text()
)["models"]


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
    selected = None
    selections = []
    managed_ids = set()
    for item in MODEL_CATALOG:
        definition = item["model"]
        models = bedrock.setdefault(item["settings_key"], [])
        entry = next((entry for entry in models if entry.get("name") == definition["name"]), None)
        if entry is None:
            models.append(definition.copy())
        else:
            entry.update(definition)
        selection = {"provider": "amazon-bedrock", "model": definition["name"]}
        if definition.get("supports_thinking"):
            selection.update(enable_thinking=True, effort="medium")
        selections.append(selection)
        aliases = {item["native_id"], item["discovery_id"], definition["name"]}
        managed_ids.update(aliases)
        if model in aliases:
            selected = selection
    if selected is None:
        selected = {"provider": "amazon-bedrock", "model": model}
        selections.append(selected)
        managed_ids.add(model)
    agent = settings.setdefault("agent", {})
    for key in MODEL_SETTINGS:
        agent[key] = selected.copy()
    favorites = agent.setdefault("favorite_models", [])
    unrelated = [item for item in favorites if not (
        item.get("provider") == "amazon-bedrock" and item.get("model") in managed_ids
    )]
    favorites[:] = unrelated + [item.copy() for item in selections]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profile", required=True, help="Existing AWS SSO profile")
    parser.add_argument("--region", required=True, help="Bedrock model's AWS region")
    parser.add_argument("--model", default="gpt-6.1-sol")
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
    for item in MODEL_CATALOG:
        if item["model"]["name"] == selected_model:
            print(f"Default picker label: {item['model']['display_name']}")
    print(f"Configured {len(MODEL_CATALOG)} labeled OpenAI catalog entries.")
    print("Zed agent and helper models use Bedrock; existing providers and MCP settings are preserved.")
    if not args.apply:
        print("Add --apply to save these settings.")


if __name__ == "__main__":
    main()
