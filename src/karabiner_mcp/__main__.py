"""Entry point for the karabiner-mcp server."""

from karabiner_mcp.server import create_server


def main() -> None:
    """Run the karabiner-mcp MCP server."""
    server = create_server()
    server.run(transport="stdio")


if __name__ == "__main__":
    main()
