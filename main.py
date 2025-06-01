from fastmcp import FastMCP
from src.registry import register_all_tools
import asyncio
import sys

app = FastMCP("zscaler-mcp-server")
register_all_tools(app)

async def main():
    print("🚀 MCP Server starting...", file=sys.stderr, flush=True)
    await app.run_stdio_async()

if __name__ == "__main__":
    asyncio.run(main())


