import React, { useEffect, useRef, useState } from "react";
import { useHistory } from "@docusaurus/router";
import Link from "@docusaurus/Link";
import useBaseUrl from "@docusaurus/useBaseUrl";
import styles from "./styles.module.css";

/**
 * Popular topic pills shown beneath the search box.
 *
 * Each pill carries (a) the query string we drop into the visible
 * search input and (b) a small curated list of result entries that
 * render below the input the moment the pill is clicked. This mirrors
 * the OneAPI Automation Hub "Popular topics" UX (a query string plus a
 * dropdown of matching pages).
 *
 * Why curated instead of wiring the search-local plugin in here:
 *
 *   `@easyops-cn/docusaurus-search-local` no-ops in dev (its
 *   `searchByWorker` returns `[]` unless `NODE_ENV === "production"`),
 *   so any path that uses the plugin's autocomplete would look broken
 *   while we're authoring docs locally. A static curated map is
 *   correct in dev and prod, doesn't depend on the Lunr index, and
 *   gives editorial control over which 3-4 pages a reader most likely
 *   wants when they click "Installation" vs the raw 12 the index would
 *   return. Free-form text entry still submits to `/search?q=` on
 *   Enter — that one DOES need the prod build, same as before.
 */
type TopicResult = {
  title: string;
  path: string; // breadcrumb-style hint, e.g. "Getting Started › Installation"
  to: string;
};

type Topic = {
  label: string;
  query: string;
  results: TopicResult[];
};

const POPULAR_TOPICS: Topic[] = [
  {
    label: "Installation",
    query: "installation",
    results: [
      {
        title: "Installation",
        path: "Getting Started › Installation",
        to: "/docs/getting-started/installation",
      },
      {
        title: "Quickstart",
        path: "Getting Started › Quickstart",
        to: "/docs/getting-started/quickstart",
      },
      {
        title: "Building from source",
        path: "Development › Building from source",
        to: "/docs/development/building-from-source",
      },
      {
        title: "Docker deployment",
        path: "Deployment › Docker",
        to: "/docs/deployment/docker",
      },
    ],
  },
  {
    label: "Authentication",
    query: "authentication",
    results: [
      {
        title: "Authentication",
        path: "Getting Started › Authentication",
        to: "/docs/getting-started/authentication",
      },
      {
        title: "MCP Client Authentication",
        path: "Security › MCP Client Auth",
        to: "/docs/security/mcp-client-auth",
      },
      {
        title: "Entra ID OIDCProxy",
        path: "Deployment › Entra ID OIDCProxy",
        to: "/docs/deployment/entra-id-oidcproxy",
      },
    ],
  },
  {
    label: "Toolsets",
    query: "toolsets",
    results: [
      {
        title: "Toolsets catalog",
        path: "Guides › Toolsets",
        to: "/docs/guides/toolsets",
      },
      {
        title: "Supported tools",
        path: "Guides › Supported Tools",
        to: "/docs/guides/supported-tools",
      },
      {
        title: "Skills",
        path: "Guides › Skills",
        to: "/docs/guides/skills",
      },
    ],
  },
  {
    label: "Supported Tools",
    query: "supported tools",
    results: [
      {
        title: "Supported tools",
        path: "Guides › Supported Tools",
        to: "/docs/guides/supported-tools",
      },
      {
        title: "Toolsets catalog",
        path: "Guides › Toolsets",
        to: "/docs/guides/toolsets",
      },
      {
        title: "Services overview",
        path: "Services › Overview",
        to: "/docs/services/overview",
      },
    ],
  },
  {
    label: "Docker",
    query: "docker",
    results: [
      {
        title: "Docker deployment",
        path: "Deployment › Docker",
        to: "/docs/deployment/docker",
      },
      {
        title: "Azure Container Apps",
        path: "Deployment › Azure",
        to: "/docs/deployment/azure",
      },
      {
        title: "Google Cloud",
        path: "Deployment › GCP",
        to: "/docs/deployment/gcp",
      },
    ],
  },
  {
    label: "Cursor",
    query: "cursor",
    results: [
      {
        title: "Cursor integration",
        path: "Integrations › Cursor",
        to: "/docs/integrations/cursor",
      },
      {
        title: "Editor integration",
        path: "Usage › Editor Integration",
        to: "/docs/usage/editor-integration",
      },
      {
        title: "Service configuration",
        path: "Usage › Service Configuration",
        to: "/docs/usage/service-configuration",
      },
    ],
  },
];

