"""Tests for profile management tools."""

from pathlib import Path
from unittest.mock import AsyncMock

from karabiner_mcp.service import karabiner as ksvc
from karabiner_mcp.tools.profiles import register_profile_tools


def _get_tools() -> dict:
    tools: dict = {}

    class FakeMCP:
        def tool(self, name: str = "", **kw):
            def decorator(fn):
                tools[name] = fn
                return fn
            return decorator

    register_profile_tools(FakeMCP())  # type: ignore[arg-type]
    return tools


TOOLS = _get_tools()
list_profiles = TOOLS["list_profiles"]
select_profile = TOOLS["select_profile"]


class TestListProfiles:
    async def test_lists_profiles(self, mock_ctx: AsyncMock) -> None:
        result = await list_profiles(ctx=mock_ctx)
        assert "Default" in result
        assert "Gaming" in result
        assert "(selected)" in result
        assert "2 rules" in result

    async def test_missing_config(self, tmp_path: Path) -> None:
        ctx = AsyncMock()
        ctx.lifespan_context = {
            "config_path": tmp_path / "nonexistent.json",
            "assets_dir": tmp_path / "assets",
        }
        result = await list_profiles(ctx=ctx)
        assert "Error" in result


class TestSelectProfile:
    async def test_switch_profile(
        self,
        mock_ctx: AsyncMock,
        karabiner_env: dict[str, Path],
    ) -> None:
        result = await select_profile(
            profile_index=1, ctx=mock_ctx
        )
        assert "Gaming" in result
        assert "Switched" in result

        config = ksvc.read_config(karabiner_env["config_path"])
        assert config["profiles"][0]["selected"] is False
        assert config["profiles"][1]["selected"] is True

    async def test_invalid_index(self, mock_ctx: AsyncMock) -> None:
        result = await select_profile(
            profile_index=99, ctx=mock_ctx
        )
        assert "Error" in result
