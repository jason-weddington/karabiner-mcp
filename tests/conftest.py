"""Shared test fixtures for karabiner-mcp tests."""

import json
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock

import pytest

SAMPLE_CONFIG: dict[str, Any] = {
    "global": {"show_in_menu_bar": True},
    "profiles": [
        {
            "name": "Default",
            "selected": True,
            "complex_modifications": {
                "parameters": {},
                "rules": [
                    {
                        "description": "Caps Lock to Escape",
                        "manipulators": [
                            {
                                "type": "basic",
                                "from": {"key_code": "caps_lock"},
                                "to": [{"key_code": "escape"}],
                            }
                        ],
                    },
                    {
                        "description": "Ctrl+H to Backspace",
                        "enabled": False,
                        "manipulators": [
                            {
                                "type": "basic",
                                "from": {
                                    "key_code": "h",
                                    "modifiers": {
                                        "mandatory": ["control"],
                                    },
                                },
                                "to": [
                                    {"key_code": "delete_or_backspace"}
                                ],
                            }
                        ],
                    },
                ],
            },
            "simple_modifications": [],
        },
        {
            "name": "Gaming",
            "selected": False,
            "complex_modifications": {"parameters": {}, "rules": []},
            "simple_modifications": [],
        },
    ],
}

SAMPLE_ASSET: dict[str, Any] = {
    "title": "Test Rules",
    "rules": [
        {
            "description": "Caps Lock to Escape",
            "manipulators": [
                {
                    "type": "basic",
                    "from": {"key_code": "caps_lock"},
                    "to": [{"key_code": "escape"}],
                }
            ],
        },
        {
            "description": "F5 to Refresh",
            "manipulators": [
                {
                    "type": "basic",
                    "from": {"key_code": "f5"},
                    "to": [
                        {
                            "key_code": "r",
                            "modifiers": ["command"],
                        }
                    ],
                }
            ],
        },
    ],
}


@pytest.fixture()
def karabiner_env(tmp_path: Path) -> dict[str, Path]:
    """Set up a temporary karabiner directory with sample config."""
    config_path = tmp_path / "karabiner.json"
    config_path.write_text(json.dumps(SAMPLE_CONFIG, indent=4))

    assets_dir = tmp_path / "assets" / "complex_modifications"
    assets_dir.mkdir(parents=True)
    (assets_dir / "test_rules.json").write_text(
        json.dumps(SAMPLE_ASSET, indent=4)
    )

    return {"config_path": config_path, "assets_dir": assets_dir}


@pytest.fixture()
def mock_ctx(karabiner_env: dict[str, Path]) -> AsyncMock:
    """Create a mock Context with lifespan_context set."""
    ctx = AsyncMock()
    ctx.lifespan_context = {
        "config_path": karabiner_env["config_path"],
        "assets_dir": karabiner_env["assets_dir"],
    }
    return ctx
