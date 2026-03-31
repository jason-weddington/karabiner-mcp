"""Profile management tools."""

from typing import Annotated, Any

from fastmcp import Context, FastMCP
from pydantic import Field

from karabiner_mcp.service import karabiner as ksvc


def _get_paths(ctx: Context | None) -> tuple[Any, Any]:
    """Extract config_path and assets_dir from lifespan context."""
    if ctx is None:
        msg = "Context not injected"
        raise RuntimeError(msg)
    lc = ctx.lifespan_context
    return lc["config_path"], lc["assets_dir"]


def register_profile_tools(mcp: FastMCP) -> None:
    """Register profile management tools."""

    @mcp.tool(name="list_profiles")
    async def list_profiles(
        ctx: Context | None = None,
    ) -> str:
        """List all Karabiner-Elements profiles with their rule counts.

        Shows which profile is currently selected. Use select_profile
        to switch the active profile.
        """
        config_path, _ = _get_paths(ctx)

        try:
            config = ksvc.read_config(config_path)
        except FileNotFoundError:
            return (
                f"Error: Karabiner config not found at {config_path}. "
                "Is Karabiner-Elements installed?"
            )

        profiles = ksvc.get_profiles(config)
        if not profiles:
            return "No profiles found in karabiner.json."

        lines: list[str] = ["Profiles:"]
        for p in profiles:
            marker = " (selected)" if p["selected"] else ""
            lines.append(
                f"  {p['index']}. {p['name']}{marker}"
                f" — {p['rule_count']} rules,"
                f" {p['simple_modification_count']} simple mods"
            )
        return "\n".join(lines)

    @mcp.tool(name="select_profile")
    async def select_profile(
        profile_index: Annotated[
            int,
            Field(
                description=(
                    "Index of the profile to activate (0-based). "
                    "Use list_profiles to see available profiles."
                ),
            ),
        ],
        ctx: Context | None = None,
    ) -> str:
        """Switch the active Karabiner-Elements profile.

        Takes effect immediately. Use list_profiles first to see
        available profiles and their indices.
        """
        config_path, _ = _get_paths(ctx)

        try:
            config = ksvc.read_config(config_path)
        except FileNotFoundError:
            return (
                f"Error: Karabiner config not found at {config_path}. "
                "Is Karabiner-Elements installed?"
            )

        try:
            new_config = ksvc.select_profile(config, profile_index)
        except ValueError as e:
            return f"Error: {e}"

        ksvc.write_config(new_config, config_path)

        profiles = ksvc.get_profiles(new_config)
        name = profiles[profile_index]["name"]
        return f"Switched to profile '{name}' (index {profile_index})."
