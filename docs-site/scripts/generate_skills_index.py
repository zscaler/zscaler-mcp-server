#!/usr/bin/env python3
"""Generate the Skills index page for the docs-site from SKILL.md frontmatter.

Every guided multi-step workflow under ``skills/`` ships as a SKILL.md
with YAML frontmatter (``name`` + ``description``). Those two fields
are the canonical source of truth — Claude / Cursor / Gemini auto-
activate a skill by matching the description against the admin's
prompt, and the same description is what the skill picker in the
Anthropic / Cursor UIs display.

This script walks ``skills/`` once, parses each frontmatter block, and
renders a single ``docs-site/docs/guides/skills.md`` page grouped by
Zscaler service. It is structurally a sibling of
``docs-site/scripts/sync_integrations_to_docs.py``:

    sync_integrations_to_docs.py  -> mirrors integrations/*/README.md
    generate_skills_index.py      -> renders skills/*/*/SKILL.md

Both ship a ``--check`` flag so CI can keep the page in sync.

Usage::

    python docs-site/scripts/generate_skills_index.py            # write
    python docs-site/scripts/generate_skills_index.py --check    # verify

Hooked into the Makefile as ``generate-skills-docs`` and
``check-skills-docs``.
"""

from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import List

import yaml  # type: ignore[import-untyped]

# ---------------------------------------------------------------------------
# Layout
# ---------------------------------------------------------------------------

# Three ``parent`` hops to get to repo root from docs-site/scripts/X.py.
REPO_ROOT = Path(__file__).resolve().parent.parent.parent
SKILLS_DIR = REPO_ROOT / "skills"
TARGET_PAGE = REPO_ROOT / "docs-site" / "docs" / "guides" / "skills.md"

# Master list of services, in the order we want them rendered on the
# page. New services get appended here; unknown service dirs surface
# as a warning at render time so we notice and add them deliberately.
SERVICE_ORDER: List[str] = [
    "zia",
    "zpa",
    "zdx",
    "zcc",
    "zms",
    "zins",
    "easm",
    "cross-product",
]

# Display labels for the section headings on the rendered page. Kept
# concise — the page banner explains the broader picture.
SERVICE_LABELS: dict[str, str] = {
    "zia": "ZIA — Internet Access",
    "zpa": "ZPA — Private Access",
    "zdx": "ZDX — Digital Experience",
    "zcc": "ZCC — Client Connector",
    "zms": "ZMS — Microsegmentation",
    "zins": "Z-Insights",
    "easm": "EASM — External Attack Surface",
    "cross-product": "Cross-Product",
}

# Public base for SKILL.md links so the rendered page jumps straight
# to the canonical source on GitHub instead of a local file path that
# would 404 on the deployed site.
GITHUB_BLOB_BASE = (
    "https://github.com/zscaler/zscaler-mcp-server/blob/master"
)


# ---------------------------------------------------------------------------
# Data shapes
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Skill:
    """One parsed SKILL.md."""

    service: str
    name: str
    description: str
    source_path: str  # repo-relative path to SKILL.md
    slug: str  # leaf folder name (used as a deterministic anchor)

    @property
    def github_url(self) -> str:
        return f"{GITHUB_BLOB_BASE}/{self.source_path}"


# ---------------------------------------------------------------------------
# Parsing
# ---------------------------------------------------------------------------


def _parse_frontmatter(path: Path) -> dict:
    """Extract the YAML frontmatter block from a Markdown file.

    SKILL.md format is always::

        ---
        <yaml>
        ---
        <body>

    We split on the first two ``---`` lines (allowing leading/trailing
    whitespace) and run ``yaml.safe_load`` on the middle. Returns the
    decoded mapping or raises ``ValueError`` if the file is malformed
    — every SKILL.md in this repo is enforced to have frontmatter, so
    a parse failure here is a real bug worth surfacing.
    """
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---"):
        raise ValueError(f"{path}: missing leading '---' frontmatter delimiter")
    parts = text.split("---", 2)
    if len(parts) < 3:
        raise ValueError(f"{path}: malformed frontmatter (need opening + closing '---')")
    data = yaml.safe_load(parts[1]) or {}
    if not isinstance(data, dict):
        raise ValueError(f"{path}: frontmatter must be a YAML mapping")
    return data


def discover_skills() -> List[Skill]:
    """Walk ``skills/`` and return every SKILL.md as a parsed ``Skill``.

    Files under ``skills/<service>/<skill-name>/example/`` and
    ``skills/<service>/<skill-name>/templates/`` are explicitly
    skipped so we never confuse a fixture file for a real skill.
    """
    discovered: List[Skill] = []
    for skill_md in sorted(SKILLS_DIR.glob("*/*/SKILL.md")):
        rel = skill_md.relative_to(REPO_ROOT)
        # Defensive: example/ and templates/ live one level deeper, so
        # the glob above already excludes them — but keep the guard in
        # case someone introduces a new fixture pattern.
        if any(part in {"example", "templates"} for part in rel.parts):
            continue

        meta = _parse_frontmatter(skill_md)
        name = meta.get("name")
        description = meta.get("description")
        if not name or not description:
            raise ValueError(
                f"{rel}: frontmatter must include both 'name' and 'description'"
            )

        service = skill_md.parent.parent.name
        slug = skill_md.parent.name
        discovered.append(
            Skill(
                service=service,
                name=name.strip(),
                description=description.strip(),
                source_path=str(rel),
                slug=slug,
            )
        )
    return discovered


# ---------------------------------------------------------------------------
# Rendering
# ---------------------------------------------------------------------------


_FRONTMATTER = """\
---
title: Skills
sidebar_label: Skills
---
"""

