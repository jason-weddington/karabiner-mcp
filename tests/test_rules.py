"""Tests for rule management tools."""

import json
from pathlib import Path
from unittest.mock import AsyncMock

from karabiner_mcp.service import karabiner as ksvc
from karabiner_mcp.tools.rules import register_rule_tools


# Import tool functions by registering them on a mock MCP
def _get_tools() -> dict:
    """Register tools and return them by name."""
    tools: dict = {}

    class FakeMCP:
        def tool(self, name: str = "", **kw):
            def decorator(fn):
                tools[name] = fn
                return fn
            return decorator

    register_rule_tools(FakeMCP())  # type: ignore[arg-type]
    return tools


TOOLS = _get_tools()
list_rules = TOOLS["list_rules"]
add_rule = TOOLS["add_rule"]
toggle_rule = TOOLS["toggle_rule"]
remove_rule = TOOLS["remove_rule"]
edit_rule = TOOLS["edit_rule"]


class TestListRules:
    async def test_lists_installed_rules(
        self, mock_ctx: AsyncMock
    ) -> None:
        result = await list_rules(ctx=mock_ctx)
        assert "Caps Lock to Escape" in result
        assert "Ctrl+H to Backspace" in result
        assert "[ON]" in result
        assert "[OFF]" in result

    async def test_includes_available(
        self, mock_ctx: AsyncMock
    ) -> None:
        result = await list_rules(
            include_available=True, ctx=mock_ctx
        )
        assert "F5 to Refresh" in result
        assert "Available" in result

    async def test_missing_config(self, tmp_path: Path) -> None:
        ctx = AsyncMock()
        ctx.lifespan_context = {
            "config_path": tmp_path / "nonexistent.json",
            "assets_dir": tmp_path / "assets",
        }
        result = await list_rules(ctx=ctx)
        assert "Error" in result


