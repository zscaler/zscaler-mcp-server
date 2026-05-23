import React, { useMemo, useState } from "react";
import toolsetsData from "@site/src/data/toolsets.json";
import styles from "./styles.module.css";

// ---------------------------------------------------------------------------
// Types — keep in lock-step with the JSON schema documented in
// `zscaler_mcp/common/docgen.py::_render_toolset_catalog_json`. The Python
// generator owns the canonical shape; this file is the consumer.
// ---------------------------------------------------------------------------

type ToolsetEntry = {
  id: string;
  description: string;
  default: boolean;
  tool_count: number;
  always_on: boolean;
};

type ServiceGroup = {
  code: string;
  label: string;
  description: string;
  toolsets: ToolsetEntry[];
};

type CatalogPayload = {
  _generated: string;
  services: ServiceGroup[];
};

const catalog = toolsetsData as CatalogPayload;

// ---------------------------------------------------------------------------
// Description shaping — turn the dense source-of-truth description string
// (a single sentence/paragraph written for Python docstring use) into the
// inline-React structure the card UI renders.
//
// We deliberately do NOT split each description into a separate "headline"
// and "body" — an earlier iteration did, but it produced two different
// typographic styles in the same card and made the reading flow stutter
// (and broke entirely on descriptions that lacked a natural `: ` / ` — `
// break, which would then render the whole paragraph as one giant bold
// headline). The `cardId` chip at the top already serves as the title;
// the description below it stays a single uniformly-styled paragraph.
// ---------------------------------------------------------------------------

/**
 * Wrap recognised "code-shaped" substrings in `<code>` so the reader's
 * eye can lock on to tool names and SDK class paths.
 *
 * Recognised:
 *   * snake_case_tokens (≥1 underscore, lowercase + digits + underscores)
 *   * dotted-path identifiers ending in `API` (e.g. `MalwareProtectionPolicyAPI`)
 *
 * Everything else is passed through verbatim. The function returns a
 * mixed array of strings and `<code>` React nodes ready for inline use
 * inside a `<p>` or `<span>`.
 */
function renderWithCode(text: string): React.ReactNode[] {
  // Two alternation arms:
  //   1. snake_case: \b[a-z][a-z0-9]*(?:_[a-z0-9]+)+\b
  //   2. dotted CamelCase ending in API: \b[A-Za-z][\w.]*API\b
  const tokenRe = /\b([a-z][a-z0-9]*(?:_[a-z0-9]+)+|[A-Za-z][\w.]*API)\b/g;
  const parts: React.ReactNode[] = [];
  let last = 0;
  let m: RegExpExecArray | null;
  let key = 0;
  while ((m = tokenRe.exec(text)) !== null) {
    if (m.index > last) {
      parts.push(text.slice(last, m.index));
    }
    parts.push(
      <code key={`c${key++}`} className={styles.inlineCode}>
        {m[0]}
      </code>,
    );
    last = m.index + m[0].length;
  }
  if (last < text.length) {
    parts.push(text.slice(last));
  }
  return parts;
}

// Characters above which a card collapses its description behind a
// "Show more" expander. Picked so the typical short descriptions (the
// one-sentence ZDX entries, the ZPA category lines) stay fully visible
// without a toggle, while the multi-paragraph ZIA singletons collapse
// to a digestible preview.
const BODY_PREVIEW_LIMIT = 180;

/**
 * Trim a string to ``limit`` characters at a word boundary and append a
 * single horizontal-ellipsis. Avoids cutting `snake_case_tokens` in
 * half mid-word, which would defeat the `renderWithCode()` pattern
 * matcher and leave half a token unwrapped.
 */
function truncateAtWord(text: string, limit: number): string {
  if (text.length <= limit) return text;
  const sliced = text.slice(0, limit);
  const lastSpace = sliced.lastIndexOf(" ");
  const cut = lastSpace > limit * 0.6 ? lastSpace : limit;
  return sliced.slice(0, cut).trimEnd() + "…";
}

// ---------------------------------------------------------------------------
// Card grid
// ---------------------------------------------------------------------------

/**
 * Single toolset card. Lives in its own component so the "Show more"
 * expander can hold local `useState` without re-rendering the entire
 * grid on every click.
 */
