"""Rule management tools — the core of the MCP server."""

from typing import Annotated, Any

from fastmcp import Context, FastMCP
from pydantic import Field, ValidationError

from karabiner_mcp.service import karabiner as ksvc
from karabiner_mcp.service.compiler import ir_to_rule, manipulator_to_ir
from karabiner_mcp.service.ir import (
    AppCondition,
    DeviceCondition,
    DeviceIdentifiers,
    ManipulatorIR,
    ToKeySpec,
)


def _get_paths(ctx: Context | None) -> tuple[Any, Any]:
    """Extract config_path and assets_dir from lifespan context."""
    if ctx is None:
        msg = "Context not injected"
        raise RuntimeError(msg)
    lc = ctx.lifespan_context
    return lc["config_path"], lc["assets_dir"]


def _resolve_profile(
    config: dict[str, Any], profile_index: int | None
) -> int:
    """Resolve profile index, defaulting to the selected profile."""
    if profile_index is not None:
        return profile_index
    return ksvc.get_selected_profile_index(config)


def _read_config_or_error(config_path: Any) -> dict[str, Any] | str:
    """Read config, returning error string on failure."""
    try:
        return ksvc.read_config(config_path)
    except FileNotFoundError:
        return (
            f"Error: Karabiner config not found at {config_path}. "
            "Is Karabiner-Elements installed?"
        )


