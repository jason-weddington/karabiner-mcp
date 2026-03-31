"""Compiler and decompiler between ManipulatorIR and Karabiner JSON.

Pure functions, no I/O.
"""

from typing import Any

from karabiner_mcp.service.ir import (
    AppCondition,
    DecompileResult,
    DeviceCondition,
    DeviceIdentifiers,
    ManipulatorIR,
    ToKeySpec,
)


def ir_to_manipulator(ir: ManipulatorIR) -> dict[str, Any]:
    """Compile a ManipulatorIR into a Karabiner manipulator dict."""
    from_spec: dict[str, Any] = {}
    if ir.from_key_code:
        from_spec["key_code"] = ir.from_key_code
    else:
        from_spec["pointing_button"] = ir.from_pointing_button

    modifiers: dict[str, list[str]] = {}
    if ir.from_mandatory_modifiers:
        modifiers["mandatory"] = list(ir.from_mandatory_modifiers)
    if ir.from_optional_modifiers:
        modifiers["optional"] = list(ir.from_optional_modifiers)
    if modifiers:
        from_spec["modifiers"] = modifiers

    result: dict[str, Any] = {
        "type": "basic",
        "from": from_spec,
    }

    if ir.to:
        result["to"] = [_to_key_spec_to_dict(t) for t in ir.to]

    if ir.to_shell_command:
        to_list = result.get("to", [])
        to_list.append({"shell_command": ir.to_shell_command})
        result["to"] = to_list

    if ir.to_if_alone:
        result["to_if_alone"] = [
            _to_key_spec_to_dict(t) for t in ir.to_if_alone
        ]

    if ir.to_if_held_down:
        result["to_if_held_down"] = [
            _to_key_spec_to_dict(t) for t in ir.to_if_held_down
        ]

    if ir.conditions:
        cond_list: list[dict[str, Any]] = []
        for cond in ir.conditions:
            if isinstance(cond, DeviceCondition):
                cond_list.append({
                    "type": cond.type,
                    "identifiers": [
                        {k: v for k, v in ident.model_dump().items()
                         if v is not None}
                        for ident in cond.identifiers
                    ],
                })
            else:
                cond_list.append({
                    "type": cond.type,
                    "bundle_identifiers": list(cond.bundle_identifiers),
                })
        result["conditions"] = cond_list

    if ir.parameters:
        result["parameters"] = dict(ir.parameters)

    return result


def _to_key_spec_to_dict(spec: ToKeySpec) -> dict[str, Any]:
    """Convert a ToKeySpec to a Karabiner dict."""
    d: dict[str, Any] = {}
    if spec.key_code:
        d["key_code"] = spec.key_code
    else:
        d["pointing_button"] = spec.pointing_button
    if spec.modifiers:
        d["modifiers"] = list(spec.modifiers)
    return d


def ir_to_rule(
    description: str, manipulators: list[ManipulatorIR]
) -> dict[str, Any]:
    """Compile a list of ManipulatorIRs into a complete Karabiner rule."""
    return {
        "description": description,
        "manipulators": [ir_to_manipulator(ir) for ir in manipulators],
    }