class TestAddRule:
    async def test_simple_remap(
        self,
        mock_ctx: AsyncMock,
        karabiner_env: dict[str, Path],
    ) -> None:
        result = await add_rule(
            description="Tab to Escape",
            from_key_code="tab",
            to_key_code="escape",
            ctx=mock_ctx,
        )
        assert "Created and installed" in result
        assert "Tab to Escape" in result

        # Verify it's in karabiner.json
        config = ksvc.read_config(karabiner_env["config_path"])
        rules = config["profiles"][0]["complex_modifications"]["rules"]
        descs = [r["description"] for r in rules]
        assert "Tab to Escape" in descs

    async def test_with_app_condition(
        self,
        mock_ctx: AsyncMock,
        karabiner_env: dict[str, Path],
    ) -> None:
        result = await add_rule(
            description="Fn to Ctrl in Terminal",
            from_key_code="fn",
            to_key_code="left_control",
            app_if=["^com\\.apple\\.Terminal$"],
            ctx=mock_ctx,
        )
        assert "Created and installed" in result

        config = ksvc.read_config(karabiner_env["config_path"])
        rules = config["profiles"][0]["complex_modifications"]["rules"]
        new_rule = next(
            r for r in rules
            if r["description"] == "Fn to Ctrl in Terminal"
        )
        conditions = new_rule["manipulators"][0]["conditions"]
        assert conditions[0]["type"] == "frontmost_application_if"

    async def test_with_device_condition(
        self,
        mock_ctx: AsyncMock,
        karabiner_env: dict[str, Path],
    ) -> None:
        result = await add_rule(
            description="Ctrl to Cmd on TKL",
            from_key_code="left_control",
            to_key_code="left_command",
            device_if=[{"vendor_id": 1234, "product_id": 5678}],
            ctx=mock_ctx,
        )
        assert "Created and installed" in result

        config = ksvc.read_config(karabiner_env["config_path"])
        rules = config["profiles"][0]["complex_modifications"]["rules"]
        new_rule = next(
            r for r in rules
            if r["description"] == "Ctrl to Cmd on TKL"
        )
        conditions = new_rule["manipulators"][0]["conditions"]
        assert conditions[0]["type"] == "device_if"
        assert conditions[0]["identifiers"][0]["vendor_id"] == 1234
        assert conditions[0]["identifiers"][0]["product_id"] == 5678

    async def test_tap_hold(
        self,
        mock_ctx: AsyncMock,
        karabiner_env: dict[str, Path],
    ) -> None:
        result = await add_rule(
            description="Caps: tap=esc, hold=ctrl",
            from_key_code="caps_lock",
            to_key_code="left_control",
            to_if_alone_key_code="escape",
            ctx=mock_ctx,
        )
        assert "Created and installed" in result

        config = ksvc.read_config(karabiner_env["config_path"])
        rules = config["profiles"][0]["complex_modifications"]["rules"]
        new_rule = next(
            r for r in rules
            if r["description"] == "Caps: tap=esc, hold=ctrl"
        )
        manip = new_rule["manipulators"][0]
        assert manip["to"][0]["key_code"] == "left_control"
        assert manip["to_if_alone"][0]["key_code"] == "escape"

    async def test_invalid_key_code(
        self, mock_ctx: AsyncMock
    ) -> None:
        result = await add_rule(
            description="Bad Key",
            from_key_code="not_a_key",
            to_key_code="escape",
            ctx=mock_ctx,
        )
        assert "Error" in result

    async def test_missing_output(
        self, mock_ctx: AsyncMock
    ) -> None:
        result = await add_rule(
            description="No Output",
            from_key_code="a",
            ctx=mock_ctx,
        )
        assert "Error" in result

    async def test_duplicate_description(
        self, mock_ctx: AsyncMock
    ) -> None:
        result = await add_rule(
            description="Caps Lock to Escape",
            from_key_code="caps_lock",
            to_key_code="escape",
            ctx=mock_ctx,
        )
        assert "Error" in result
        assert "already" in result.lower()

    async def test_shell_command(
        self,
        mock_ctx: AsyncMock,
        karabiner_env: dict[str, Path],
    ) -> None:
        result = await add_rule(
            description="F5 opens Safari",
            from_key_code="f5",
            to_shell_command="open -a Safari",
            ctx=mock_ctx,
        )
        assert "Created and installed" in result

        config = ksvc.read_config(karabiner_env["config_path"])
        rules = config["profiles"][0]["complex_modifications"]["rules"]
        new_rule = next(
            r for r in rules
            if r["description"] == "F5 opens Safari"
        )
        to_list = new_rule["manipulators"][0]["to"]
        assert to_list[0]["shell_command"] == "open -a Safari"

    async def test_asset_file_created(
        self,
        mock_ctx: AsyncMock,
        karabiner_env: dict[str, Path],
    ) -> None:
        await add_rule(
            description="Test Asset",
            from_key_code="a",
            to_key_code="b",
            asset_title="My Custom Rules",
            ctx=mock_ctx,
        )

        asset_path = (
            karabiner_env["assets_dir"] / "my_custom_rules.json"
        )
        assert asset_path.exists()
        data = json.loads(asset_path.read_text())
        assert data["title"] == "My Custom Rules"
        assert len(data["rules"]) == 1


class TestToggleRule:
    async def test_disable(
        self,
        mock_ctx: AsyncMock,
        karabiner_env: dict[str, Path],
    ) -> None:
        result = await toggle_rule(
            description="Caps Lock to Escape",
            enabled=False,
            ctx=mock_ctx,
        )
        assert "disabled" in result

        config = ksvc.read_config(karabiner_env["config_path"])
        rules = config["profiles"][0]["complex_modifications"]["rules"]
        rule = next(
            r for r in rules
            if r["description"] == "Caps Lock to Escape"
        )
        assert rule["enabled"] is False

    async def test_enable(
        self,
        mock_ctx: AsyncMock,
        karabiner_env: dict[str, Path],
    ) -> None:
        result = await toggle_rule(
            description="Ctrl+H to Backspace",
            enabled=True,
            ctx=mock_ctx,
        )
        assert "enabled" in result

        config = ksvc.read_config(karabiner_env["config_path"])
        rules = config["profiles"][0]["complex_modifications"]["rules"]
        rule = next(
            r for r in rules
            if r["description"] == "Ctrl+H to Backspace"
        )
        assert "enabled" not in rule

    async def test_not_found(self, mock_ctx: AsyncMock) -> None:
        result = await toggle_rule(
            description="Nonexistent Rule",
            enabled=True,
            ctx=mock_ctx,
        )
        assert "Error" in result


