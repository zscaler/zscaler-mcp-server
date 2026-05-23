#!/usr/bin/env python3
"""Sync integration READMEs into the docs-site (Docusaurus) source tree.

The READMEs under ``integrations/*/`` are the canonical, video-rich
walkthroughs for every supported deployment target and MCP client
plugin. The Docusaurus site at ``docs-site/`` needs to mirror those
files so that publishing to GitHub Pages always reflects the same
content GitHub users see when they browse the repo.

This script is the single source of truth for that mirror. Running it:

1. Reads each source README listed in :data:`SYNC_MAP`.
2. Rewrites image paths so embedded thumbnails resolve when served
   from ``zscaler.github.io/zscaler-mcp-server`` — every
   ``../../assets/foo.png`` style relative path becomes a
   ``https://raw.githubusercontent.com/...`` absolute URL pointing at
   the same asset on ``master``. Images that need to render before
   they're committed should live under ``docs-site/static/img/``
   instead and be referenced as ``/img/<name>.png``.
3. Strips the source's leading H1 (so Docusaurus doesn't render it
   twice — the frontmatter ``title`` provides the page title).
4. Prepends a Docusaurus frontmatter block with ``sidebar_label`` and
   ``title``.
5. Writes the result to the matching ``docs-site/docs/...`` path.

It also runs in ``--check`` mode (no writes; exits 1 if any target is
stale) so CI can enforce the mirror stays in sync.

This is a **maintainer-only** build helper, not a tool an end user is
meant to run. It lives under ``docs-site/scripts/`` (next to the
consumer it serves) instead of the top-level ``scripts/`` folder so
end users browsing ``scripts/`` only see entry points that are
relevant to them (today: ``setup-mcp-server.py``).

Usage::

    python docs-site/scripts/sync_integrations_to_docs.py            # write
    python docs-site/scripts/sync_integrations_to_docs.py --check    # verify

The Makefile targets ``sync-integration-docs`` and
``check-integration-docs`` are the recommended entry points.
"""

from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import List

# ---------------------------------------------------------------------------
# Layout
# ---------------------------------------------------------------------------

# This script lives at <repo>/docs-site/scripts/sync_integrations_to_docs.py
# — REPO_ROOT therefore needs three ``parent`` hops, not two.
REPO_ROOT = Path(__file__).resolve().parent.parent.parent
DOCS_SITE = REPO_ROOT / "docs-site" / "docs"
RAW_GITHUB_BASE = (
    "https://raw.githubusercontent.com/zscaler/zscaler-mcp-server/master"
)

# Header injected at the top of every synced file so editors don't try to
# hand-edit the mirror.
GENERATED_BANNER = (
    "<!--\n"
    "  AUTO-GENERATED — do not edit by hand.\n"
    "  Source of truth: {source}\n"
    "  Regenerate with: make sync-integration-docs\n"
    "                   (or: python docs-site/scripts/sync_integrations_to_docs.py)\n"
    "-->\n"
)


# ---------------------------------------------------------------------------
# Sync map
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class SyncTarget:
    """One source README → docs-site target."""

    # Source README path, relative to REPO_ROOT.
    source: str
    # Target Markdown path, relative to DOCS_SITE.
    target: str
    # Docusaurus frontmatter values.
    title: str
    sidebar_label: str
    # Optional sidebar_position for explicit ordering inside its section.
    # The unified sidebar uses sidebars.ts ordering, so this is just a
    # hint to the auto-derived sidebar — leave None unless intentional.
    sidebar_position: int | None = None


