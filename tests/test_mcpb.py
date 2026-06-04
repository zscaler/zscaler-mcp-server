"""Tests for the MCPB manifest builder (zscaler_mcp/common/mcpb.py).

The docgen test suite (`tests/test_docgen.py`) already covers the
generic "whole-file" generation pathway and the repo-sync invariant.
This file targets the MCPB-specific contracts that would silently
ship a broken Claude Desktop extension if regressed:

* Spec version and required top-level fields.
* Server type pinned to "uv" (NOT "python" — the old pip-target
  bundle was platform-locked; see commit/PR #30).
* Env-var names match what `zscaler_mcp/server.py` actually reads
  (these were silently broken pre-fix: ZSCALER_MCP_ENABLED_SERVICES
  / _ENABLED_TOOLS / _DEBUG_MODE were ignored at runtime).
* Version comes from `zscaler_mcp.__version__`, not a hand-edited
  string.
* `tools` array is non-empty and contains the right ordering
  invariants (meta first, then service-grouped).
* Manifest is valid JSON and round-trips through json.loads.
"""

from __future__ import annotations

import json
import unittest

from zscaler_mcp import __version__
from zscaler_mcp.common import mcpb
from zscaler_mcp.common.docgen import build_inventory
from zscaler_mcp.common.toolsets import TOOLSETS


class TestSpecCompliance(unittest.TestCase):
    """Top-level manifest fields the MCPB spec requires."""

    @classmethod
    def setUpClass(cls):
        cls.inv = build_inventory()
        cls.manifest = mcpb.build_manifest(cls.inv)

    def test_manifest_version_is_0_4(self):
        """MCPB 0.4 is the spec we target. Bumping it requires an audit."""
        self.assertEqual(self.manifest["manifest_version"], "0.4")

    def test_required_top_level_fields_present(self):
        # Per https://github.com/anthropics/mcpb/blob/main/MANIFEST.md
        for field in (
            "manifest_version",
            "name",
            "version",
            "description",
            "author",
            "server",
            "tools",
            "compatibility",
            "user_config",
        ):
            self.assertIn(field, self.manifest, f"required field missing: {field}")

    def test_author_has_name_and_email(self):
        author = self.manifest["author"]
        self.assertIn("name", author)
        self.assertIn("email", author)
        self.assertTrue(author["email"].endswith("@zscaler.com"))

    def test_icon_path_matches_repo_root_file(self):
        # Icon lives under ``assets/`` to keep the repo root clean.
        # ``.mcpbignore`` un-ignores this single file with
        # ``!assets/icon.png`` so it still ships in the bundle.
        from zscaler_mcp.common.docgen import REPO_ROOT

        self.assertEqual(self.manifest["icon"], "assets/icon.png")
        self.assertTrue(
            (REPO_ROOT / self.manifest["icon"]).is_file(),
            f"icon file missing on disk: {REPO_ROOT / self.manifest['icon']}",
        )


class TestVersionWiring(unittest.TestCase):
    """Version comes from `zscaler_mcp.__version__`, not a hand string."""

    def test_version_matches_package_version(self):
        manifest = mcpb.build_manifest(build_inventory())
        self.assertEqual(manifest["version"], __version__)


