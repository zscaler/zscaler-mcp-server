"""Tests for the documentation generator (zscaler_mcp/common/docgen.py).

Covers:
    * Marker-based rewrite (round-trip, idempotency, error cases).
    * Inventory walk (every registered tool ends up classified).
    * Per-region renderers (the three shipped today).
    * Repo-wide :func:`check_docs` invariant — once :func:`generate_docs`
      has run, ``check_docs()`` must come back clean.
    * The CI guardrail invariant: the version of the docs committed in
      git must already be in sync with the live inventory. If this test
      fails, run ``zscaler-mcp --generate-docs``.
"""

from __future__ import annotations

import unittest
from pathlib import Path
from textwrap import dedent

from zscaler_mcp.common import docgen
from zscaler_mcp.common.docgen import (
    Inventory,
    ToolEntry,
    _rewrite_region,
    build_inventory,
    check_docs,
    render_region,
)


class TestMarkerRewrite(unittest.TestCase):
    """The low-level marker-replacement primitive."""

    def test_round_trip_replaces_body(self):
        before = dedent(
            """\
            # Title

            <!-- generated:start tools -->
            old body
            <!-- generated:end tools -->

            after
            """
        )
        out = _rewrite_region(before, "tools", "new body")
        self.assertIn("new body", out)
        self.assertNotIn("old body", out)
        self.assertTrue(out.startswith("# Title"))
        self.assertTrue(out.rstrip().endswith("after"))

    def test_idempotent(self):
        before = "<!-- generated:start x -->\n<!-- generated:end x -->\n"
        once = _rewrite_region(before, "x", "body")
        twice = _rewrite_region(once, "x", "body")
        self.assertEqual(once, twice)

    def test_preserves_unrelated_regions(self):
        before = dedent(
            """\
            <!-- generated:start a -->
            A
            <!-- generated:end a -->
            <!-- generated:start b -->
            B
            <!-- generated:end b -->
            """
        )
        out = _rewrite_region(before, "a", "NEW")
        self.assertIn("NEW", out)
        self.assertIn("B", out)

    def test_missing_start_marker_raises(self):
        with self.assertRaisesRegex(ValueError, "Missing start marker"):
            _rewrite_region("just text\n<!-- generated:end x -->\n", "x", "y")

    def test_missing_end_marker_raises(self):
        with self.assertRaisesRegex(ValueError, "Missing end marker"):
            _rewrite_region("<!-- generated:start x -->\nbody\n", "x", "y")

    def test_swapped_marker_order_raises(self):
        content = dedent(
            """\
            <!-- generated:end x -->
            <!-- generated:start x -->
            """
        )
        with self.assertRaisesRegex(ValueError, "precedes start marker"):
            _rewrite_region(content, "x", "y")

    def test_duplicate_region_raises(self):
        content = dedent(
            """\
            <!-- generated:start x -->
            <!-- generated:end x -->
            <!-- generated:start x -->
            <!-- generated:end x -->
            """
        )
        with self.assertRaisesRegex(ValueError, "more than once"):
            _rewrite_region(content, "x", "y")


class TestInventory(unittest.TestCase):
    """Walking the live tool inventory."""

    def test_inventory_has_tools_from_every_service(self):
        inv = build_inventory()
        services = {t.service for t in inv.tools}
        for required in ("zia", "zpa", "zdx", "zcc", "meta"):
            self.assertIn(required, services)

    def test_every_tool_has_toolset(self):
        inv = build_inventory()
        for t in inv.tools:
            self.assertTrue(t.toolset, f"{t.name} has empty toolset")

    def test_meta_tools_present(self):
        inv = build_inventory()
        names = {t.name for t in inv.tools}
        for required in (
            "zscaler_check_connectivity",
            "zscaler_list_toolsets",
            "zscaler_get_toolset_tools",
            "zscaler_enable_toolset",
        ):
            self.assertIn(required, names)

    def test_write_tools_flagged(self):
        inv = build_inventory()
        # ZIA has plenty of write tools (create / update / delete).
        zia_writes = [t for t in inv.tools if t.service == "zia" and t.is_write]
        self.assertGreater(len(zia_writes), 10)

    def test_service_counts_shape(self):
        inv = build_inventory()
        counts = inv.service_counts()
        for svc, c in counts.items():
            self.assertEqual(c["read"] + c["write"], c["total"], svc)


