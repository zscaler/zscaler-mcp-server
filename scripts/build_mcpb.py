#!/usr/bin/env python3
"""Build the Zscaler MCP Server MCPB bundle (`.mcpb`) for Claude Desktop.

This is the single, canonical builder. It produces a **source-only,
cross-platform** bundle using the ``uv`` runtime pattern: dependencies are
NOT vendored into the bundle (which would lock it to one OS + Python
version via compiled wheels like ``pydantic_core`` / ``orjson`` /
``cryptography``). Instead ``uv run`` resolves the correct wheels on the
user's machine at install time, so one ``.mcpb`` works on macOS, Windows,
and Linux across Python versions.

Pipeline:

  1. Regenerate the manifest from the live tool inventory and verify it is
     in sync (fails fast if a contributor forgot to run ``make
     generate-docs``).
  2. Assert ``server.type == "uv"`` — the load-bearing cross-platform
     invariant. A ``"python"`` manifest would silently ship a
     platform-locked bundle.
  3. Copy the canonical ``integrations/anthropic/manifest.json`` to the
     repo root (where ``mcpb pack`` requires it), pack, then remove the
     root copy. The root copy is a transient build artifact, never
     committed.
  4. Emit both ``zscaler-mcp-server.mcpb`` and a versioned
     ``zscaler-mcp-server-<version>.mcpb`` into ``dist/``.

Usage:
    python scripts/build_mcpb.py [--output-dir dist] [--keep-root-manifest]
    make build-mcpb

Requires ``npx`` (Node) or a globally-installed ``mcpb`` for the pack step.
"""
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path
from typing import NoReturn

REPO_ROOT = Path(__file__).resolve().parent.parent
CANONICAL_MANIFEST = REPO_ROOT / "integrations" / "anthropic" / "manifest.json"
ROOT_MANIFEST = REPO_ROOT / "manifest.json"

GREEN = "\033[0;32m"
YELLOW = "\033[1;33m"
RED = "\033[0;31m"
NC = "\033[0m"


def c(text: str, color: str) -> str:
    return f"{color}{text}{NC}"


def fail(msg: str) -> NoReturn:
    sys.exit(c(f"ERROR: {msg}", RED))


def run(cmd: list[str], **kwargs) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, check=True, **kwargs)


def regenerate_and_verify_manifest() -> dict:
    """Regenerate the manifest and confirm it's byte-in-sync.

    We invoke the same ``--generate-docs`` path the release uses, then
    re-read the file. If the regeneration changed anything, the working
    tree now has the fresh content and the build proceeds with it — but
    we warn so the contributor knows to commit it.
    """
    print(c("[1/4] Regenerating MCPB manifest from live tool inventory...", GREEN))
    before = CANONICAL_MANIFEST.read_text(encoding="utf-8") if CANONICAL_MANIFEST.is_file() else None
    run(
        [sys.executable, "-m", "zscaler_mcp.server", "--generate-docs"],
        cwd=REPO_ROOT,
        stdout=subprocess.DEVNULL,
    )
    if not CANONICAL_MANIFEST.is_file():
        fail(f"manifest not generated at {CANONICAL_MANIFEST}")
    after = CANONICAL_MANIFEST.read_text(encoding="utf-8")
    if before is not None and before != after:
        print(
            c(
                "  WARNING: the committed manifest was stale and has been "
                "regenerated. Commit integrations/anthropic/manifest.json.",
                YELLOW,
            )
        )
    return json.loads(after)


