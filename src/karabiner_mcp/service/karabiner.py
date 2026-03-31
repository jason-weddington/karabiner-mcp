"""Core service for reading/writing Karabiner-Elements configuration.

Pure functions take/return dicts. I/O wrappers handle filesystem access.
"""

import json
import re
import shutil
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

KARABINER_DIR = Path.home() / ".config" / "karabiner"
KARABINER_CONFIG = KARABINER_DIR / "karabiner.json"
ASSETS_DIR = KARABINER_DIR / "assets" / "complex_modifications"
BACKUP_DIR = KARABINER_DIR / "automatic_backups"


# --- I/O Wrappers ---


def read_config(config_path: Path | None = None) -> dict[str, Any]:
    """Read karabiner.json and return parsed dict."""
    path = config_path or KARABINER_CONFIG
    return json.loads(path.read_text(encoding="utf-8"))  # type: ignore[no-any-return]


def write_config(
    config: dict[str, Any], config_path: Path | None = None
) -> None:
    """Write karabiner.json atomically with a backup."""
    path = config_path or KARABINER_CONFIG
    backup_dir = path.parent / "automatic_backups"
    backup_dir.mkdir(parents=True, exist_ok=True)

    if path.exists():
        ts = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
        shutil.copy2(path, backup_dir / f"karabiner_{ts}.json")

    tmp = path.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(config, indent=4, ensure_ascii=False) + "\n")
    tmp.replace(path)


def list_asset_files(
    assets_dir: Path | None = None,
) -> list[dict[str, Any]]:
    """List all .json files in the assets/complex_modifications directory."""
    d = assets_dir or ASSETS_DIR
    if not d.exists():
        return []

    results: list[dict[str, Any]] = []
    for f in sorted(d.glob("*.json")):
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            continue
        results.append(
            {
                "filename": f.name,
                "title": data.get("title", f.stem),
                "rules": data.get("rules", []),
                "rule_count": len(data.get("rules", [])),
            }
        )
    return results


# --- Pure Functions ---


def get_profiles(config: dict[str, Any]) -> list[dict[str, Any]]:
    """Extract profile summaries from config."""
    profiles: list[dict[str, Any]] = []
    for i, p in enumerate(config.get("profiles", [])):
        profiles.append(
            {
                "name": p.get("name", "Unnamed"),
                "selected": p.get("selected", False),
                "index": i,
                "rule_count": len(
                    p.get("complex_modifications", {}).get("rules", [])
                ),
                "simple_modification_count": len(
                    p.get("simple_modifications", [])
                ),
            }
        )
    return profiles


def get_selected_profile_index(config: dict[str, Any]) -> int:
    """Return the index of the selected profile, defaulting to 0."""
    for i, p in enumerate(config.get("profiles", [])):
        if p.get("selected", False):
            return i
    return 0


def get_profile_rules(
    config: dict[str, Any], profile_index: int
) -> list[dict[str, Any]]:
    """Get the complex modification rules for a specific profile."""
    profiles = config.get("profiles", [])
    if profile_index < 0 or profile_index >= len(profiles):
        return []
    profile = profiles[profile_index]
    return list(
        profile.get("complex_modifications", {}).get("rules", [])
    )


def match_rule_to_asset(
    rule: dict[str, Any], asset_files: list[dict[str, Any]]
) -> str | None:
    """Match a rule to its source asset file by description string."""
    desc = rule.get("description", "")
    if not desc:
        return None
    for asset in asset_files:
        for asset_rule in asset.get("rules", []):
            if asset_rule.get("description") == desc:
                return asset.get("filename")
    return None