SYNC_MAP: List[SyncTarget] = [
    # ------------------------------------------------------------------
    # Cloud deployments — these are the ones with the Wistia walkthroughs
    # the docs-site was previously missing.
    # ------------------------------------------------------------------
    SyncTarget(
        source="integrations/azure/README.md",
        target="deployment/azure.md",
        title="Microsoft Azure",
        sidebar_label="Azure",
    ),
    SyncTarget(
        source="integrations/google/README.md",
        target="deployment/gcp.md",
        title="Google Cloud",
        sidebar_label="Google Cloud",
    ),
    SyncTarget(
        source="integrations/google/adk/README.md",
        target="integrations/google-adk.md",
        title="Google ADK Agent",
        sidebar_label="Google ADK",
    ),
    SyncTarget(
        source="integrations/aws/harness/README.md",
        target="integrations/aws-harness.md",
        title="AWS Harness — Local Testing Client",
        sidebar_label="AWS Harness",
    ),
    # ------------------------------------------------------------------
    # MCP client plugins — the canonical install + usage guides live in
    # the integrations folder; the docs-site stubs were drifting behind.
    # ------------------------------------------------------------------
    SyncTarget(
        source="integrations/claude-code-plugin/README.md",
        target="integrations/claude.md",
        title="Claude",
        sidebar_label="Claude",
    ),
    SyncTarget(
        source="integrations/cursor-plugin/README.md",
        target="integrations/cursor.md",
        title="Cursor Plugin",
        sidebar_label="Cursor",
    ),
    SyncTarget(
        source="integrations/gemini-extension/README.md",
        target="integrations/gemini-cli.md",
        title="Gemini CLI Extension",
        sidebar_label="Gemini CLI",
    ),
    SyncTarget(
        source="integrations/kiro/README.md",
        target="integrations/kiro.md",
        title="Kiro Power",
        sidebar_label="Kiro IDE",
    ),
    SyncTarget(
        source="integrations/github/README.md",
        target="integrations/github-registry.md",
        title="GitHub MCP Registry",
        sidebar_label="GitHub MCP Registry",
    ),
]


# ---------------------------------------------------------------------------
# Transformations
# ---------------------------------------------------------------------------

# Match Markdown image refs whose URL contains a relative path into
# assets/. Handles both ``![alt](path)`` (used in image-only refs) and
# ``[![alt](path)](href)`` (linked image / video thumbnail). The
# rewriter only touches the inner ``(path)`` capture group.
_REL_IMG_RE = re.compile(r"(!\[[^\]]*\]\()((?:\.\./)+assets/[^)]+)(\))")

# Match Markdown links of the form ``[text](url)`` — used for the
# generic relative-link rewriter below. We deliberately exclude image
# refs (``![alt](url)``) and intentionally only fire on the inner URL.
_MD_LINK_RE = re.compile(r"(?<!\!)\[([^\]]*)\]\(([^)]+)\)")

# Cross-reference map: when a source README links to a sibling
# integration's README via a relative path, redirect that link to the
# matching synced docs-site page instead of a GitHub blob URL. Keys are
# substrings the original href ends with (case-sensitive); the match is
# evaluated after stripping leading ``./`` and any ``../`` segments.
#
# These come from the cross-doc-links we know to exist in the source
# READMEs today. Adding a new one is a one-line entry here.
_CROSS_REF_REDIRECTS: dict[str, str] = {
    "integrations/google/adk/README.md": "/docs/integrations/google-adk",
    "integrations/gemini-extension/README.md": "/docs/integrations/gemini-cli",
    "integrations/claude-code-plugin/README.md": "/docs/integrations/claude",
    "integrations/cursor-plugin/README.md": "/docs/integrations/cursor",
    "integrations/kiro/README.md": "/docs/integrations/kiro",
    "integrations/github/README.md": "/docs/integrations/github-registry",
    "integrations/aws/bedrock-agentcore/README.md": "/docs/deployment/amazon-bedrock",
    "integrations/aws/harness/README.md": "/docs/integrations/aws-harness",
    "integrations/google/README.md": "/docs/deployment/gcp",
    "integrations/azure/README.md": "/docs/deployment/azure",
}

# URLs that the link rewriter must always treat as already-absolute and
# leave untouched. Anything matching one of these protocols / prefixes
# is skipped.
_ABSOLUTE_LINK_PREFIXES = (
    "http://",
    "https://",
    "mailto:",
    "#",
    "/",
)