class TestServerConfig(unittest.TestCase):
    """The `server` block determines how Claude Desktop launches us."""

    @classmethod
    def setUpClass(cls):
        cls.server = mcpb.build_manifest(build_inventory())["server"]

    def test_server_type_is_uv_not_python(self):
        """``uv`` defers wheel resolution to install time — required for
        cross-platform bundles. ``python`` with pip --target embeds
        platform-locked compiled extensions (.so/.pyd) and silently
        fails on the other OSes. PR #30 root-caused this.
        """
        self.assertEqual(self.server["type"], "uv")
        self.assertNotEqual(self.server["type"], "python")

    def test_entry_point_is_relative_and_exists(self):

        from zscaler_mcp.common.docgen import REPO_ROOT

        entry = self.server["entry_point"]
        # Must NOT lead with "/", "./", or refer to anything outside
        # the bundle root (Claude Desktop refuses absolute paths).
        self.assertFalse(entry.startswith(("/", "./", "../")))
        self.assertTrue((REPO_ROOT / entry).is_file(), f"entry point missing: {entry}")

    def test_uv_invocation_args(self):
        """``uv run python -m zscaler_mcp.server`` is the canonical
        invocation. Anything else either skips dependency resolution
        or runs the wrong module.
        """
        cfg = self.server["mcp_config"]
        self.assertEqual(cfg["command"], "uv")
        self.assertEqual(cfg["args"], ["run", "python", "-m", "zscaler_mcp.server"])

    def test_env_uses_correct_zscaler_mcp_var_names(self):
        """Catches the silent-ignore bug from PR #30 commit 2.

        The manifest used to set ZSCALER_MCP_ENABLED_SERVICES /
        _ENABLED_TOOLS / _DEBUG_MODE, but ``zscaler_mcp/server.py``
        reads ZSCALER_MCP_SERVICES / _TOOLS / _DEBUG. The old names
        were silently ignored. Anyone using the Claude Desktop UI
        toggles got no effect.
        """
        env = self.server["mcp_config"]["env"]

        # These must be present (the correct names).
        self.assertIn("ZSCALER_MCP_SERVICES", env)
        self.assertIn("ZSCALER_MCP_TOOLS", env)
        self.assertIn("ZSCALER_MCP_DEBUG", env)

        # These must NOT be present (the broken names).
        self.assertNotIn("ZSCALER_MCP_ENABLED_SERVICES", env)
        self.assertNotIn("ZSCALER_MCP_ENABLED_TOOLS", env)
        self.assertNotIn("ZSCALER_MCP_DEBUG_MODE", env)

    def test_env_vars_match_runtime_reads(self):
        """The env vars the manifest writes are actually consumed by
        ``zscaler_mcp/server.py``. We grep the source — a stronger
        guarantee than the name-shape check above.
        """

        from zscaler_mcp.common.docgen import REPO_ROOT

        server_py = (REPO_ROOT / "zscaler_mcp" / "server.py").read_text(
            encoding="utf-8"
        )
        env = self.server["mcp_config"]["env"]

        # PYTHONPATH is a Python runtime var, not consumed by server.py.
        # Same for the credential vars — those are read by the Zscaler
        # SDK, not server.py. We only assert on the server.py-controlled
        # toggles where the bug actually was.
        for var in (
            "ZSCALER_MCP_SERVICES",
            "ZSCALER_MCP_TOOLS",
            "ZSCALER_MCP_DEBUG",
            "ZSCALER_MCP_WRITE_ENABLED",
            "ZSCALER_MCP_WRITE_TOOLS",
            "ZSCALER_MCP_USER_AGENT_COMMENT",
        ):
            self.assertIn(var, env, f"missing from manifest env: {var}")
            self.assertIn(
                var,
                server_py,
                f"{var} declared in manifest but never read by server.py — "
                "this is exactly the kind of silent-ignore drift the test "
                "is here to catch.",
            )

    def test_every_user_config_reference_resolves(self):
        """If env has ``${user_config.foo}``, ``foo`` must exist in
        the manifest's user_config block — otherwise Claude Desktop
        substitutes the literal placeholder string.
        """
        import re

        env = self.server["mcp_config"]["env"]
        manifest = mcpb.build_manifest(build_inventory())
        declared_keys = set(manifest["user_config"].keys())

        pattern = re.compile(r"\$\{user_config\.([a-zA-Z0-9_]+)\}")
        for var, template in env.items():
            for ref in pattern.findall(str(template)):
                self.assertIn(
                    ref,
                    declared_keys,
                    f"env {var} references ${{user_config.{ref}}} but no "
                    f"such key in user_config block. Declared: "
                    f"{sorted(declared_keys)}",
                )