def register_rule_tools(mcp: FastMCP) -> None:
    """Register rule management tools."""

    @mcp.tool(name="list_rules")
    async def list_rules(
        profile_index: Annotated[
            int | None,
            Field(
                description=(
                    "Profile index (0-based). "
                    "Omit to use the currently selected profile."
                ),
            ),
        ] = None,
        include_available: Annotated[
            bool,
            Field(
                description=(
                    "Also show rules from asset files "
                    "not yet installed in the profile."
                ),
            ),
        ] = False,
        ctx: Context | None = None,
    ) -> str:
        """List Karabiner-Elements complex modification rules for a profile.

        Returns each rule's description, enabled/disabled status, whether
        it's installed in karabiner.json, and its source asset file.
        Rules are listed in priority order (first match wins in Karabiner).
        """
        config_path, assets_dir = _get_paths(ctx)
        result = _read_config_or_error(config_path)
        if isinstance(result, str):
            return result
        config = result

        idx = _resolve_profile(config, profile_index)
        profiles = ksvc.get_profiles(config)
        if idx < 0 or idx >= len(profiles):
            return f"Error: Profile index {idx} out of range."

        profile = profiles[idx]
        asset_files = ksvc.list_asset_files(assets_dir)
        rules = ksvc.get_rules_with_status(config, idx, asset_files)

        installed = [r for r in rules if r["in_config"]]
        available = [r for r in rules if not r["in_config"]]

        sel = " (selected)" if profile["selected"] else ""
        lines: list[str] = [
            f"Profile: {profile['name']} (index {idx}{sel})"
        ]

        if installed:
            lines.append(f"\nInstalled rules ({len(installed)}):")
            for i, r in enumerate(installed, 1):
                status = "ON" if r["enabled"] else "OFF"
                source = (
                    f"  (source: {r['source_asset']})"
                    if r["source_asset"]
                    else ""
                )
                lines.append(
                    f"  {i}. [{status}] {r['description']}{source}"
                )
        else:
            lines.append("\nNo installed rules.")

        if include_available and available:
            lines.append(
                f"\nAvailable (not installed, {len(available)}):"
            )
            for r in available:
                source = (
                    f"  (source: {r['source_asset']})"
                    if r["source_asset"]
                    else ""
                )
                lines.append(f"  - {r['description']}{source}")

        return "\n".join(lines)

    @mcp.tool(name="add_rule")
    async def add_rule(
        description: Annotated[
            str,
            Field(
                description=(
                    "Human-readable rule description. "
                    "Must be unique across all rules."
                ),
            ),
        ],
        from_key_code: Annotated[
            str | None,
            Field(
                description=(
                    "Trigger key code (e.g. 'caps_lock', 'a', "
                    "'left_command'). Mutually exclusive with "
                    "from_pointing_button."
                ),
            ),
        ] = None,
        from_pointing_button: Annotated[
            str | None,
            Field(
                description=(
                    "Trigger mouse button (e.g. 'button1'). "
                    "Mutually exclusive with from_key_code."
                ),
            ),
        ] = None,
        from_mandatory_modifiers: Annotated[
            list[str] | None,
            Field(
                description=(
                    "Modifiers that must be held for the rule to fire "
                    "(e.g. ['command', 'shift']). "
                    "Use search_key_codes to find valid names."
                ),
            ),
        ] = None,
        from_optional_modifiers: Annotated[
            list[str] | None,
            Field(
                description=(
                    "Modifiers allowed but not required. "
                    "Use ['any'] to ignore all extra modifiers "
                    "(recommended for most remaps)."
                ),
            ),
        ] = None,
        to_key_code: Annotated[
            str | None,
            Field(
                description=(
                    "Output key code (shorthand for a single to-key). "
                    "For multiple outputs or modifiers on output, "
                    "use to_keys instead."
                ),
            ),
        ] = None,
        to_modifiers: Annotated[
            list[str] | None,
            Field(
                description=(
                    "Modifiers to apply to the output key "
                    "(used with to_key_code)."
                ),
            ),
        ] = None,
        to_keys: Annotated[
            list[dict[str, Any]] | None,
            Field(
                description=(
                    "Full output key list. Each entry: "
                    "{key_code, modifiers[], pointing_button}. "
                    "Use instead of to_key_code for multi-key "
                    "or complex outputs."
                ),
            ),
        ] = None,
        to_shell_command: Annotated[
            str | None,
            Field(
                description=(
                    "Shell command to execute when the rule fires "
                    "(e.g. 'open -a Terminal')."
                ),
            ),
        ] = None,
        to_if_alone_key_code: Annotated[
            str | None,
            Field(
                description=(
                    "Key to send if the trigger is tapped briefly "
                    "(not held). Common for dual-purpose keys like "
                    "'caps_lock as escape when tapped, "
                    "control when held'."
                ),
            ),
        ] = None,
        to_if_held_down_key_code: Annotated[
            str | None,
            Field(
                description=(
                    "Key to send if the trigger is held down "
                    "past the threshold."
                ),
            ),
        ] = None,
        app_if: Annotated[
            list[str] | None,
            Field(
                description=(
                    "Bundle ID regexes — rule only fires in these "
                    "apps (e.g. ['^com\\\\.apple\\\\.Terminal$']). "
                    "Use app_unless for the inverse."
                ),
            ),
        ] = None,
        app_unless: Annotated[
            list[str] | None,
            Field(
                description=(
                    "Bundle ID regexes — rule fires everywhere "
                    "EXCEPT these apps."
                ),
            ),
        ] = None,
        device_if: Annotated[
            list[dict[str, Any]] | None,
            Field(
                description=(
                    "Device identifiers — rule only fires on "
                    "these devices. Each dict may contain: "
                    "vendor_id (int), product_id (int), "
                    "location_id (int), is_keyboard (bool), "
                    "is_pointing_device (bool)."
                ),
            ),
        ] = None,
        device_unless: Annotated[
            list[dict[str, Any]] | None,
            Field(
                description=(
                    "Device identifiers — rule fires on all "
                    "devices EXCEPT these. Same fields as "
                    "device_if."
                ),
            ),
        ] = None,
        profile_index: Annotated[
            int | None,
            Field(
                description=(
                    "Profile to install the rule in. "
                    "Omit for the selected profile."
                ),
            ),
        ] = None,
        asset_title: Annotated[
            str | None,
            Field(
                description=(
                    "Asset file group title. Rules with the same "
                    "title go in the same file. Default: 'MCP Rules'."
                ),
            ),
        ] = None,
        ctx: Context | None = None,
    ) -> str:
        """Create and install a new Karabiner-Elements rule.

        Writes the rule to an asset file AND installs it in karabiner.json
        for immediate effect. Karabiner-Elements auto-reloads on file change.

        For simple remaps, use to_key_code. For tap-vs-hold, combine
        to_key_code (held behavior) with to_if_alone_key_code (tap behavior).

        Examples:
        - Simple remap (caps->esc): from_key_code="caps_lock",
          to_key_code="escape"
        - With modifier (ctrl+h->backspace): from_key_code="h",
          from_mandatory_modifiers=["control"],
          to_key_code="delete_or_backspace"
        - Tap/hold (caps: tap=esc, hold=ctrl): from_key_code="caps_lock",
          to_key_code="left_control", to_if_alone_key_code="escape"
        - App-specific: add app_if=['^com\\.apple\\.Terminal$']
        - Shell command: from_key_code="f5",
          to_shell_command="open -a Safari"
        """
        config_path, assets_dir = _get_paths(ctx)

        # Validate inputs
        if not from_key_code and not from_pointing_button:
            return (
                "Error: Either from_key_code or from_pointing_button "
                "is required. Use search_key_codes to find valid names."
            )
        if not to_key_code and not to_keys and not to_shell_command:
            return (
                "Error: At least one output is required — set to_key_code, "
                "to_keys, or to_shell_command."
            )

        # Build to list
        to_list: list[ToKeySpec] = []
        if to_key_code:
            to_list.append(
                ToKeySpec(
                    key_code=to_key_code,
                    modifiers=to_modifiers or [],
                )
            )
        elif to_keys:
            for tk in to_keys:
                to_list.append(
                    ToKeySpec(
                        key_code=tk.get("key_code", ""),
                        pointing_button=tk.get("pointing_button", ""),
                        modifiers=tk.get("modifiers", []),
                    )
                )

        # Build conditions
        conditions: list[AppCondition | DeviceCondition] = []
        if app_if:
            conditions.append(
                AppCondition(
                    type="frontmost_application_if",
                    bundle_identifiers=app_if,
                )
            )
        if app_unless:
            conditions.append(
                AppCondition(
                    type="frontmost_application_unless",
                    bundle_identifiers=app_unless,
                )
            )
        if device_if:
            conditions.append(
                DeviceCondition(
                    type="device_if",
                    identifiers=[
                        DeviceIdentifiers(**d) for d in device_if
                    ],
                )
            )
        if device_unless:
            conditions.append(
                DeviceCondition(
                    type="device_unless",
                    identifiers=[
                        DeviceIdentifiers(**d) for d in device_unless
                    ],
                )
            )

        # Build to_if_alone / to_if_held_down
        alone_list: list[ToKeySpec] = []
        if to_if_alone_key_code:
            alone_list.append(ToKeySpec(key_code=to_if_alone_key_code))
        held_list: list[ToKeySpec] = []
        if to_if_held_down_key_code:
            held_list.append(ToKeySpec(key_code=to_if_held_down_key_code))

        # Create IR
        try:
            ir = ManipulatorIR(
                from_key_code=from_key_code or "",
                from_pointing_button=from_pointing_button or "",
                from_mandatory_modifiers=from_mandatory_modifiers or [],
                from_optional_modifiers=from_optional_modifiers or [],
                to=to_list,
                to_if_alone=alone_list,
                to_if_held_down=held_list,
                to_shell_command=to_shell_command,
                conditions=conditions,
            )
        except ValidationError as e:
            return f"Error: Invalid rule parameters — {e}"

        # Compile to Karabiner JSON
        rule_dict = ir_to_rule(description, [ir])

        # Write to asset file
        title = asset_title or "MCP Rules"
        filename = ksvc.slugify_title(title) + ".json"
        try:
            existing = ksvc.read_asset_file(filename, assets_dir)
            # Check for duplicate description in asset
            for r in existing["rules"]:
                if r.get("description") == description:
                    return (
                        f"Error: A rule named '{description}' already "
                        f"exists in asset file '{filename}'."
                    )
            rules = [*existing["rules"], rule_dict]
        except FileNotFoundError:
            rules = [rule_dict]
        ksvc.write_asset_file(title, rules, assets_dir, filename=filename)

        # Install into karabiner.json
        result = _read_config_or_error(config_path)
        if isinstance(result, str):
            return result
        config = result

        idx = _resolve_profile(config, profile_index)

        # Check for duplicate in config
        existing_rules = ksvc.get_profile_rules(config, idx)
        for r in existing_rules:
            if r.get("description") == description:
                return (
                    f"Error: A rule named '{description}' is already "
                    "installed in this profile."
                )

        try:
            new_config = ksvc.install_rule(config, idx, rule_dict)
        except ValueError as e:
            return f"Error: {e}"

        ksvc.write_config(new_config, config_path)
        return (
            f"Created and installed rule '{description}'. "
            f"Asset file: {filename}. "
            "Karabiner will auto-reload."
        )

    @mcp.tool(name="toggle_rule")
    async def toggle_rule(
        description: Annotated[
            str,
            Field(
                description="Exact description of the rule to toggle.",
            ),
        ],
        enabled: Annotated[
            bool,
            Field(description="True to enable, False to disable."),
        ],
        profile_index: Annotated[
            int | None,
            Field(
                description=(
                    "Profile index. Omit for the selected profile."
                ),
            ),
        ] = None,
        ctx: Context | None = None,
    ) -> str:
        """Enable or disable an installed rule.

        The rule stays in karabiner.json either way — disabling adds
        'enabled: false', enabling removes that flag.
        """
        config_path, _ = _get_paths(ctx)
        result = _read_config_or_error(config_path)
        if isinstance(result, str):
            return result
        config = result

        idx = _resolve_profile(config, profile_index)
        try:
            new_config = ksvc.set_rule_enabled(
                config, idx, description, enabled=enabled
            )
        except ValueError as e:
            return f"Error: {e}"

        ksvc.write_config(new_config, config_path)
        state = "enabled" if enabled else "disabled"
        return f"Rule '{description}' {state}."

    @mcp.tool(name="remove_rule")
    async def remove_rule(
        description: Annotated[
            str,
            Field(
                description=(
                    "Exact description of the rule to remove."
                ),
            ),
        ],
        also_delete_asset: Annotated[
            bool,
            Field(
                description=(
                    "Also remove the rule from its source asset file. "
                    "Default: False (keeps asset so rule can be "
                    "re-installed later)."
                ),
            ),
        ] = False,
        ctx: Context | None = None,
    ) -> str:
        """Remove a rule from karabiner.json (all profiles).

        By default the asset file is preserved so the rule can be
        re-added later via the Karabiner Settings UI or add_rule.
        """
        config_path, assets_dir = _get_paths(ctx)
        result = _read_config_or_error(config_path)
        if isinstance(result, str):
            return result
        config = result

        new_config = ksvc.remove_rules_from_config(
            config, {description}
        )
        ksvc.write_config(new_config, config_path)

        parts = [f"Removed rule '{description}' from karabiner.json."]

        if also_delete_asset:
            asset_files = ksvc.list_asset_files(assets_dir)
            for asset in asset_files:
                remaining = [
                    r
                    for r in asset["rules"]
                    if r.get("description") != description
                ]
                if len(remaining) < len(asset["rules"]):
                    if remaining:
                        ksvc.write_asset_file(
                            asset["title"],
                            remaining,
                            assets_dir,
                            filename=asset["filename"],
                        )
                        parts.append(
                            f"Removed from asset '{asset['filename']}' "
                            f"({len(remaining)} rules remain)."
                        )
                    else:
                        ksvc.delete_asset_file(
                            asset["filename"], assets_dir
                        )
                        parts.append(
                            f"Deleted empty asset '{asset['filename']}'."
                        )
        else:
            parts.append("Asset file preserved.")

        return " ".join(parts)

    @mcp.tool(name="edit_rule")
    async def edit_rule(
        description: Annotated[
            str,
            Field(
                description=(
                    "Exact description of the rule to edit."
                ),
            ),
        ],
        new_description: Annotated[
            str | None,
            Field(
                description="New description. None = keep current.",
            ),
        ] = None,
        from_key_code: Annotated[
            str | None,
            Field(description="New trigger key code. None = keep current."),
        ] = None,
        from_pointing_button: Annotated[
            str | None,
            Field(
                description=(
                    "New trigger mouse button. None = keep current."
                ),
            ),
        ] = None,
        from_mandatory_modifiers: Annotated[
            list[str] | None,
            Field(
                description=(
                    "New mandatory modifiers. None = keep current."
                ),
            ),
        ] = None,
        from_optional_modifiers: Annotated[
            list[str] | None,
            Field(
                description=(
                    "New optional modifiers. None = keep current."
                ),
            ),
        ] = None,
        to_key_code: Annotated[
            str | None,
            Field(description="New output key code. None = keep current."),
        ] = None,
        to_modifiers: Annotated[
            list[str] | None,
            Field(
                description=(
                    "New output modifiers (with to_key_code). "
                    "None = keep current."
                ),
            ),
        ] = None,
        to_shell_command: Annotated[
            str | None,
            Field(
                description="New shell command. None = keep current.",
            ),
        ] = None,
        to_if_alone_key_code: Annotated[
            str | None,
            Field(description="New tap key code. None = keep current."),
        ] = None,
        to_if_held_down_key_code: Annotated[
            str | None,
            Field(description="New hold key code. None = keep current."),
        ] = None,
        app_if: Annotated[
            list[str] | None,
            Field(
                description=(
                    "New app_if bundle IDs. None = keep current. "
                    "Pass [] to clear."
                ),
            ),
        ] = None,
        app_unless: Annotated[
            list[str] | None,
            Field(
                description=(
                    "New app_unless bundle IDs. None = keep current. "
                    "Pass [] to clear."
                ),
            ),
        ] = None,
        device_if: Annotated[
            list[dict[str, Any]] | None,
            Field(
                description=(
                    "New device_if identifiers. None = keep current. "
                    "Pass [] to clear."
                ),
            ),
        ] = None,
        device_unless: Annotated[
            list[dict[str, Any]] | None,
            Field(
                description=(
                    "New device_unless identifiers. "
                    "None = keep current. Pass [] to clear."
                ),
            ),
        ] = None,
        ctx: Context | None = None,
    ) -> str:
        """Edit an existing rule. Updates both the asset file and
        karabiner.json. Only pass the parameters you want to change.

        To see a rule's current configuration, use list_rules first.
        """
        config_path, assets_dir = _get_paths(ctx)
        result = _read_config_or_error(config_path)
        if isinstance(result, str):
            return result
        config = result

        # Find the rule in config
        all_rules = []
        for profile in config.get("profiles", []):
            cm = profile.get("complex_modifications", {})
            all_rules.extend(cm.get("rules", []))

        target = None
        for r in all_rules:
            if r.get("description") == description:
                target = r
                break

        if target is None:
            # Try asset files
            asset_files = ksvc.list_asset_files(assets_dir)
            for asset in asset_files:
                for r in asset["rules"]:
                    if r.get("description") == description:
                        target = r
                        break
                if target is not None:
                    break

        if target is None:
            return (
                f"Error: Rule '{description}' not found in config "
                "or asset files."
            )

        # Decompile the first manipulator
        manips = target.get("manipulators", [])
        if not manips:
            return (
                f"Error: Rule '{description}' has no manipulators."
            )

        dr = manipulator_to_ir(manips[0])
        if dr.ir is None:
            return (
                f"Error: Rule '{description}' uses unsupported "
                f"features ({', '.join(dr.unsupported_fields)}) "
                "and cannot be edited through this tool."
            )

        # Apply overrides
        ir = dr.ir
        if from_key_code is not None:
            ir.from_key_code = from_key_code
            ir.from_pointing_button = ""
        if from_pointing_button is not None:
            ir.from_pointing_button = from_pointing_button
            ir.from_key_code = ""
        if from_mandatory_modifiers is not None:
            ir.from_mandatory_modifiers = from_mandatory_modifiers
        if from_optional_modifiers is not None:
            ir.from_optional_modifiers = from_optional_modifiers

        if to_key_code is not None:
            ir.to = [
                ToKeySpec(
                    key_code=to_key_code,
                    modifiers=to_modifiers or [],
                )
            ]
        elif to_modifiers is not None and ir.to:
            ir.to[0].modifiers = to_modifiers

        if to_shell_command is not None:
            ir.to_shell_command = to_shell_command

        if to_if_alone_key_code is not None:
            ir.to_if_alone = (
                [ToKeySpec(key_code=to_if_alone_key_code)]
                if to_if_alone_key_code
                else []
            )
        if to_if_held_down_key_code is not None:
            ir.to_if_held_down = (
                [ToKeySpec(key_code=to_if_held_down_key_code)]
                if to_if_held_down_key_code
                else []
            )

        if app_if is not None:
            # Remove existing app_if conditions, add new
            ir.conditions = [
                c
                for c in ir.conditions
                if c.type != "frontmost_application_if"
            ]
            if app_if:
                ir.conditions.append(
                    AppCondition(
                        type="frontmost_application_if",
                        bundle_identifiers=app_if,
                    )
                )
        if app_unless is not None:
            ir.conditions = [
                c
                for c in ir.conditions
                if c.type != "frontmost_application_unless"
            ]
            if app_unless:
                ir.conditions.append(
                    AppCondition(
                        type="frontmost_application_unless",
                        bundle_identifiers=app_unless,
                    )
                )
        if device_if is not None:
            ir.conditions = [
                c
                for c in ir.conditions
                if not (
                    isinstance(c, DeviceCondition)
                    and c.type == "device_if"
                )
            ]
            if device_if:
                ir.conditions.append(
                    DeviceCondition(
                        type="device_if",
                        identifiers=[
                            DeviceIdentifiers(**d) for d in device_if
                        ],
                    )
                )
        if device_unless is not None:
            ir.conditions = [
                c
                for c in ir.conditions
                if not (
                    isinstance(c, DeviceCondition)
                    and c.type == "device_unless"
                )
            ]
            if device_unless:
                ir.conditions.append(
                    DeviceCondition(
                        type="device_unless",
                        identifiers=[
                            DeviceIdentifiers(**d)
                            for d in device_unless
                        ],
                    )
                )

        # Revalidate
        try:
            ir = ManipulatorIR(**ir.model_dump())
        except ValidationError as e:
            return f"Error: Invalid edited rule — {e}"

        final_desc = new_description or description
        new_rule = ir_to_rule(final_desc, [ir])

        # Update karabiner.json
        new_config = ksvc.update_rule_in_config(
            config, description, new_rule
        )
        ksvc.write_config(new_config, config_path)

        # Update asset file
        asset_files = ksvc.list_asset_files(assets_dir)
        for asset in asset_files:
            updated_rules = []
            found_in_asset = False
            for r in asset["rules"]:
                if r.get("description") == description:
                    updated_rules.append(new_rule)
                    found_in_asset = True
                else:
                    updated_rules.append(r)
            if found_in_asset:
                ksvc.write_asset_file(
                    asset["title"],
                    updated_rules,
                    assets_dir,
                    filename=asset["filename"],
                )

        return (
            f"Updated rule '{final_desc}'. "
            "Karabiner will auto-reload."
        )
