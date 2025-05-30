#!/bin/bash
cd "$(dirname "$0")"
export PYTHONPATH="src"
export PATH="$HOME/.local/bin:$PATH"
# Replace the path below with the exact output of your `which poetry` command
/Users/wguilherme/.local/bin/poetry run python -m zscaler_mcp.server_main
