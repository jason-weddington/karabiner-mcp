# karabiner-mcp

MCP server for managing [Karabiner-Elements](https://karabiner-elements.pqrs.org/) keyboard remapping rules on macOS.

Exposes Karabiner configuration as MCP tools so an LLM can search key codes, list/add/edit/remove/toggle rules, and switch profiles — all through natural language.

## Tools

| Tool | Description |
|------|-------------|
| `search_key_codes` | Find Karabiner key code names (e.g. "enter" → `return_or_enter`) |
| `list_rules` | List all rules in the current profile with enabled/disabled status |
| `add_rule` | Create a new remapping rule |
| `edit_rule` | Modify an existing rule |
| `remove_rule` | Delete a rule (with optional asset cleanup) |
| `toggle_rule` | Enable or disable a rule |
| `list_profiles` | Show all Karabiner profiles |
| `select_profile` | Switch the active profile |

## Installation

Requires Python 3.13+ and [uv](https://docs.astral.sh/uv/). No need to clone the repo — register the server in your Claude config (`~/.claude.json`) and `uvx` will install it on first run:

```json
{
  "mcpServers": {
    "karabiner-mcp": {
      "type": "stdio",
      "command": "uvx",
      "args": [
        "--from", "git+https://github.com/jason-weddington/karabiner-mcp.git",
        "karabiner-mcp"
      ]
    }
  }
}
```

Then ask Claude things like:

- "Remap Caps Lock to Escape"
- "Make right Option act as Hyper key"
- "When I tap left Shift, type open-paren"
- "Disable the rule called 'Caps Lock to Escape'"

## Rule patterns

- **Simple remap** — one key to another
- **Modifier combo** — e.g. Cmd+Shift+K to something
- **Tap vs hold** — different output for tap and hold on the same key
- **App-specific** — rules scoped to specific applications by bundle ID
- **Shell command** — trigger a shell command from a key combo

## Development

```bash
uv run pytest                        # Run tests
uv run pytest --cov=karabiner_mcp    # Tests with coverage
uv run ruff check .                  # Lint
uv run ruff format .                 # Format
uv run mypy src/                     # Type check
```

## License

[MIT](LICENSE)
