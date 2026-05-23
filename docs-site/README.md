# Zscaler MCP Server — Documentation Site

This directory hosts the public documentation site at
[https://zscaler.github.io/zscaler-mcp-server/](https://zscaler.github.io/zscaler-mcp-server/).

It is built with [Docusaurus 3](https://docusaurus.io/) and deployed
automatically to GitHub Pages from the `master` branch via
[`.github/workflows/docs-site.yml`](../.github/workflows/docs-site.yml).

## Local development

```bash
cd docs-site
npm install        # one-time setup
npm run start      # http://localhost:3000
```

The dev server hot-reloads on every save.

## Production build (local preview)

```bash
npm run build      # outputs to ./build/
npm run serve      # serves ./build/ at http://localhost:3000
```

`npm run build` is what CI runs. If it fails locally, it will fail in CI.

## Structure

```
docs-site/
├── docusaurus.config.ts   # site config (navbar, footer, baseUrl)
├── sidebars.ts            # sidebar layout (4 sidebars: Getting Started, Services, Deployment, Integrations)
├── docs/                  # all content (Markdown / MDX)
│   ├── intro.md
│   ├── getting-started/
│   ├── usage/
│   ├── security/
│   ├── services/
│   ├── deployment/
│   ├── integrations/
│   ├── guides/
│   ├── development/
│   └── changelog.md
├── src/
│   ├── css/custom.css     # Zscaler brand palette
│   ├── pages/index.tsx    # homepage
│   └── components/        # Hero, Features, GetStarted
└── static/
    └── img/               # Zscaler logo, favicon, hero background
```

## Branding

The visual identity (colors, logo, favicon, footer) mirrors the
[Zscaler OneAPI Automation Hub](https://gitlab/oneapi-automation-hub). The
palette is **all-blue, no green/teal**, anchored on the Zscaler wordmark blue:

| Token | Value | Use |
|---|---|---|
| `--primary-color` | `#194CBB` | Wordmark blue. Links, buttons, admonition headers (light mode). |
| `--secondary-color` | `#0A2540` | Navbar/footer surface (deep navy). |
| `--accent-color` | `#2D7DFD` | Vivid blue. CTAs, active sidebar items, search-focus rings, dark-mode `--ifm-color-primary`. |
| `--accent-color-soft` | `#7BAFFF` | Lighter blue for inline text accents. |
| `--accent-color-dim` | `#1C5FCC` | Pressed/hover CTA shade. |
| `--light-bg` | `#F4F6F8` | Section backgrounds in light mode. |

The "AI agents" gradient on the homepage is `#194CBB → #3DB7FF` — a clean
deep-to-light blue progression with no green at any point.

Changes to the palette should keep the all-blue rule. Don't reintroduce
teal/green even for highlights — Zscaler's brand identity is fundamentally
blue.

## Adding a new page

1. Create the Markdown file under `docs/<section>/<page>.md`
2. (Optional) Add frontmatter (`id`, `title`, `sidebar_position`) — Docusaurus auto-derives from the filename + first H1 if omitted
3. Add the page to `sidebars.ts` under the appropriate sidebar
4. Run `npm run start` to preview

## Editing existing content

The bulk of the content lives in `docs/`. Most of it was migrated from
`docs/guides/*.md`, `docs/deployment/*.md`, and the project `README.md`
at scaffolding time. When source markdown in those locations changes
substantively, mirror the change here.

### Auto-mirrored from `integrations/*/README.md`

Nine pages in this site are **auto-mirrored** from the canonical
walkthrough READMEs under `integrations/` — that's where the rich
Wistia video content + per-deployment guides actually live. Editing the
mirror by hand has no effect; the next sync run will overwrite it.

| docs-site page | Source of truth |
|---|---|
| `docs/deployment/azure.md` | `integrations/azure/README.md` |
| `docs/deployment/gcp.md` | `integrations/google/README.md` |
| `docs/integrations/google-adk.md` | `integrations/google/adk/README.md` |
| `docs/integrations/aws-harness.md` | `integrations/aws/harness/README.md` |
| `docs/integrations/claude.md` | `integrations/claude-code-plugin/README.md` |
| `docs/integrations/cursor.md` | `integrations/cursor-plugin/README.md` |
| `docs/integrations/gemini-cli.md` | `integrations/gemini-extension/README.md` |
| `docs/integrations/kiro.md` | `integrations/kiro/README.md` |
| `docs/integrations/github-registry.md` | `integrations/github/README.md` |

To regenerate:

```bash
make sync-integration-docs           # from repo root, writes the mirror
# or:
python docs-site/scripts/sync_integrations_to_docs.py
```

To verify (CI runs this):

```bash
make check-integration-docs          # exit 1 if anything is stale
```

The sync script lives at `docs-site/scripts/sync_integrations_to_docs.py`
— a maintainer-only build helper, intentionally kept out of the
top-level `scripts/` folder (which is reserved for end-user-runnable
entry points like `setup-mcp-server.py`). It does three things on
every mirror: rewrites `../../assets/foo.png` image refs to absolute
`raw.githubusercontent.com` URLs, rewrites relative repo links
(`../../README.md`, `./adk/README.md`, etc.) to either the matching
docs-site page or a `github.com/.../blob/master/...` URL, and prepends
a Docusaurus frontmatter block plus a generated-content banner so
editors don't waste time hand-editing the mirror.

Adding a new mirrored page: append a `SyncTarget(...)` entry to
`SYNC_MAP` in the script, then run `make sync-integration-docs`. The
GitHub Pages workflow (`.github/workflows/docs-site.yml`) runs
`--check` as the first step of every build.

## Deployment

Pushes to `master` that touch any file under `docs-site/` (or the workflow
itself) trigger a build + publish to GitHub Pages. See
[`.github/workflows/docs-site.yml`](../.github/workflows/docs-site.yml).

The published URL is **https://zscaler.github.io/zscaler-mcp-server/**.

## Troubleshooting build issues

- **`Module not found` / `Cannot find module`** → run `npm install` again
- **Broken link errors** → Docusaurus is strict; either fix the link or set `onBrokenLinks: 'warn'` in `docusaurus.config.ts`
- **MDX syntax error** → some pure-markdown files contain `{` or `<` characters Docusaurus interprets as MDX expressions. Escape them or rename `.md` to `.mdx`.
- **Cleared build cache** → `npm run clear && npm run start`
