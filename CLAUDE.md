## Build and Test Commands
```bash
uv sync                              # Install dependencies
uv run pytest                        # Run tests
uv run pytest --cov=karabiner_mcp    # Tests with coverage
uv run ruff check .                  # Lint
uv run ruff format .                 # Format
uv run mypy src/                     # Type check
```

## Project Structure
```
karabiner_mcp/
├── src/karabiner_mcp/
│   ├── __main__.py          # Entry point: create_server().run(transport="stdio")
│   ├── server.py            # FastMCP creation, lifespan, instructions
│   ├── config.py            # Env vars: CONFIG_PATH, ASSETS_DIR, LOG_LEVEL
│   ├── tools/
│   │   ├── rules.py         # list_rules, add_rule, edit_rule, remove_rule, toggle_rule
│   │   ├── profiles.py      # list_profiles, select_profile
│   │   └── keycodes.py      # search_key_codes
│   └── service/             # Pure service layer (copied from karabiner_pro_ui)
│       ├── karabiner.py     # Config I/O, rule CRUD, asset management
│       ├── compiler.py      # IR <-> Karabiner JSON compiler/decompiler
│       ├── ir.py            # ManipulatorIR Pydantic models with validation
│       └── keycodes.py      # Key code data (~180 codes, modifiers, pointing buttons)
└── tests/
    ├── conftest.py          # Fixtures: karabiner_env (temp dir), mock_ctx
    ├── test_rules.py        # Rule tool tests
    ├── test_profiles.py     # Profile tool tests
    └── test_keycodes_tool.py # Key code search tests
```

## Architecture
- **FastMCP server** with stdio transport, registered in `~/.claude.json`
- **Lifespan** resolves config/asset paths; tools read karabiner.json fresh each call
- **Service layer** (`service/`) is pure functions with zero framework dependencies
- **IR layer** handles all Karabiner JSON serialization gotchas (see `karabiner_research.md` in karabiner_pro_ui)
- **Error handling**: tools return error strings, not exceptions

## MCP Registration
```json
"karabiner-mcp": {
    "type": "stdio",
    "command": "uv",
    "args": ["run", "--directory", "/Users/jason/git/karabiner_mcp", "karabiner-mcp"]
}
```

## Tool Design
- `add_rule` uses flat parameters with shortcuts (to_key_code for common case, to_keys for complex)
- LLM does natural language -> structured params translation; IR layer handles JSON serialization
- `search_key_codes` solves key code discoverability (Karabiner uses non-obvious names)