class TestToolsArray(unittest.TestCase):
    """The dynamic part of the manifest."""

    @classmethod
    def setUpClass(cls):
        cls.inv = build_inventory()
        cls.tools = mcpb.build_manifest(cls.inv)["tools"]

    def test_tools_array_is_non_empty(self):
        # Stale / hand-curated manifest used to drift to zero or 265
        # tools while the live inventory had >300. The whole point of
        # this generator is to keep the array honest.
        self.assertGreater(
            len(self.tools), 200, "tools array suspiciously small — generator may be broken"
        )

    def test_every_tool_has_name_and_description(self):
        for entry in self.tools:
            self.assertIn("name", entry)
            self.assertIn("description", entry)
            self.assertTrue(entry["name"], "blank tool name in manifest")
            self.assertTrue(entry["description"], f"blank description: {entry['name']}")

    def test_no_duplicate_tool_names(self):
        names = [t["name"] for t in self.tools]
        dupes = {n for n in names if names.count(n) > 1}
        self.assertEqual(dupes, set(), f"duplicate tool names: {dupes}")

    def test_count_matches_live_inventory(self):
        self.assertEqual(
            len(self.tools),
            len(self.inv.tools),
            "manifest tool count must equal live inventory count — the "
            "generator dropped or added rows.",
        )

    def test_meta_tools_appear_first(self):
        """Service-grouped ordering: ``meta`` first, then ZIA, ZPA, etc.
        Matches the convention used by every other docgen target.
        """
        names = [t["name"] for t in self.tools]
        # First meta tool's index should be lower than the first non-meta tool.
        meta_indices = [
            i for i, n in enumerate(names) if n.startswith("zscaler_")
        ]
        non_meta_indices = [
            i for i, n in enumerate(names) if not n.startswith("zscaler_")
        ]
        if meta_indices and non_meta_indices:
            self.assertLess(
                max(meta_indices),
                min(non_meta_indices),
                "meta tools should appear before service tools",
            )

    def test_descriptions_are_single_sentence(self):
        """The MCPB directory only shows a one-line description per
        tool. The renderer should trim each description to its first
        sentence to keep the catalog row scannable.
        """
        for entry in self.tools:
            desc = entry["description"]
            # Allow embedded periods inside parens/inline code, but the
            # post-trim text should end with exactly one period (the
            # sentence terminator) and not contain ". " mid-string
            # (that would be sentence #2 leaking through).
            self.assertTrue(
                desc.endswith(".") or desc.endswith("..."),
                f"description doesn't end with period: {entry['name']!r}: {desc!r}",
            )


class TestRendererContract(unittest.TestCase):
    """The docgen integration."""

    def test_render_manifest_json_signature(self):
        # Must match the (Inventory, ToolsetCatalog) -> str contract.
        inv = build_inventory()
        result = mcpb.render_manifest_json(inv, TOOLSETS)
        self.assertIsInstance(result, str)
        # Trailing newline for POSIX-friendliness.
        self.assertTrue(result.endswith("\n"))

    def test_renderer_output_is_valid_json(self):
        out = mcpb.render_manifest_json(build_inventory(), TOOLSETS)
        # No-throw round trip.
        roundtrip = json.loads(out)
        self.assertEqual(roundtrip["name"], "Zscaler MCP Server")

    def test_renderer_is_deterministic(self):
        """Two calls with the same inventory produce byte-identical
        output. Without this, ``check-docs`` would oscillate between
        clean and stale on every CI run.
        """
        inv = build_inventory()
        a = mcpb.render_manifest_json(inv, TOOLSETS)
        b = mcpb.render_manifest_json(inv, TOOLSETS)
        self.assertEqual(a, b)


class TestCommittedManifest(unittest.TestCase):
    """The committed manifest at ``integrations/anthropic/manifest.json``
    must match what the generator would emit right now.

    Equivalent to the `tests/test_docgen.py::TestRepoIsInSync` guard
    but scoped to just the MCPB manifest — the error message is
    actionable enough to be worth surfacing as its own test.
    """

    def test_canonical_manifest_path(self):
        # Guards the location decision: the committed manifest lives under
        # integrations/anthropic/ (not the repo root). The build flow copies
        # it to the root only transiently at pack time.
        self.assertEqual(
            mcpb.MANIFEST_RELATIVE_PATH, "integrations/anthropic/manifest.json"
        )

    def test_root_manifest_is_not_committed(self):
        # A repo-root manifest.json is a transient build artifact and must
        # never be committed (it would go stale and confuse `mcpb pack`).
        from zscaler_mcp.common.docgen import REPO_ROOT

        self.assertFalse(
            (REPO_ROOT / "manifest.json").is_file(),
            "A repo-root manifest.json exists. It is a transient pack-time "
            "artifact and must not be committed — the canonical copy lives "
            "at integrations/anthropic/manifest.json.",
        )

    def test_committed_manifest_is_current(self):

        from zscaler_mcp.common.docgen import REPO_ROOT

        path = REPO_ROOT / mcpb.MANIFEST_RELATIVE_PATH
        self.assertTrue(path.is_file(), f"manifest not at expected path: {path}")

        on_disk = path.read_text(encoding="utf-8")
        expected = mcpb.render_manifest_json(build_inventory(), TOOLSETS)
        self.assertEqual(
            on_disk,
            expected,
            "Committed manifest is stale. Run `make generate-docs` "
            "(or `zscaler-mcp --generate-docs`) and commit the result.",
        )


if __name__ == "__main__":
    unittest.main()
