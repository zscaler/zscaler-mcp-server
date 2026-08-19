"""Tests for the documentation generator (zscaler_mcp/common/docgen.py, v2).

Covers:
    * Marker-based rewrite (round-trip, idempotency, error cases).
    * Inventory walk (every registered tool ends up classified from the registry).
    * Per-region renderers (the three shipped today).
    * Repo-wide :func:`check_docs` invariant — once :func:`generate_docs` has run,
      ``check_docs()`` must come back clean.
    * The CI guardrail: the committed docs must already be in sync with the live
      inventory. If it fails, run ``zscaler-mcp --generate-docs``.
"""

from __future__ import annotations

import shutil
import tempfile
import unittest
import unittest.mock
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
    """Walking the live tool inventory (registry-driven)."""

    def test_inventory_has_tools_from_every_service(self):
        inv = build_inventory()
        services = {t.service for t in inv.tools}
        for required in ("zia", "zpa", "zdx", "zcc", "zcell"):
            self.assertIn(required, services)

    def test_every_tool_has_toolset(self):
        inv = build_inventory()
        for t in inv.tools:
            self.assertTrue(t.toolset, f"{t.name} has empty toolset")

    def test_zcell_is_read_only(self):
        inv = build_inventory()
        zcell = [t for t in inv.tools if t.service == "zcell"]
        self.assertEqual(len(zcell), 20)
        self.assertTrue(all(not t.is_write for t in zcell))

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
                ToolEntry("zcell_list_sims", "Search SIMs.", "zcell", "zcell_sim_handling", False),
            ]
        )

    def test_supported_tools_region_includes_every_tool(self):
        out = render_region("tools", self.inv)
        for name in (
            "zia_list_locations",
            "zia_create_location",
            "zpa_list_app_segments",
            "zcell_list_sims",
        ):
            self.assertIn(name, out, f"missing {name} in supported-tools region")

    def test_supported_tools_region_marks_write(self):
        out = render_region("tools", self.inv)
        lines = [ln for ln in out.splitlines() if "zia_create_location" in ln]
        self.assertEqual(len(lines), 1)
        self.assertIn("Write", lines[0])

    def test_service_summary_region_lists_services(self):
        out = render_region("service-summary", self.inv)
        self.assertIn("**ZIA**", out)
        self.assertIn("**ZPA**", out)
        self.assertIn("**ZCell**", out)
        # Counts are present.
        self.assertIn("2 read/write", out)  # 1 read + 1 write for zia
        self.assertIn("1 read-only", out)  # 1 read for zpa

    def test_toolset_catalog_region_groups_by_service(self):
        out = render_region("toolset-catalog", self.inv)
        self.assertIn("ZIA — Internet Access", out)
        self.assertIn("`zia_locations`", out)
        self.assertIn("ZCell — Cellular", out)
        self.assertIn("`zcell_sim_handling`", out)

    def test_unknown_region_raises(self):
        with self.assertRaisesRegex(KeyError, "Unknown region"):
            render_region("does_not_exist", self.inv)