function ToolsetCard({ toolset }: { toolset: ToolsetEntry }): React.ReactElement {
  const [expanded, setExpanded] = useState(false);
  const desc = toolset.description.trim();
  const isLong = desc.length > BODY_PREVIEW_LIMIT;
  const visible =
    !isLong || expanded ? desc : truncateAtWord(desc, BODY_PREVIEW_LIMIT);

  return (
    <article className={styles.card}>
      <div className={styles.cardId}>{toolset.id}</div>
      <p className={styles.cardBody}>{renderWithCode(visible)}</p>
      {isLong && (
        <button
          type="button"
          onClick={() => setExpanded((v) => !v)}
          className={styles.cardExpand}
          aria-expanded={expanded}
        >
          {expanded ? "Show less" : "Show more"}
          <span className={styles.cardExpandIcon} aria-hidden="true">
            {expanded ? "−" : "+"}
          </span>
        </button>
      )}
      <div className={styles.cardFooter}>
        <span className={styles.toolCount}>
          {toolset.always_on
            ? "always loaded"
            : `${toolset.tool_count} ${toolset.tool_count === 1 ? "tool" : "tools"}`}
        </span>
        {toolset.always_on ? (
          <span className={`${styles.badge} ${styles.badgeAlwaysOn}`}>
            always on
          </span>
        ) : toolset.default ? (
          <span className={`${styles.badge} ${styles.badgeDefault}`}>
            default-on
          </span>
        ) : (
          <span className={`${styles.badge} ${styles.badgeOptional}`}>
            opt-in
          </span>
        )}
      </div>
    </article>
  );
}

/**
 * Rich card-grid view of the Zscaler MCP toolset catalog.
 *
 * Replaces the dense markdown tables that were previously rendered in
 * `docs-site/docs/guides/toolsets.md`. Cards group by service so an
 * admin scanning the page can answer the two questions they actually
 * have ("what's available for ZIA?" and "is it on by default?")
 * without reading a wall of small-text "Coverage" cells.
 *
 * Data is generated from `zscaler_mcp/common/toolsets.py` by the
 * project's docgen — see `make generate-docs`. Editing the JSON by
 * hand is a no-op since CI runs `make check-docs` and will overwrite
 * any drift.
 */
export default function ToolsetsCatalog(): React.ReactElement {
  const [query, setQuery] = useState("");

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    if (!q) return catalog.services;
    return catalog.services
      .map((svc) => ({
        ...svc,
        toolsets: svc.toolsets.filter((ts) =>
          [ts.id, ts.description, svc.code, svc.description]
            .join(" ")
            .toLowerCase()
            .includes(q),
        ),
      }))
      .filter((svc) => svc.toolsets.length > 0);
  }, [query]);

  const totalToolsets = useMemo(
    () => catalog.services.reduce((acc, svc) => acc + svc.toolsets.length, 0),
    [],
  );
  const totalTools = useMemo(
    () =>
      catalog.services.reduce(
        (acc, svc) =>
          acc + svc.toolsets.reduce((a, ts) => a + ts.tool_count, 0),
        0,
      ),
    [],
  );

  return (
    <div className={styles.catalog}>
      <div className={styles.catalogHeader}>
        <div className={styles.catalogStats}>
          <span>
            <strong>{totalToolsets}</strong> toolsets
          </span>
          <span className={styles.catalogStatsDivider} aria-hidden="true">
            ·
          </span>
          <span>
            <strong>{totalTools}</strong> tools
          </span>
          <span className={styles.catalogStatsDivider} aria-hidden="true">
            ·
          </span>
          <span>
            <strong>{catalog.services.length}</strong> services
          </span>
        </div>
        <label className={styles.searchWrap}>
          <span className={styles.searchIcon} aria-hidden="true">
            ⌕
          </span>
          <input
            type="search"
            placeholder="Filter toolsets by id, description, or service…"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            className={styles.searchInput}
            aria-label="Filter toolsets"
          />
          {query && (
            <button
              type="button"
              onClick={() => setQuery("")}
              className={styles.searchClear}
              aria-label="Clear filter"
            >
              ×
            </button>
          )}
        </label>
      </div>

      {filtered.length === 0 ? (
        <div className={styles.empty}>
          No toolsets match <code>{query}</code>.
        </div>
      ) : (
        filtered.map((svc) => (
          <section key={svc.code} className={styles.serviceSection}>
            <header className={styles.serviceHeader}>
              <span className={styles.serviceCode}>{svc.code}</span>
              {svc.description && (
                <span className={styles.servicePill}>{svc.description}</span>
              )}
              <span className={styles.serviceCount}>
                {svc.toolsets.length}{" "}
                {svc.toolsets.length === 1 ? "toolset" : "toolsets"}
              </span>
            </header>
            <div className={styles.cardGrid}>
              {svc.toolsets.map((ts) => (
                <ToolsetCard key={ts.id} toolset={ts} />
              ))}
            </div>
          </section>
        ))
      )}
    </div>
  );
}
