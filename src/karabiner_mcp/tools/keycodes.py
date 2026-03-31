"""Key code discovery tool."""

from typing import Annotated

from fastmcp import Context, FastMCP
from pydantic import Field

from karabiner_mcp.service.keycodes import KEY_CODES, MODIFIERS, POINTING_BUTTONS


def register_keycode_tools(mcp: FastMCP) -> None:
    """Register key code discovery tools."""

    @mcp.tool(name="search_key_codes")
    async def search_key_codes(
        query: Annotated[
            str | None,
            Field(
                description=(
                    "Search term to filter key codes "
                    "(e.g. 'arrow', 'f1', 'ctrl', 'media'). "
                    "Case-insensitive substring match. "
                    "Omit to list all categories."
                ),
            ),
        ] = None,
        category: Annotated[
            str | None,
            Field(
                description=(
                    "Filter by category: Letters, Numbers, "
                    "Function Keys, Modifiers, Navigation, "
                    "Punctuation, Keypad, Media, International, System."
                ),
            ),
        ] = None,
        ctx: Context | None = None,
    ) -> str:
        """Search valid Karabiner-Elements key codes and modifiers.

        Call this before add_rule or edit_rule to find the correct
        key_code string. Key codes are Karabiner-specific identifiers
        (e.g. 'return_or_enter' not 'enter', 'delete_or_backspace'
        not 'backspace', 'grave_accent_and_tilde' not '`').
        """
        lines: list[str] = []
        q = query.lower() if query else None

        # Filter categories
        categories = KEY_CODES
        if category:
            cat_lower = category.lower()
            matched = {
                k: v
                for k, v in KEY_CODES.items()
                if k.lower() == cat_lower
            }
            if not matched:
                valid = ", ".join(KEY_CODES.keys())
                return (
                    f"Error: Unknown category '{category}'. "
                    f"Valid categories: {valid}"
                )
            categories = matched

        # Search within categories
        for cat_name, codes in categories.items():
            matches = [c for c in codes if q in c.lower()] if q else codes
            if matches:
                lines.append(f"{cat_name}: {', '.join(matches)}")

        # Search modifiers
        mod_matches = MODIFIERS
        if q:
            mod_matches = [m for m in MODIFIERS if q in m.lower()]
        if mod_matches and not category:
            lines.append(
                f"\nModifier names (for from_mandatory_modifiers, "
                f"from_optional_modifiers, to modifiers):\n"
                f"  {', '.join(mod_matches)}\n"
                f"  Special: 'any' (matches any modifier combination)"
            )

        # Search pointing buttons
        btn_matches = POINTING_BUTTONS
        if q:
            btn_matches = [b for b in POINTING_BUTTONS if q in b.lower()]
        if btn_matches and not category:
            if len(btn_matches) <= 5:
                lines.append(
                    f"\nPointing buttons: {', '.join(btn_matches)}"
                )
            else:
                lines.append(
                    f"\nPointing buttons: {btn_matches[0]}..{btn_matches[-1]}"
                    f" ({len(btn_matches)} buttons)"
                )

        if not lines:
            return (
                f"No key codes matching '{query}'. "
                "Try a broader search or omit query to list all."
            )

        header = "Key codes"
        if q:
            header += f" matching '{query}'"
        if category:
            header += f" in {category}"
        return header + ":\n" + "\n".join(lines)