def assert_cross_platform(manifest: dict) -> None:
    """The single most important guard: no platform-locked bundles."""
    print(c("[2/4] Validating cross-platform (uv runtime) invariants...", GREEN))
    server = manifest.get("server", {})
    server_type = server.get("type")
    if server_type != "uv":
        fail(
            f"server.type is '{server_type}', expected 'uv'. A non-uv manifest "
            "vendors platform-locked compiled wheels and silently fails on "
            "other OS / Python versions. Refusing to build."
        )
    args = server.get("mcp_config", {}).get("args", [])
    if args[:2] != ["run", "python"]:
        fail(
            f"server.mcp_config.args is {args!r}; expected to start with "
            "['run', 'python', ...] for the uv runtime."
        )
    platforms = manifest.get("compatibility", {}).get("platforms", [])
    for required in ("darwin", "win32", "linux"):
        if required not in platforms:
            fail(
                f"compatibility.platforms is {platforms!r}; missing '{required}'. "
                "The uv bundle must advertise all three platforms."
            )
    print(f"  OK: type=uv, platforms={platforms}")


def resolve_packer() -> list[str]:
    if shutil.which("npx"):
        return ["npx", "@anthropic-ai/mcpb@latest"]
    if shutil.which("mcpb"):
        return ["mcpb"]
    fail(
        "Neither 'npx' nor 'mcpb' found. Install Node (for npx) or run: "
        "npm install -g @anthropic-ai/mcpb"
    )


def human(num_bytes: float) -> str:
    for unit in ("B", "K", "M", "G"):
        if num_bytes < 1024 or unit == "G":
            return f"{num_bytes:.1f}{unit}"
        num_bytes /= 1024.0
    return f"{num_bytes:.1f}G"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output-dir",
        default="dist",
        help="Directory (relative to repo root) for the built .mcpb files (default: dist).",
    )
    parser.add_argument(
        "--keep-root-manifest",
        action="store_true",
        help="Leave the transient repo-root manifest.json in place after packing (debug).",
    )
    args = parser.parse_args()

    print(c("Building Zscaler MCP Server MCPB bundle", GREEN))
    print()

    # The version is the single source of truth in the generated manifest
    # (which itself reads zscaler_mcp.__version__ at generation time). We
    # avoid importing the package here so the script works whether or not
    # the repo root happens to be on sys.path — the heavy lifting is done
    # by the `python -m zscaler_mcp.server --generate-docs` subprocess,
    # which runs with cwd=REPO_ROOT.
    manifest = regenerate_and_verify_manifest()
    version = manifest.get("version", "unknown")
    print(c(f"  Version: {version}", GREEN))
    assert_cross_platform(manifest)

    packer = resolve_packer()
    out_dir = (REPO_ROOT / args.output_dir).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    default_bundle = out_dir / "zscaler-mcp-server.mcpb"
    versioned_bundle = out_dir / f"zscaler-mcp-server-{version}.mcpb"

    print(c("[3/4] Packing bundle (manifest copied to pack root)...", GREEN))
    if ROOT_MANIFEST.exists() and ROOT_MANIFEST.resolve() != CANONICAL_MANIFEST.resolve():
        # Stale leftover from a previous flow — remove so we don't pack it.
        ROOT_MANIFEST.unlink()
    shutil.copy2(CANONICAL_MANIFEST, ROOT_MANIFEST)
    try:
        default_bundle.unlink(missing_ok=True)
        run([*packer, "pack", ".", str(default_bundle)], cwd=REPO_ROOT)
    finally:
        if not args.keep_root_manifest:
            ROOT_MANIFEST.unlink(missing_ok=True)

    if not default_bundle.is_file():
        fail("pack reported success but the .mcpb was not produced.")

    shutil.copy2(default_bundle, versioned_bundle)

    print()
    print(c("[4/4] Bundle built successfully.", GREEN))
    print(f"  {default_bundle}  ({human(default_bundle.stat().st_size)})")
    print(f"  {versioned_bundle}  ({human(versioned_bundle.stat().st_size)})")
    print()
    print(c("Bundle info:", GREEN))
    subprocess.run([*packer, "info", str(versioned_bundle)], check=False)
    print()
    print(
        c(
            "Upload the versioned bundle to Anthropic's submission form, or let "
            "the GitHub Actions release workflow attach it automatically.",
            YELLOW,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