def manipulator_to_ir(manipulator: dict[str, Any]) -> DecompileResult:
    """Decompile a Karabiner manipulator dict into a DecompileResult.

    Returns ir=None for unsupported patterns (non-basic type, simultaneous,
    mouse_key, etc.).
    """
    raw = dict(manipulator)

    # Non-basic types are not supported
    if manipulator.get("type") != "basic":
        return DecompileResult(
            ir=None,
            unsupported_fields=["type"],
            raw=raw,
        )

    from_spec = manipulator.get("from", {})

    # Simultaneous keys not supported
    if "simultaneous" in from_spec:
        return DecompileResult(
            ir=None,
            unsupported_fields=["from.simultaneous"],
            raw=raw,
        )

    # Determine from source: key_code or pointing_button
    from_key_code = from_spec.get("key_code", "")
    from_pointing_button = from_spec.get("pointing_button", "")

    # Must have exactly one of key_code or pointing_button
    if not from_key_code and not from_pointing_button:
        return DecompileResult(
            ir=None,
            unsupported_fields=["from.key_code (missing)"],
            raw=raw,
        )

    modifiers = from_spec.get("modifiers", {})
    from_mandatory = modifiers.get("mandatory", [])
    from_optional = modifiers.get("optional", [])

    unsupported_fields: list[str] = []

    # Parse to keys
    to_keys: list[ToKeySpec] = []
    shell_command: str | None = None
    for to_item in manipulator.get("to", []):
        if "shell_command" in to_item:
            shell_command = to_item["shell_command"]
        elif "key_code" in to_item:
            to_keys.append(
                ToKeySpec(
                    key_code=to_item["key_code"],
                    modifiers=to_item.get("modifiers", []),
                )
            )
        elif "pointing_button" in to_item:
            to_keys.append(
                ToKeySpec(
                    pointing_button=to_item["pointing_button"],
                    modifiers=to_item.get("modifiers", []),
                )
            )
        elif "set_variable" in to_item:
            unsupported_fields.append("to.set_variable")
        elif "mouse_key" in to_item:
            unsupported_fields.append("to.mouse_key")
        elif "software_function" in to_item:
            unsupported_fields.append("to.software_function")
        elif "select_input_source" in to_item:
            unsupported_fields.append("to.select_input_source")
        else:
            unsupported_fields.append("to (unknown shape)")

    # Parse to_if_alone
    to_if_alone: list[ToKeySpec] = []
    for item in manipulator.get("to_if_alone", []):
        if "key_code" in item:
            to_if_alone.append(
                ToKeySpec(
                    key_code=item["key_code"],
                    modifiers=item.get("modifiers", []),
                )
            )
        else:
            unsupported_fields.append("to_if_alone (non-key)")

    # Parse to_if_held_down
    to_if_held_down: list[ToKeySpec] = []
    for item in manipulator.get("to_if_held_down", []):
        if "key_code" in item:
            to_if_held_down.append(
                ToKeySpec(
                    key_code=item["key_code"],
                    modifiers=item.get("modifiers", []),
                )
            )
        elif "pointing_button" in item:
            to_if_held_down.append(
                ToKeySpec(
                    pointing_button=item["pointing_button"],
                    modifiers=item.get("modifiers", []),
                )
            )
        else:
            unsupported_fields.append("to_if_held_down (non-key)")

    # Parse parameters
    parameters: dict[str, int] = {}
    if "parameters" in manipulator:
        params_raw = manipulator["parameters"]
        if isinstance(params_raw, dict):
            for k, v in params_raw.items():
                if isinstance(v, int):
                    parameters[k] = v
                else:
                    unsupported_fields.append(f"parameters.{k}")
        else:
            unsupported_fields.append("parameters")

    # Note unsupported top-level fields
    if "to_after_key_up" in manipulator:
        unsupported_fields.append("to_after_key_up")
    if "to_delayed_action" in manipulator:
        unsupported_fields.append("to_delayed_action")

    # Parse conditions
    conditions: list[AppCondition | DeviceCondition] = []
    for cond in manipulator.get("conditions", []):
        cond_type = cond.get("type", "")
        if cond_type in (
            "frontmost_application_if",
            "frontmost_application_unless",
        ):
            conditions.append(
                AppCondition(
                    type=cond_type,
                    bundle_identifiers=cond.get("bundle_identifiers", []),
                )
            )
        elif cond_type in ("device_if", "device_unless"):
            raw_ids = cond.get("identifiers", [])
            conditions.append(
                DeviceCondition(
                    type=cond_type,
                    identifiers=[
                        DeviceIdentifiers(**ident) for ident in raw_ids
                    ],
                )
            )
        else:
            unsupported_fields.append(f"conditions.{cond_type}")

    ir = ManipulatorIR(
        from_key_code=from_key_code,
        from_pointing_button=from_pointing_button,
        from_mandatory_modifiers=from_mandatory,
        from_optional_modifiers=from_optional,
        to=to_keys,
        to_if_alone=to_if_alone,
        to_if_held_down=to_if_held_down,
        to_shell_command=shell_command,
        conditions=conditions,
        parameters=parameters,
    )

    return DecompileResult(
        ir=ir,
        unsupported_fields=unsupported_fields,
        raw=raw,
    )
