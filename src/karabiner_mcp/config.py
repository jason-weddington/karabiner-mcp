"""Environment-based configuration for karabiner-mcp."""

import os
from pathlib import Path


def get_config_path() -> Path:
    """Return the karabiner.json path from KARABINER_MCP_CONFIG_PATH."""
    raw = os.environ.get(
        "KARABINER_MCP_CONFIG_PATH",
        "~/.config/karabiner/karabiner.json",
    )
    return Path(raw).expanduser()


def get_assets_dir() -> Path:
    """Return the assets directory from KARABINER_MCP_ASSETS_DIR."""
    raw = os.environ.get(
        "KARABINER_MCP_ASSETS_DIR",
        "~/.config/karabiner/assets/complex_modifications",
    )
    return Path(raw).expanduser()


def get_log_level() -> str:
    """Return the log level from KARABINER_MCP_LOG_LEVEL."""
    return os.environ.get("KARABINER_MCP_LOG_LEVEL", "WARNING").upper()
