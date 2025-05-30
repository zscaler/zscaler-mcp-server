# from fastmcp import FastMCP
# from mcp.server import InitializationOptions, NotificationOptions
# from mcp.server.stdio import stdio_server
# from zscaler_mcp.registry import register_all_tools
# import asyncio

# app = FastMCP("zscaler-mcp-server")
# register_all_tools(app)

# async def main():
#     async with stdio_server() as (read_stream, write_stream):
#         await app.run(
#             read_stream,
#             write_stream,
#             InitializationOptions(
#                 server_name="zscaler-mcp-server",
#                 server_version="0.1.0",
#                 capabilities=app.capabilities(notification_options=NotificationOptions()),
#             ),
#         )

# if __name__ == "__main__":
#     asyncio.run(main())

# from fastmcp import FastMCP
# from zscaler_mcp.registry import register_all_tools
# import asyncio

# app = FastMCP("zscaler-mcp-server")
# register_all_tools(app)

# async def main():
#     await app.run_stdio_async()  # Corrected: No arguments needed here.

# if __name__ == "__main__":
#     asyncio.run(main())


from fastmcp import FastMCP
from zscaler_mcp.registry import register_all_tools
import asyncio
import sys

app = FastMCP("zscaler-mcp-server")
register_all_tools(app)

async def main():
    print("🚀 MCP Server starting...", file=sys.stderr, flush=True)
    await app.run_stdio_async()

if __name__ == "__main__":
    asyncio.run(main())


