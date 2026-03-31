"""Intermediate Representation for Karabiner manipulators.

The IR captures ~90% of common manipulator patterns in a flat,
form-friendly structure. The compiler converts IR <-> Karabiner JSON.
"""

from pydantic import BaseModel, field_validator, model_validator

from karabiner_mcp.service.keycodes import (
    ALL_KEY_CODES,
    ALL_POINTING_BUTTONS,
    MODIFIERS,
)


def _validate_key_code(v: str) -> str:
    if v not in ALL_KEY_CODES:
        msg = f"Unknown key code: {v}"
        raise ValueError(msg)
    return v


def _validate_pointing_button(v: str) -> str:
    if v not in ALL_POINTING_BUTTONS:
        msg = f"Unknown pointing button: {v}"
        raise ValueError(msg)
    return v


def _validate_modifier(v: str) -> str:
    if v not in MODIFIERS:
        msg = f"Unknown modifier: {v}"
        raise ValueError(msg)
    return v


class ToKeySpec(BaseModel):
    """A single key output with optional modifiers."""

    key_code: str = ""
    pointing_button: str = ""
    modifiers: list[str] = []

    @field_validator("key_code")
    @classmethod
    def validate_key_code(cls, v: str) -> str:
        """Validate key_code against known Karabiner key codes."""
        if not v:
            return v
        return _validate_key_code(v)

    @field_validator("pointing_button")
    @classmethod
    def validate_pointing_button(cls, v: str) -> str:
        """Validate pointing_button against known Karabiner pointing buttons."""
        if not v:
            return v
        return _validate_pointing_button(v)

    @field_validator("modifiers")
    @classmethod
    def validate_modifiers(cls, v: list[str]) -> list[str]:
        """Validate each modifier against known Karabiner modifiers."""
        return [_validate_modifier(m) for m in v]

    @model_validator(mode="after")
    def check_key_or_button(self) -> "ToKeySpec":
        """Exactly one of key_code or pointing_button must be set."""
        if self.key_code and self.pointing_button:
            msg = "ToKeySpec: set key_code or pointing_button, not both"
            raise ValueError(msg)
        if not self.key_code and not self.pointing_button:
            msg = "ToKeySpec: one of key_code or pointing_button is required"
            raise ValueError(msg)
        return self


class AppCondition(BaseModel):
    """A frontmost application condition."""

    type: str
    bundle_identifiers: list[str]

    @field_validator("type")
    @classmethod
    def validate_type(cls, v: str) -> str:
        """Validate condition type is a supported frontmost_application variant."""
        allowed = {"frontmost_application_if", "frontmost_application_unless"}
        if v not in allowed:
            msg = f"Condition type must be one of {allowed}, got: {v}"
            raise ValueError(msg)
        return v


class DeviceIdentifiers(BaseModel):
    """Device identifiers for a device condition."""

    vendor_id: int | None = None
    product_id: int | None = None
    location_id: int | None = None
    is_keyboard: bool | None = None
    is_pointing_device: bool | None = None


class DeviceCondition(BaseModel):
    """A device_if / device_unless condition."""

    type: str
    identifiers: list[DeviceIdentifiers]

    @field_validator("type")
    @classmethod
    def validate_type(cls, v: str) -> str:
        """Validate condition type is a supported device variant."""
        allowed = {"device_if", "device_unless"}
        if v not in allowed:
            msg = f"Condition type must be one of {allowed}, got: {v}"
            raise ValueError(msg)
        return v


class ManipulatorIR(BaseModel):
    """Intermediate representation for a single Karabiner manipulator.

    Covers key-to-key remaps, modifiers, app conditions, to_if_alone,
    and shell commands. Unsupported features (variables, simultaneous,
    mouse_key, etc.) are handled by the decompiler's fallback path.
    """

    from_key_code: str = ""
    from_pointing_button: str = ""
    from_mandatory_modifiers: list[str] = []
    from_optional_modifiers: list[str] = []
    to: list[ToKeySpec] = []
    to_if_alone: list[ToKeySpec] = []
    to_if_held_down: list[ToKeySpec] = []
    to_shell_command: str | None = None
    conditions: list[AppCondition | DeviceCondition] = []
    parameters: dict[str, int] = {}

    @field_validator("from_key_code")
    @classmethod
    def validate_from_key_code(cls, v: str) -> str:
        """Validate from_key_code against known Karabiner key codes."""
        if not v:
            return v
        return _validate_key_code(v)

    @field_validator("from_pointing_button")
    @classmethod
    def validate_from_pointing_button(cls, v: str) -> str:
        """Validate from_pointing_button against known Karabiner pointing buttons."""
        if not v:
            return v
        return _validate_pointing_button(v)

    @field_validator("from_mandatory_modifiers", "from_optional_modifiers")
    @classmethod
    def validate_from_modifiers(cls, v: list[str]) -> list[str]:
        """Validate each from-modifier against known Karabiner modifiers."""
        return [_validate_modifier(m) for m in v]

    @model_validator(mode="after")
    def check_from_key_or_button(self) -> "ManipulatorIR":
        """Exactly one of from_key_code or from_pointing_button must be set."""
        if self.from_key_code and self.from_pointing_button:
            msg = (
                "ManipulatorIR: set from_key_code or"
                " from_pointing_button, not both"
            )
            raise ValueError(msg)
        if not self.from_key_code and not self.from_pointing_button:
            msg = (
                "ManipulatorIR: one of from_key_code or"
                " from_pointing_button is required"
            )
            raise ValueError(msg)
        return self


class DecompileResult(BaseModel):
    """Result of decompiling a Karabiner manipulator to IR.

    If the manipulator is fully representable, `ir` is set.
    If some fields are not supported, they are listed in `unsupported_fields`.
    If the manipulator cannot be represented at all, `ir` is None.
    `raw` always contains the original manipulator dict.
    """

    ir: ManipulatorIR | None = None
    unsupported_fields: list[str] = []
    raw: dict[str, object] = {}