_BANNER = """\
<!--
  AUTO-GENERATED — do not edit by hand.
  Source of truth: skills/*/*/SKILL.md (frontmatter)
  Regenerate with: make generate-skills-docs
                   (or: python docs-site/scripts/generate_skills_index.py)
-->
"""

_INTRO = """\
Skills are guided multi-step workflows that ship with the Zscaler MCP Server. Unlike individual tools — which are single API operations — a skill encodes the *playbook* for a complete admin task: which tools to call, in which order, with which guardrails, and how to talk to the admin while doing it.

**How skills get loaded.** Every skill carries a `description` in its frontmatter. MCP clients that support skill loading (Claude Code, Claude Desktop, Cursor) auto-activate a skill when the admin's prompt matches that description. You don't need to invoke them manually — describe what you want, and Claude / Cursor pick the right skill.

**Where skills live.** Every skill is a directory under [`skills/`](https://github.com/zscaler/zscaler-mcp-server/tree/master/skills) on GitHub, organised by Zscaler service. Click any skill below to read its full `SKILL.md` (workflow steps, edge cases, validation rules).
"""


def _summary_table(skills: List[Skill]) -> str:
    """Render the at-a-glance table at the top of the page.

    One row per service with the count. We do not list every skill
    here — the per-service H2 sections below are the canonical
    catalog. This table is a navigational hint.
    """
    counts: dict[str, int] = {}
    for skill in skills:
        counts[skill.service] = counts.get(skill.service, 0) + 1
    total = sum(counts.values())

    lines = ["| Service | Skills |", "|---------|--------|"]
    for service in SERVICE_ORDER:
        count = counts.get(service, 0)
        if not count:
            continue
        label = SERVICE_LABELS[service]
        anchor = _anchor_for_service(service)
        lines.append(f"| [**{label}**](#{anchor}) | {count} |")
    lines.append(f"| **Total** | **{total}** |")
    return "\n".join(lines)


def _anchor_for_service(service: str) -> str:
    """Deterministic anchor slug used on the service H2 heading.

    Rather than guess at Docusaurus's slug-from-heading algorithm
    (which differs subtly across versions for non-ASCII glyphs like
    the em-dash in our labels), we emit an explicit ``{#anchor}``
    suffix on every H2 and link to that. This anchor is therefore the
    only contract — the heading text can change freely without
    breaking the in-page jump links.
    """
    return f"service-{service}"


def _normalize_description(description: str) -> str:
    """Collapse the long single-line YAML description into prose.

    SKILL.md descriptions are deliberately dense — they're keyword
    matchers for the auto-activation matcher — so they can be 500-
    1000 characters of one-line keyword-stuffed prose. On a docs page
    that reads as a wall of text. We just trim and normalise
    whitespace; we do NOT truncate, because the full description is
    the most useful answer to "what does this skill actually do?".
    """
    return " ".join(description.split())


def render_page(skills: List[Skill]) -> str:
    """Assemble the full Markdown page body."""
    parts: List[str] = [
        _FRONTMATTER,
        "",
        _BANNER,
        "",
        _INTRO,
        "",
        "## At a glance",
        "",
        _summary_table(skills),
        "",
    ]

    # Group by service and render H2 per service in canonical order.
    by_service: dict[str, List[Skill]] = {}
    for skill in skills:
        by_service.setdefault(skill.service, []).append(skill)

    seen_services: set[str] = set()
    for service in SERVICE_ORDER:
        bucket = by_service.get(service, [])
        if not bucket:
            continue
        seen_services.add(service)
        label = SERVICE_LABELS[service]
        anchor = _anchor_for_service(service)
        parts.append(f"## {label} {{#{anchor}}}")
        parts.append("")
        for skill in sorted(bucket, key=lambda s: s.name):
            description = _normalize_description(skill.description)
            parts.append(f"### [`{skill.name}`]({skill.github_url})")
            parts.append("")
            parts.append(description)
            parts.append("")

    # Warn (loudly, but don't fail) if we discovered a service folder
    # we don't have a label for. The page still renders without it —
    # the maintainer just needs to add an entry to SERVICE_ORDER and
    # SERVICE_LABELS.
    unknown = [s for s in by_service.keys() if s not in seen_services]
    if unknown:
        print(
            f"warning: skills found under unknown service folders: {sorted(unknown)} "
            f"— add them to SERVICE_ORDER + SERVICE_LABELS in "
            f"{Path(__file__).relative_to(REPO_ROOT)}",
            file=sys.stderr,
        )

    body = "\n".join(parts).rstrip() + "\n"
    return body


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--check",
        action="store_true",
        help="Verify the target page matches what would be generated. "
        "Exit 1 if the page is stale.",
    )
    args = parser.parse_args()

    skills = discover_skills()
    if not skills:
        print("error: no skills discovered under skills/", file=sys.stderr)
        return 1

    rendered = render_page(skills)

    existing = (
        TARGET_PAGE.read_text(encoding="utf-8") if TARGET_PAGE.exists() else None
    )

    if args.check:
        if existing != rendered:
            print(
                "Skills index is stale. Re-run `make generate-skills-docs`.",
                file=sys.stderr,
            )
            return 1
        print(f"Skills index is in sync ({len(skills)} skills).")
        return 0

    if existing == rendered:
        print(f"Skills index already up to date ({len(skills)} skills).")
        return 0

    TARGET_PAGE.parent.mkdir(parents=True, exist_ok=True)
    TARGET_PAGE.write_text(rendered, encoding="utf-8")
    print(
        f"Wrote {TARGET_PAGE.relative_to(REPO_ROOT)} "
        f"({len(skills)} skills across {len(set(s.service for s in skills))} services)."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
