import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "src")))

from src.registry import register_all_tools
from src.zscaler_mcp import app
import asyncio


register_all_tools(app)

async def main():
    print("🚀 MCP Server starting...", file=sys.stderr, flush=True)
    await app.run_stdio_async()

if __name__ == "__main__":
    asyncio.run(main())