class TestRemoveRule:
    async def test_remove_keeps_asset(
        self,
        mock_ctx: AsyncMock,
        karabiner_env: dict[str, Path],
    ) -> None:
        result = await remove_rule(
            description="Caps Lock to Escape",
            ctx=mock_ctx,
        )
        assert "Removed" in result
        assert "Asset file preserved" in result

        config = ksvc.read_config(karabiner_env["config_path"])
        rules = config["profiles"][0]["complex_modifications"]["rules"]
        descs = [r["description"] for r in rules]
        assert "Caps Lock to Escape" not in descs

        # Asset still exists
        asset = karabiner_env["assets_dir"] / "test_rules.json"
        assert asset.exists()

    async def test_remove_deletes_asset(
        self,
        mock_ctx: AsyncMock,
        karabiner_env: dict[str, Path],
    ) -> None:
        result = await remove_rule(
            description="Caps Lock to Escape",
            also_delete_asset=True,
            ctx=mock_ctx,
        )
        assert "Removed" in result

        # Asset should still exist with 1 rule remaining
        data = json.loads(
            (
                karabiner_env["assets_dir"] / "test_rules.json"
            ).read_text()
        )
        descs = [r["description"] for r in data["rules"]]
        assert "Caps Lock to Escape" not in descs
        assert "F5 to Refresh" in descs


class TestEditRule:
    async def test_edit_output_key(
        self,
        mock_ctx: AsyncMock,
        karabiner_env: dict[str, Path],
    ) -> None:
        result = await edit_rule(
            description="Caps Lock to Escape",
            to_key_code="delete_or_backspace",
            ctx=mock_ctx,
        )
        assert "Updated" in result

        config = ksvc.read_config(karabiner_env["config_path"])
        rules = config["profiles"][0]["complex_modifications"]["rules"]
        rule = next(
            r for r in rules
            if r["description"] == "Caps Lock to Escape"
        )
        assert (
            rule["manipulators"][0]["to"][0]["key_code"]
            == "delete_or_backspace"
        )

    async def test_edit_not_found(self, mock_ctx: AsyncMock) -> None:
        result = await edit_rule(
            description="Nonexistent",
            to_key_code="a",
            ctx=mock_ctx,
        )
        assert "Error" in result

    async def test_edit_adds_device_condition(
        self,
        mock_ctx: AsyncMock,
        karabiner_env: dict[str, Path],
    ) -> None:
        result = await edit_rule(
            description="Caps Lock to Escape",
            device_if=[
                {"vendor_id": 1234, "product_id": 5678}
            ],
            ctx=mock_ctx,
        )
        assert "Updated" in result

        config = ksvc.read_config(karabiner_env["config_path"])
        rules = config["profiles"][0]["complex_modifications"]["rules"]
        rule = next(
            r for r in rules
            if r["description"] == "Caps Lock to Escape"
        )
        conditions = rule["manipulators"][0]["conditions"]
        assert len(conditions) == 1
        assert conditions[0]["type"] == "device_if"
        assert conditions[0]["identifiers"][0]["vendor_id"] == 1234

    async def test_edit_clears_device_condition(
        self,
        mock_ctx: AsyncMock,
        karabiner_env: dict[str, Path],
    ) -> None:
        # First add a device condition
        await edit_rule(
            description="Caps Lock to Escape",
            device_if=[
                {"vendor_id": 1234, "product_id": 5678}
            ],
            ctx=mock_ctx,
        )
        # Then clear it
        result = await edit_rule(
            description="Caps Lock to Escape",
            device_if=[],
            ctx=mock_ctx,
        )
        assert "Updated" in result

        config = ksvc.read_config(karabiner_env["config_path"])
        rules = config["profiles"][0]["complex_modifications"]["rules"]
        rule = next(
            r for r in rules
            if r["description"] == "Caps Lock to Escape"
        )
        conditions = rule["manipulators"][0].get("conditions", [])
        assert len(conditions) == 0

    async def test_edit_adds_app_condition(
        self,
        mock_ctx: AsyncMock,
        karabiner_env: dict[str, Path],
    ) -> None:
        result = await edit_rule(
            description="Caps Lock to Escape",
            app_unless=["^com\\.apple\\.Terminal$"],
            ctx=mock_ctx,
        )
        assert "Updated" in result

        config = ksvc.read_config(karabiner_env["config_path"])
        rules = config["profiles"][0]["complex_modifications"]["rules"]
        rule = next(
            r for r in rules
            if r["description"] == "Caps Lock to Escape"
        )
        conditions = rule["manipulators"][0]["conditions"]
        assert len(conditions) == 1
        assert (
            conditions[0]["type"] == "frontmost_application_unless"
        )