/**
 * Headline stats shown beneath the hero. Drives the "this is a serious
 * piece of software" first impression — same pattern Vercel, Astro,
 * Supabase use on their landing pages.
 */
const STATS: Array<{ value: string; label: string }> = [
  { value: "300+", label: "MCP tools" },
  { value: "52", label: "toolsets" },
  { value: "9", label: "Zscaler services" },
  { value: "6", label: "IDE & CLI clients" },
  { value: "3", label: "cloud platforms" },
];

export default function Hero(): React.JSX.Element {
  const history = useHistory();
  const [query, setQuery] = useState("");
  const [activeTopic, setActiveTopic] = useState<Topic | null>(null);
  const inputRef = useRef<HTMLInputElement | null>(null);
  const dropdownWrapRef = useRef<HTMLDivElement | null>(null);
  const searchBase = useBaseUrl("/search");

  const runSearch = (raw: string) => {
    const trimmed = raw.trim();
    if (!trimmed) return;
    // Docusaurus' local search plugin reads `q` from `/search`. In dev
    // the page shows a "build first" warning because the plugin only
    // emits the Lunr index on `postBuild` — that's documented
    // upstream, not something we can patch from here.
    history.push(`${searchBase}?q=${encodeURIComponent(trimmed)}`);
  };

  const onSubmit = (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setActiveTopic(null);
    runSearch(query);
  };

  /**
   * Pill click → fill the input + show that topic's curated dropdown.
   * Mirrors the Automation Hub interaction (screenshot 3 in the
   * referenced bug report): the search input populates with the
   * topic label and a small dropdown of matching pages appears
   * underneath.
   */
  const onTopicClick = (topic: Topic) => {
    setQuery(topic.query);
    setActiveTopic(topic);
    inputRef.current?.focus();
  };

  // Dismiss the curated dropdown on outside clicks or Escape, the same
  // affordance every dropdown on the web has. Without this it sticks
  // open forever, which feels broken.
  useEffect(() => {
    if (!activeTopic) return;

    const onClick = (event: MouseEvent) => {
      const wrap = dropdownWrapRef.current;
      if (wrap && !wrap.contains(event.target as Node)) {
        setActiveTopic(null);
      }
    };
    const onKey = (event: KeyboardEvent) => {
      if (event.key === "Escape") setActiveTopic(null);
    };
    document.addEventListener("mousedown", onClick);
    document.addEventListener("keydown", onKey);
    return () => {
      document.removeEventListener("mousedown", onClick);
      document.removeEventListener("keydown", onKey);
    };
  }, [activeTopic]);

  return (
    <section className={styles.heroContainer}>
      <div className={styles.heroInner}>
        <div className={styles.heroLeft}>
          <h1 className={styles.heroTitle}>
            Connect <span className={styles.heroTitleAccent}>AI agents</span>{" "}
            to the Zscaler Zero Trust Exchange
          </h1>
          <p className={styles.heroSubtitle}>
            300+ MCP tools across ZPA, ZIA, ZDX, ZCC, ZTW, ZIdentity, EASM,
            Z-Insights, and ZMS. Read-only by default, HMAC-confirmed writes,
            OneAPI authentication baked in.
          </p>
          <div className={styles.heroCta}>
            <Link
              to="/docs/getting-started/installation"
              className={styles.heroButton}
            >
              Get Started
              <span className={styles.heroButtonIcon}>→</span>
            </Link>
            <Link
              to="https://github.com/zscaler/zscaler-mcp-server"
              className={styles.heroButtonSecondary}
            >
              View on GitHub
            </Link>
          </div>
        </div>

        <div className={styles.heroRight}>
          <div className={styles.searchWrap} ref={dropdownWrapRef}>
            <form
              className={styles.searchForm}
              role="search"
              onSubmit={onSubmit}
            >
              <span className={styles.searchIcon} aria-hidden="true">
                <svg
                  width="18"
                  height="18"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="2"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                >
                  <circle cx="11" cy="11" r="7" />
                  <line x1="21" y1="21" x2="16.65" y2="16.65" />
                </svg>
              </span>
              <input
                ref={inputRef}
                type="search"
                className={styles.searchInput}
                placeholder="Search tools, services, deployment guides…"
                aria-label="Search the documentation"
                value={query}
                onChange={(e) => {
                  setQuery(e.target.value);
                  // Typing into the box clears the curated dropdown —
                  // it's a topic-pill affordance, not a general typeahead.
                  if (activeTopic) setActiveTopic(null);
                }}
              />
              <kbd className={styles.searchKbd}>↵</kbd>
            </form>

            {activeTopic && (
              <div
                className={styles.suggestionDropdown}
                role="listbox"
                aria-label={`Top pages for ${activeTopic.label}`}
              >
                {activeTopic.results.map((result) => (
                  <Link
                    key={result.to}
                    to={result.to}
                    className={styles.suggestionItem}
                    role="option"
                    onClick={() => setActiveTopic(null)}
                  >
                    <span className={styles.suggestionTitle}>
                      {result.title}
                    </span>
                    <span className={styles.suggestionPath}>{result.path}</span>
                  </Link>
                ))}
                <button
                  type="button"
                  className={styles.suggestionFooter}
                  onClick={() => {
                    setActiveTopic(null);
                    runSearch(activeTopic.query);
                  }}
                >
                  See all results for &ldquo;{activeTopic.label}&rdquo; →
                </button>
              </div>
            )}
          </div>

          <div className={styles.popularTopics}>
            <span className={styles.popularTopicsLabel}>↗ Popular topics</span>
            <div className={styles.popularTopicsPills}>
              {POPULAR_TOPICS.map((topic) => (
                <button
                  key={topic.query}
                  type="button"
                  className={styles.topicPill}
                  onClick={() => onTopicClick(topic)}
                >
                  {topic.label}
                </button>
              ))}
            </div>
          </div>

          {/* Faux terminal preview — gives the right column visual weight
              and shows the "install + first tool call" story in 3 lines. */}
          <div className={styles.terminal} aria-hidden="true">
            <div className={styles.terminalChrome}>
              <span className={styles.terminalDot} data-color="red" />
              <span className={styles.terminalDot} data-color="amber" />
              <span className={styles.terminalDot} data-color="green" />
              <span className={styles.terminalTitle}>~/zscaler-mcp</span>
            </div>
            <pre className={styles.terminalBody}>
              <span className={styles.codeMuted}># Install via uv (fastest)</span>
              {"\n"}
              <span className={styles.codePrompt}>$</span>{" "}
              <span className={styles.codeCmd}>uvx zscaler-mcp</span>
              {"\n\n"}
              <span className={styles.codeMuted}># Then in Claude / Cursor / Gemini CLI:</span>
              {"\n"}
              <span className={styles.codeStr}>"List my ZPA application segments"</span>
            </pre>
          </div>
        </div>
      </div>

      <div className={styles.statsBar}>
        <div className={styles.statsInner}>
          {STATS.map((stat) => (
            <div key={stat.label} className={styles.stat}>
              <span className={styles.statValue}>{stat.value}</span>
              <span className={styles.statLabel}>{stat.label}</span>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