def _rewrite_image_paths(text: str) -> str:
    """Turn every ``../../assets/foo.png`` into a raw.githubusercontent URL.

    Why raw URLs instead of mirroring the binaries into
    ``docs-site/static/``? Two reasons:

    * Zero asset duplication and zero asset-sync drift.
    * The thumbnails live in the public repo anyway — clicking through
      goes to Wistia, so the docs site never needs to host the binaries.

    The trade-off: the image must be committed to ``master`` for the
    raw URL to resolve. For new walkthrough screenshots that need to
    render before they're pushed (e.g. local dev preview), copy them
    into ``docs-site/static/img/`` and reference them as
    ``/img/<name>.png`` — that path is served directly by Docusaurus
    and is not touched by this rewriter.
    """

    def replace(match: re.Match[str]) -> str:
        alt_open, rel_path, close = match.group(1), match.group(2), match.group(3)
        # Strip every leading ``../`` and join with the raw GitHub base.
        cleaned = re.sub(r"^(?:\.\./)+", "", rel_path)
        return f"{alt_open}{RAW_GITHUB_BASE}/{cleaned}{close}"

    return _REL_IMG_RE.sub(replace, text)


def _resolve_relative(source: str, href: str) -> str:
    """Resolve ``href`` against the directory of ``source``.

    Returns a repo-root-relative path with ``..`` segments collapsed,
    suitable for matching against :data:`_CROSS_REF_REDIRECTS` or
    appending to a GitHub blob URL. ``source`` is the source README's
    repo-relative path.
    """
    base_dir = Path(source).parent.as_posix()
    # Drop the optional leading ``./`` so PurePosixPath joins cleanly.
    if href.startswith("./"):
        href = href[2:]
    joined = (Path(base_dir) / href).as_posix() if base_dir else href
    # Collapse ``foo/../bar`` style segments without touching the OS.
    parts: list[str] = []
    for segment in joined.split("/"):
        if segment in ("", "."):
            continue
        if segment == "..":
            if parts:
                parts.pop()
            continue
        parts.append(segment)
    return "/".join(parts)


def _rewrite_relative_links(text: str, source: str) -> str:
    """Rewrite every relative Markdown link in ``text``.

    Two rules, applied in order:

    1. If the resolved repo-relative path matches a known cross-
       reference (:data:`_CROSS_REF_REDIRECTS`), replace the link with
       the synced docs-site page URL.
    2. Otherwise, rewrite the link to a GitHub blob URL so the reader
       can still navigate to the original file (often a config file,
       a sibling guide, or a top-level README).

    Anchors-only links (``#section``), absolute URLs, mailto: links,
    and site-absolute paths (``/foo``) are left alone.
    """

    def replace(match: re.Match[str]) -> str:
        text_, href = match.group(1), match.group(2).strip()

        # Strip optional "title" portion of a Markdown link if present
        # (``[label](url "title")``). The MDX parser tolerates the title
        # so we preserve it verbatim by splitting on whitespace.
        href_only, _, title = href.partition(" ")
        href_only = href_only.strip()

        # Skip anything that's already absolute or doesn't look like a
        # relative file reference.
        if href_only.startswith(_ABSOLUTE_LINK_PREFIXES):
            return match.group(0)

        # Anchor-only links inside the page.
        if href_only.startswith("#") or not href_only:
            return match.group(0)

        # Split off any trailing anchor (``foo.md#section``) so we can
        # match the file path against the redirect map cleanly. We
        # forward the anchor onto the rewritten href.
        path_part, sep, anchor = href_only.partition("#")
        resolved = _resolve_relative(source, path_part)

        # 1. Synced-cross-reference redirect.
        for needle, replacement in _CROSS_REF_REDIRECTS.items():
            if resolved == needle:
                new_href = replacement + (sep + anchor if sep else "")
                return f"[{text_}]({new_href})"

        # 2. Fall back to a GitHub blob URL so the link still works.
        github_href = f"{RAW_GITHUB_BASE.replace('/raw.githubusercontent.com/', '/github.com/').replace('/master', '/blob/master')}/{resolved}"
        # The simple replace() chain above transforms the raw-content
        # base into a /blob/ URL pointing at the same ref. Append the
        # anchor and any link title.
        suffix = (sep + anchor if sep else "") + (
            (" " + title) if title else ""
        )
        return f"[{text_}]({github_href}{suffix})"

    return _MD_LINK_RE.sub(replace, text)