class TestRenderers(unittest.TestCase):
    """Each region renderer produces well-formed Markdown tables."""

    def setUp(self):
        # Tiny synthetic inventory keeps the assertions stable across
        # real-world tool-list churn.
        self.inv = Inventory(
            tools=[
                ToolEntry(
                    "zia_list_locations", "List ZIA locations.", "zia", "zia_locations", False
                ),
                ToolEntry(
                    "zia_create_location", "Create a ZIA location.", "zia", "zia_locations", True
                ),
                ToolEntry(
                    "zpa_list_app_segments",
                    "List ZPA app segments.",
                    "zpa",
                    "zpa_app_segments",
                    False,
                ),
                ToolEntry("zscaler_list_toolsets", "Discover toolsets.", "meta", "meta", False),
            ]
        )

    def test_supported_tools_region_includes_every_tool(self):
        out = render_region("tools", self.inv)
        for name in (
            "zia_list_locations",
            "zia_create_location",
            "zpa_list_app_segments",
            "zscaler_list_toolsets",
        ):
            self.assertIn(name, out, f"missing {name} in supported-tools region")

    def test_supported_tools_region_marks_write(self):
        out = render_region("tools", self.inv)
        # Find the row for zia_create_location and assert it carries 'Write'.
        lines = [ln for ln in out.splitlines() if "zia_create_location" in ln]
        self.assertEqual(len(lines), 1)
        self.assertIn("Write", lines[0])

    def test_service_summary_region_lists_services(self):
        out = render_region("service-summary", self.inv)
        self.assertIn("**ZIA**", out)
        self.assertIn("**ZPA**", out)
        # Meta is intentionally excluded from the user-facing summary.
        self.assertNotIn("**META**", out)
        # Counts are present.
        self.assertIn("2 read/write", out)  # 1 read + 1 write for zia
        self.assertIn("1 read-only", out)  # 1 read for zpa

    def test_toolset_catalog_region_groups_by_service(self):
        out = render_region("toolset-catalog", self.inv)
        self.assertIn("Always-on", out)
        self.assertIn("`meta`", out)
        self.assertIn("ZIA — Internet Access", out)
        self.assertIn("`zia_locations`", out)

    def test_unknown_region_raises(self):
        with self.assertRaisesRegex(KeyError, "Unknown region"):
            render_region("does_not_exist", self.inv)


class TestEndToEndOnTempCopy(unittest.TestCase):
    """Run generate / check against an isolated repo-tree copy.

    Avoids touching the real docs from a test run, while still
    exercising the full file-rewrite path.
    """

    def test_check_then_generate_then_check_clean(self):
        import tempfile
        import shutil

        with tempfile.TemporaryDirectory() as tmpdir:
            tmproot = Path(tmpdir)
            # Materialise just enough of the repo tree to satisfy TARGETS.
            for relpath, region, _ in docgen.TARGETS:
                src = docgen.REPO_ROOT / relpath
                dst = tmproot / relpath
                dst.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src, dst)
                # Stuff the marker block with a known-stale value so we
                # know the rewrite ran.
                content = dst.read_text(encoding="utf-8")
                content = content.replace(
                    f"<!-- generated:end {region} -->",
                    f"\nstale-content\n<!-- generated:end {region} -->",
                )
                dst.write_text(content, encoding="utf-8")

            inv = build_inventory()

            # First check should report all targets stale.
            stale_before = docgen.check_docs(repo_root=tmproot, inv=inv)
            self.assertEqual(len(stale_before), len(docgen.TARGETS))

            # Generate to refresh.
            written = docgen.generate_docs(repo_root=tmproot, inv=inv)
            self.assertEqual(
                set(p.name for p in written), set(Path(rel).name for rel, _, _ in docgen.TARGETS)
            )

            # Second check should be clean.
            stale_after = docgen.check_docs(repo_root=tmproot, inv=inv)
            self.assertEqual(stale_after, [])

            # Generating again is a no-op.
            written_again = docgen.generate_docs(repo_root=tmproot, inv=inv)
            self.assertEqual(written_again, [])


class TestRepoIsInSync(unittest.TestCase):
    """The CI guardrail.

    The committed docs in this repo MUST be in sync with the live tool
    inventory. If this test fails, run::

        zscaler-mcp --generate-docs

    and commit the resulting changes.
    """

    def test_committed_docs_are_in_sync(self):
        stale = check_docs()
        self.assertEqual(
            stale,
            [],
            "Committed docs are stale. Run `zscaler-mcp --generate-docs` "
            "and commit the changes. Stale files: " + ", ".join(str(p) for p in stale),
        )


if __name__ == "__main__":
    unittest.main()
