"""Tests for key code search tool."""

from karabiner_mcp.tools.keycodes import register_keycode_tools


def _get_tools() -> dict:
    tools: dict = {}

    class FakeMCP:
        def tool(self, name: str = "", **kw):
            def decorator(fn):
                tools[name] = fn
                return fn
            return decorator

    register_keycode_tools(FakeMCP())  # type: ignore[arg-type]
    return tools


TOOLS = _get_tools()
search_key_codes = TOOLS["search_key_codes"]


class TestSearchKeyCodes:
    async def test_search_arrow(self) -> None:
        result = await search_key_codes(query="arrow")
        assert "up_arrow" in result
        assert "down_arrow" in result
        assert "left_arrow" in result
        assert "right_arrow" in result

    async def test_search_f1(self) -> None:
        result = await search_key_codes(query="f1")
        assert "f1" in result
        assert "f10" in result

    async def test_list_all(self) -> None:
        result = await search_key_codes()
        assert "Letters" in result
        assert "Navigation" in result
        assert "Modifier names" in result

    async def test_category_filter(self) -> None:
        result = await search_key_codes(category="Navigation")
        assert "return_or_enter" in result
        assert "Letters" not in result

    async def test_invalid_category(self) -> None:
        result = await search_key_codes(category="FakeCategory")
        assert "Error" in result
        assert "Unknown category" in result

    async def test_no_results(self) -> None:
        result = await search_key_codes(query="zzzznotakey")
        assert "No key codes" in result

    async def test_modifier_search(self) -> None:
        result = await search_key_codes(query="control")
        assert "left_control" in result
        assert "Modifier names" in result

    async def test_pointing_button_search(self) -> None:
        result = await search_key_codes(query="button")
        assert "button1" in result
        assert "Pointing buttons" in result