def _strip_leading_h1(text: str) -> str:
    """Drop the first H1 (and its trailing blank line) from a README.

    Docusaurus already renders ``# Title`` from the frontmatter
    ``title:`` field. If we keep the source's H1, the page renders two
    titles stacked on top of each other.
    """
    lines = text.splitlines()
    out: list[str] = []
    dropped = False
    for line in lines:
        if not dropped and line.startswith("# "):
            dropped = True
            continue
        if dropped and not out and line.strip() == "":
            # Skip the blank line immediately after the removed H1.
            continue
        out.append(line)
    return "\n".join(out)


def _build_frontmatter(target: SyncTarget) -> str:
    """Render a Docusaurus YAML frontmatter block."""
    lines = ["---"]
    lines.append(f"title: {target.title}")
    lines.append(f"sidebar_label: {target.sidebar_label}")
    if target.sidebar_position is not None:
        lines.append(f"sidebar_position: {target.sidebar_position}")
    lines.append("---")
    return "\n".join(lines) + "\n"


def render_target(target: SyncTarget) -> str:
    """Produce the full Markdown body for one target, without writing."""
    source_path = REPO_ROOT / target.source
    if not source_path.exists():
        raise FileNotFoundError(f"Source README missing: {target.source}")
    raw = source_path.read_text(encoding="utf-8")
    body = _rewrite_image_paths(raw)
    body = _rewrite_relative_links(body, target.source)
    body = _strip_leading_h1(body)
    body = body.rstrip() + "\n"
    return (
        _build_frontmatter(target)
        + "\n"
        + GENERATED_BANNER.format(source=target.source)
        + "\n"
        + body
    )


# ---------------------------------------------------------------------------
# Entry points
# ---------------------------------------------------------------------------


def sync(write: bool) -> tuple[list[Path], list[Path]]:
    """Render every target and (optionally) write it.

    Returns a tuple ``(changed, missing_source)``. In ``--check`` mode
    ``changed`` contains the paths that would be modified;
    ``missing_source`` contains targets whose source README was not
    found. Both should be empty for a clean check.
    """
    changed: list[Path] = []
    missing: list[Path] = []
    for target in SYNC_MAP:
        try:
            rendered = render_target(target)
        except FileNotFoundError as exc:
            print(f"  ! {exc}", file=sys.stderr)
            missing.append(REPO_ROOT / target.source)
            continue

        target_path = DOCS_SITE / target.target
        existing = target_path.read_text(encoding="utf-8") if target_path.exists() else None
        if existing == rendered:
            continue
        changed.append(target_path)
        if write:
            target_path.parent.mkdir(parents=True, exist_ok=True)
            target_path.write_text(rendered, encoding="utf-8")
    return changed, missing


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--check",
        action="store_true",
        help="Verify that every target is in sync without writing. "
        "Exit 1 if any target is stale.",
    )
    args = parser.parse_args()

    changed, missing = sync(write=not args.check)

    if missing:
        print("\nMissing source READMEs (cannot sync):", file=sys.stderr)
        for path in missing:
            print(f"  - {path}", file=sys.stderr)
        return 1

    if args.check:
        if changed:
            print("Out-of-date integration docs (re-run sync to fix):")
            for path in changed:
                print(f"  - {path.relative_to(REPO_ROOT)}")
            return 1
        print("All integration docs are in sync.")
        return 0

    if changed:
        print(f"Synced {len(changed)} integration doc(s):")
        for path in changed:
            print(f"  - {path.relative_to(REPO_ROOT)}")
    else:
        print("All integration docs are already up to date.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