class TestEndToEndOnTempCopy(unittest.TestCase):
    """Run generate / check against an isolated repo-tree copy."""

    def test_check_then_generate_then_check_clean(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmproot = Path(tmpdir)
            for relpath, region, _ in docgen.TARGETS:
                src = docgen.REPO_ROOT / relpath
                dst = tmproot / relpath
                dst.parent.mkdir(parents=True, exist_ok=True)
                if region is None:
                    dst.write_text("stale-whole-file\n", encoding="utf-8")
                    continue
                shutil.copy2(src, dst)
                # Stuff the marker block with a known-stale value.
                content = dst.read_text(encoding="utf-8")
                content = content.replace(
                    f"<!-- generated:end {region} -->",
                    f"\nstale-content\n<!-- generated:end {region} -->",
                )
                dst.write_text(content, encoding="utf-8")

            inv = build_inventory()

            stale_before = docgen.check_docs(repo_root=tmproot, inv=inv)
            self.assertEqual(len(stale_before), len(docgen.TARGETS))

            written = docgen.generate_docs(repo_root=tmproot, inv=inv)
            self.assertEqual(
                {p.name for p in written}, {Path(rel).name for rel, _, _ in docgen.TARGETS}
            )

            stale_after = docgen.check_docs(repo_root=tmproot, inv=inv)
            self.assertEqual(stale_after, [])

            written_again = docgen.generate_docs(repo_root=tmproot, inv=inv)
            self.assertEqual(written_again, [])


class TestOutsideSourceCheckout(unittest.TestCase):
    """The doc commands must explain themselves off a source tree.

    ``REPO_ROOT`` counts four levels up from ``docgen.py``, which only lands on
    the repo root while the ``src/`` layer exists. A non-editable install (pip,
    uvx, the container image) has no such layer, so the same walk resolves into
    the interpreter's library directory and every target path is wrong. That
    surfaced as a ``FileNotFoundError`` naming a path the caller never asked
    for; it should be a stated precondition instead.
    """

    def test_derived_root_without_pyproject_raises(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            fake_root = Path(tmpdir) / "lib" / "python3.14"
            fake_root.mkdir(parents=True)
            with unittest.mock.patch.object(docgen, "REPO_ROOT", fake_root):
                for fn in (docgen.check_docs, docgen.generate_docs):
                    with self.assertRaises(docgen.SourceCheckoutRequired) as ctx:
                        fn()
                    self.assertIn("source checkout", str(ctx.exception))
                    self.assertIn("pyproject.toml", str(ctx.exception))

    def test_explicit_root_is_trusted(self):
        """An explicitly passed root bypasses the check — callers name it."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmproot = Path(tmpdir)
            for relpath, region, _ in docgen.TARGETS:
                dst = tmproot / relpath
                dst.parent.mkdir(parents=True, exist_ok=True)
                if region is None:
                    dst.write_text("stale\n", encoding="utf-8")
                else:
                    shutil.copy2(docgen.REPO_ROOT / relpath, dst)

            self.assertFalse((tmproot / "pyproject.toml").exists())
            docgen.check_docs(repo_root=tmproot, inv=build_inventory())

    def test_real_repo_root_passes_the_check(self):
        self.assertTrue((docgen.REPO_ROOT / "pyproject.toml").is_file())


class TestRepoIsInSync(unittest.TestCase):
    """CI guardrail: committed docs MUST match the live inventory.

    If this fails, run ``zscaler-mcp --generate-docs`` and commit the result.
    """

    def test_committed_docs_are_in_sync(self):
        stale = check_docs()
        self.assertEqual(
            stale,
            [],
            "Committed docs are stale. Run `zscaler-mcp --generate-docs` and commit "
            "the changes. Stale files: " + ", ".join(str(p) for p in stale),
        )


if __name__ == "__main__":
    unittest.main()


class TestDescriptionsAreInterpreterIndependent:
    """Tool descriptions must not vary with the Python version.

    Python 3.13+ dedents docstrings at compile time; 3.11/3.12 do not. Reading
    ``fn.__doc__`` raw therefore yields differently-indented descriptions on
    different interpreters — which ships indented text to agents on 3.11 AND
    makes the generated docs flip-flop between contributors (the CI failure that
    caught this: docs generated on 3.13 were "stale" when checked on 3.11).
    ``@tool`` normalizes with ``inspect.cleandoc``.
    """

    def test_no_description_has_indented_continuation_lines(self):
        from zscaler_mcp.registry import REGISTRY, discover_tools

        discover_tools()
        offenders = []
        for spec in REGISTRY:
            for line in spec.description.splitlines():
                # cleandoc strips the common leading indent; a surviving 4-space
                # indent means the raw __doc__ leaked through.
                if line.startswith("    ") and line.strip():
                    offenders.append(f"{spec.name}: {line[:60]!r}")
                    break
        assert not offenders, (
            "Descriptions carry raw docstring indentation — use inspect.cleandoc "
            "(these render differently on Python 3.11 vs 3.13):\n  " + "\n  ".join(offenders[:10])
        )

    def test_cleandoc_matches_what_the_decorator_stores(self):
        import inspect

        from zscaler_mcp.registry import REGISTRY, discover_tools

        discover_tools()
        spec = REGISTRY.get("zpa_list_segment_groups")
        assert spec.description == inspect.cleandoc(spec.fn.__doc__)
