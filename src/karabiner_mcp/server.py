"""FastMCP server with lifespan management and tool registration."""

import logging
import sys
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any

from fastmcp import FastMCP

from karabiner_mcp.config import get_assets_dir, get_config_path, get_log_level
from karabiner_mcp.tools.keycodes import register_keycode_tools
from karabiner_mcp.tools.profiles import register_profile_tools
from karabiner_mcp.tools.rules import register_rule_tools


@asynccontextmanager
async def lifespan(server: FastMCP) -> AsyncIterator[dict[str, Any]]:
    """Resolve filesystem paths and verify Karabiner config is accessible."""
    log_level = getattr(logging, get_log_level())
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s %(name)s %(levelname)s %(message)s",
        stream=sys.stderr,
    )
    logger = logging.getLogger(__name__)

    config_path = get_config_path()
    assets_dir = get_assets_dir()

    if config_path.exists():
        logger.info("Karabiner config: %s", config_path)
    else:
        logger.warning(
            "Karabiner config not found at %s — tools will fail until"
            " Karabiner-Elements is installed",
            config_path,
        )

    yield {
        "config_path": config_path,
        "assets_dir": assets_dir,
    }


_INSTRUCTIONS = """\
Manage Karabiner-Elements keyboard remapping rules on macOS.

WORKFLOW:
1. search_key_codes to find the correct key code names
2. list_rules to see current rules and their status
3. add_rule to create new remaps, toggle_rule to enable/disable, remove_rule \
to delete

KEY NAMING:
Karabiner uses specific key code strings — not the labels on your keyboard. \
Common gotchas:
- Enter key: "return_or_enter" (not "enter" or "return")
- Backspace: "delete_or_backspace" (not "backspace" or "delete")
- Forward delete: "delete_forward"
- Backtick/tilde: "grave_accent_and_tilde"
- Modifier aliases: "control" means either side, "left_control" is specific
- "any" in optional modifiers means "ignore all other held modifiers"
When unsure, call search_key_codes first.

RULE PATTERNS:
- Simple remap: set from_key_code + to_key_code
- Modifier combo: add from_mandatory_modifiers (e.g. ["command", "shift"])
- Tap vs hold: set to_key_code (held output) + to_if_alone_key_code \
(tap output)
- App-specific: add app_if or app_unless with bundle ID regexes
- Shell command: set to_shell_command instead of to_key_code

SAFETY:
- Changes take effect immediately (Karabiner auto-reloads on file change)
- Backups are created automatically before each write
- Rules are identified by their description string (must be unique)
- toggle_rule is reversible; remove_rule with also_delete_asset=False is \
also recoverable

PROFILES:
Rules belong to a profile. Most users have one profile ("Default").
Use list_profiles to see profiles, select_profile to switch.
Omit profile_index on rule tools to use the currently selected profile.
"""


def create_server() -> FastMCP:
    """Create and configure the MCP server with all tools."""
    mcp = FastMCP(
        "karabiner-mcp",
        instructions=_INSTRUCTIONS,
        lifespan=lifespan,
    )

    register_rule_tools(mcp)
    register_profile_tools(mcp)
    register_keycode_tools(mcp)

    return mcp
