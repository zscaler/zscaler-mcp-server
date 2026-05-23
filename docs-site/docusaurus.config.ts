import type * as Preset from "@docusaurus/preset-classic";
import type { Config } from "@docusaurus/types";
import { themes as prismThemes } from "prism-react-renderer";

const config: Config = {
  title: "Zscaler MCP Server",
  tagline: "Connect AI assistants to the Zscaler Zero Trust Exchange via the Model Context Protocol",
  favicon: "img/zscalerfavicon.svg",

  // GitHub Pages deployment
  // Site served from https://zscaler.github.io/zscaler-mcp-server/
  url: "https://zscaler.github.io",
  baseUrl: "/zscaler-mcp-server/",
  organizationName: "zscaler",
  projectName: "zscaler-mcp-server",
  deploymentBranch: "gh-pages",
  trailingSlash: false,

  onBrokenLinks: "warn",
  // Set "detect" so files with .md extension are treated as plain CommonMark
  // and only files with .mdx extension parse as MDX (avoids `<foo>` in tables
  // being interpreted as JSX in our auto-generated tool reference tables).
  markdown: {
    format: "detect",
    hooks: {
      onBrokenMarkdownLinks: "warn",
      onBrokenMarkdownImages: "warn",
    },
  },

  i18n: {
    defaultLocale: "en",
    locales: ["en"],
  },

  plugins: [
    // Local, fully offline search. Builds a Lunr index at build time and
    // serves it as a static asset — no SaaS dependency, works on GitHub
    // Pages out of the box. Powers both the navbar autocomplete and the
    // `/search` results page the Hero search box submits to.
    [
      require.resolve("@easyops-cn/docusaurus-search-local"),
      {
        hashed: true,
        indexDocs: true,
        indexBlog: false,
        indexPages: true,
        docsRouteBasePath: "/docs",
        highlightSearchTermsOnTargetPage: true,
        explicitSearchResultPath: true,
        searchResultLimits: 12,
      },
    ],
  ],

  presets: [
    [
      "classic",
      {
        docs: {
          path: "docs",
          routeBasePath: "docs",
          sidebarPath: require.resolve("./sidebars.ts"),
          editUrl:
            "https://github.com/zscaler/zscaler-mcp-server/tree/master/docs-site/",
          showLastUpdateAuthor: false,
          showLastUpdateTime: true,
        },
        blog: false,
        theme: {
          customCss: require.resolve("./src/css/custom.css"),
        },
        sitemap: {
          changefreq: "weekly",
          priority: 0.5,
          ignorePatterns: ["/tags/**"],
          filename: "sitemap.xml",
        },
      } satisfies Preset.Options,
    ],
  ],

  themeConfig: {
    image: "img/zscaler-logo.png",
    colorMode: {
      defaultMode: "light",
      disableSwitch: false,
      respectPrefersColorScheme: true,
    },
    docs: {
      sidebar: {
        hideable: true,
        autoCollapseCategories: true,
      },
    },
    navbar: {
      title: "MCP Server",
      logo: {
        alt: "Zscaler",
        src: "img/zscaler.svg",
        href: "/",
      },
      // Top-level shortcuts mirroring the OneAPI Automation Hub's
      // header: Getting Started · Documentation · Toolsets · Integrations
      // · Deployment · Community. Each one is a direct link into the
      // unified left sidebar — no sub-sidebar dropdowns. Custom styling
      // (weight, spacing, hover underline) lives in `src/css/custom.css`
      // under the "Navbar polish" section.
      items: [
        {
          to: "/docs/getting-started/installation",
          label: "Getting Started",
          position: "left",
        },
        {
          to: "/docs/intro",
          label: "Documentation",
          position: "left",
        },
        {
          to: "/docs/guides/toolsets",
          label: "Toolsets",
          position: "left",
        },
        {
          to: "/docs/integrations/claude",
          label: "Integrations",
          position: "left",
        },
        {
          to: "/docs/deployment/docker",
          label: "Deployment",
          position: "left",
        },
        {
          to: "/docs/changelog",
          label: "Changelog",
          position: "left",
        },
        {
          href: "https://community.zscaler.com/s/",
          label: "Community",
          position: "right",
        },
        {
          href: "https://github.com/zscaler/zscaler-mcp-server",
          label: "GitHub",
          position: "right",
        },
      ],
    },
    footer: {
      style: "dark",
      links: [
        {
          title: "Documentation",
          items: [
            {
              label: "Getting Started",
              to: "/docs/getting-started/installation",
            },
            {
              label: "Services",
              to: "/docs/services/overview",
            },
            {
              label: "Integrations",
              to: "/docs/integrations/claude",
            },
            {
              label: "Changelog",
              to: "/docs/changelog",
            },
          ],
        },
        {
          title: "Community",
          items: [
            {
              label: "Zscaler Community",
              href: "https://community.zscaler.com/s/",
            },
            {
              label: "GitHub Issues",
              href: "https://github.com/zscaler/zscaler-mcp-server/issues",
            },
            {
              label: "GitHub Discussions",
              href: "https://github.com/zscaler/zscaler-mcp-server/discussions",
            },
          ],
        },
        {
          title: "More",
          items: [
            {
              label: "GitHub",
              href: "https://github.com/zscaler/zscaler-mcp-server",
            },
            {
              label: "PyPI",
              href: "https://pypi.org/project/zscaler-mcp-server/",
            },
            {
              label: "Docker Hub",
              href: "https://hub.docker.com/r/zscaler/zscaler-mcp-server",
            },
          ],
        },
        {
          title: "Zscaler",
          items: [
            {
              label: "Zscaler.com",
              href: "https://www.zscaler.com",
            },
            {
              label: "Help Center",
              href: "https://help.zscaler.com/",
            },
            {
              label: "Automation Hub",
              href: "https://automate.zscaler.com/",
            },
          ],
        },
      ],
      copyright: `Copyright © ${new Date().getFullYear()} Zscaler, Inc. All rights reserved.`,
    },
    prism: {
      theme: prismThemes.github,
      darkTheme: prismThemes.dracula,
      additionalLanguages: [
        "bash",
        "json",
        "yaml",
        "python",
        "go",
        "docker",
        "hcl",
        "toml",
        "ini",
        "powershell",
      ],
    },
    algolia: undefined,
  } satisfies Preset.ThemeConfig,
};

export default config;
