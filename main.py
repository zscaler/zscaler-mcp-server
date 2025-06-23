import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "src")))

from fastmcp import FastMCP
from src.registry import register_all_tools
import asyncio

# ✅ Add and FLUSH after each print
# print("[MCP] Environment check:")
# print(f"  ZSCALER_CLIENT_ID set: {'ZSCALER_CLIENT_ID' in os.environ}", flush=True)
# print(f"  ZSCALER_CLIENT_SECRET set: {'ZSCALER_CLIENT_SECRET' in os.environ}", flush=True)
# print(f"  ZSCALER_CUSTOMER_ID: {os.environ.get('ZSCALER_CUSTOMER_ID')}", flush=True)
# print(f"  ZSCALER_CLOUD: {os.environ.get('ZSCALER_CLOUD')}", flush=True)
# print(f"  VANITY_DOMAIN: {os.environ.get('ZSCALER_VANITY_DOMAIN')}", flush=True)


app = FastMCP("zscaler-mcp-server")
register_all_tools(app)

async def main():
    print("🚀 MCP Server starting...", file=sys.stderr, flush=True)
    await app.run_stdio_async()

if __name__ == "__main__":
    asyncio.run(main())