def get_rules_with_status(
    config: dict[str, Any],
    profile_index: int,
    asset_files: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Build a unified list of rules with enabled/disabled status.

    Active rules come from karabiner.json. Inactive rules come from asset
    files that have no matching description in the active rules.
    """
    active_rules = get_profile_rules(config, profile_index)
    active_descriptions = {
        r.get("description", "") for r in active_rules
    }

    results: list[dict[str, Any]] = []

    for rule in active_rules:
        source = match_rule_to_asset(rule, asset_files)
        results.append(
            {
                "description": rule.get("description", ""),
                "enabled": rule.get("enabled", True),
                "in_config": True,
                "manipulators": rule.get("manipulators", []),
                "source_asset": source,
            }
        )

    for asset in asset_files:
        for rule in asset.get("rules", []):
            desc = rule.get("description", "")
            if desc and desc not in active_descriptions:
                results.append(
                    {
                        "description": desc,
                        "enabled": False,
                        "in_config": False,
                        "manipulators": rule.get("manipulators", []),
                        "source_asset": asset.get("filename"),
                    }
                )

    return results


def set_rule_enabled(
    config: dict[str, Any],
    profile_index: int,
    description: str,
    *,
    enabled: bool,
) -> dict[str, Any]:
    """Enable or disable a rule in karabiner.json by description.

    Enable removes the "enabled" key; disable sets "enabled": false.
    Returns a new config dict (shallow copy of profiles list and rules list).
    Raises ValueError if the profile or rule is not found.
    """
    profiles = config.get("profiles", [])
    if profile_index < 0 or profile_index >= len(profiles):
        msg = f"Profile index {profile_index} out of range"
        raise ValueError(msg)

    profile = profiles[profile_index]
    rules = profile.get("complex_modifications", {}).get("rules", [])

    found = False
    new_rules = []
    for rule in rules:
        if rule.get("description") == description:
            found = True
            rule = dict(rule)
            if enabled:
                rule.pop("enabled", None)
            else:
                rule["enabled"] = False
        new_rules.append(rule)

    if not found:
        msg = f"Rule not found: {description}"
        raise ValueError(msg)

    new_config = dict(config)
    new_profiles = list(profiles)
    new_profile = dict(profile)
    new_cm = dict(new_profile.get("complex_modifications", {}))
    new_cm["rules"] = new_rules
    new_profile["complex_modifications"] = new_cm
    new_profiles[profile_index] = new_profile
    new_config["profiles"] = new_profiles
    return new_config


def select_profile(
    config: dict[str, Any], profile_index: int
) -> dict[str, Any]:
    """Set the selected profile by index.

    Returns a new config dict. Raises ValueError if index is out of range.
    """
    profiles = config.get("profiles", [])
    if profile_index < 0 or profile_index >= len(profiles):
        msg = f"Profile index {profile_index} out of range"
        raise ValueError(msg)

    new_config = dict(config)
    new_profiles = []
    for i, p in enumerate(profiles):
        new_p = dict(p)
        new_p["selected"] = i == profile_index
        new_profiles.append(new_p)
    new_config["profiles"] = new_profiles
    return new_config


def install_rule(
    config: dict[str, Any],
    profile_index: int,
    rule_dict: dict[str, Any],
) -> dict[str, Any]:
    """Append a rule to a profile's complex_modifications.rules[].

    Returns a new config dict. Raises ValueError if profile index out of range.
    """
    profiles = config.get("profiles", [])
    if profile_index < 0 or profile_index >= len(profiles):
        msg = f"Profile index {profile_index} out of range"
        raise ValueError(msg)

    profile = profiles[profile_index]
    new_config = dict(config)
    new_profiles = list(profiles)
    new_profile = dict(profile)
    new_cm = dict(new_profile.get("complex_modifications", {}))
    new_cm["rules"] = [*new_cm.get("rules", []), rule_dict]
    new_profile["complex_modifications"] = new_cm
    new_profiles[profile_index] = new_profile
    new_config["profiles"] = new_profiles
    return new_config


def remove_rules_from_config(
    config: dict[str, Any], descriptions: set[str]
) -> dict[str, Any]:
    """Remove rules matching given descriptions from all profiles.

    Returns a new config dict.
    """
    new_config = dict(config)
    new_profiles = []
    for p in config.get("profiles", []):
        new_p = dict(p)
        cm = new_p.get("complex_modifications", {})
        new_cm = dict(cm)
        new_cm["rules"] = [
            r
            for r in cm.get("rules", [])
            if r.get("description", "") not in descriptions
        ]
        new_p["complex_modifications"] = new_cm
        new_profiles.append(new_p)
    new_config["profiles"] = new_profiles
    return new_config


def update_rule_in_config(
    config: dict[str, Any],
    old_description: str,
    new_rule: dict[str, Any],
) -> dict[str, Any]:
    """Replace a rule in all profiles by matching the old description.

    Returns a new config dict. Used when editing a rule that's already
    installed in karabiner.json -- the asset is updated separately.
    """
    new_config = dict(config)
    new_profiles = []
    for p in config.get("profiles", []):
        new_p = dict(p)
        cm = new_p.get("complex_modifications", {})
        new_cm = dict(cm)
        new_rules = []
        for r in cm.get("rules", []):
            if r.get("description") == old_description:
                updated = dict(new_rule)
                if "enabled" in r:
                    updated["enabled"] = r["enabled"]
                new_rules.append(updated)
            else:
                new_rules.append(r)
        new_cm["rules"] = new_rules
        new_p["complex_modifications"] = new_cm
        new_profiles.append(new_p)
    new_config["profiles"] = new_profiles
    return new_config


# --- Asset File I/O ---


def slugify_title(title: str) -> str:
    """Convert a title to a filesystem-safe slug."""
    slug = title.lower().strip()
    slug = re.sub(r"[^a-z0-9]+", "_", slug)
    slug = slug.strip("_")
    return slug or "untitled"


def write_asset_file(
    title: str,
    rules: list[dict[str, Any]],
    assets_dir: Path | None = None,
    filename: str | None = None,
) -> str:
    """Write an asset file. Returns the filename used."""
    d = assets_dir or ASSETS_DIR
    d.mkdir(parents=True, exist_ok=True)

    if filename is None:
        filename = slugify_title(title) + ".json"

    path = d / filename
    data = {"title": title, "rules": rules}
    path.write_text(
        json.dumps(data, indent=4, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return filename


def delete_asset_file(
    filename: str, assets_dir: Path | None = None
) -> None:
    """Delete an asset file. Raises FileNotFoundError if missing."""
    d = assets_dir or ASSETS_DIR
    path = d / filename
    if not path.exists():
        msg = f"Asset file not found: {filename}"
        raise FileNotFoundError(msg)
    path.unlink()


def read_asset_file(
    filename: str, assets_dir: Path | None = None
) -> dict[str, Any]:
    """Read a single asset file. Raises FileNotFoundError if missing."""
    d = assets_dir or ASSETS_DIR
    path = d / filename
    data = json.loads(path.read_text(encoding="utf-8"))
    return {
        "filename": filename,
        "title": data.get("title", path.stem),
        "rules": data.get("rules", []),
        "rule_count": len(data.get("rules", [])),
    }
