#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
BUILD_DIR="$REPO_ROOT/dist/cowork-plugin"
OUTPUT="$REPO_ROOT/dist/zscaler-cowork-plugin.zip"

rm -rf "$BUILD_DIR"
mkdir -p "$BUILD_DIR/.claude-plugin"

cp "$REPO_ROOT/.claude-plugin/plugin.json" "$BUILD_DIR/.claude-plugin/plugin.json"
if [ -f "$REPO_ROOT/.claude-plugin/marketplace.json" ]; then
  cp "$REPO_ROOT/.claude-plugin/marketplace.json" "$BUILD_DIR/.claude-plugin/marketplace.json"
fi
cp "$REPO_ROOT/.mcp.json" "$BUILD_DIR/.mcp.json"

cp -r "$REPO_ROOT/skills" "$BUILD_DIR/skills"
cp -r "$REPO_ROOT/commands" "$BUILD_DIR/commands"

rm -f "$OUTPUT"
(cd "$BUILD_DIR" && zip -r "$OUTPUT" . -x '*.DS_Store' -x '__MACOSX/*')

echo ""
echo "Plugin package created: $OUTPUT"
echo ""
echo "Contents:"
unzip -l "$OUTPUT"
