import React from "react";
import Link from "@docusaurus/Link";
import styles from "./styles.module.css";

type Feature = {
  title: string;
  description: string;
  link: string;
  linkLabel: string;
  icon: React.JSX.Element;
};

const features: Feature[] = [
  {
    title: "AI-Powered Zero Trust Operations",
    description:
      "Let AI agents triage threats, audit policies, and automate routine changes across the entire Zscaler Zero Trust Exchange — without leaving your assistant.",
    link: "/docs/getting-started/quickstart",
    linkLabel: "Quickstart",
    icon: (
      <svg viewBox="0 0 24 24" width="48" height="48" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
        <path d="M13 2L3 14h7l-1 8 10-12h-7l1-8z" />
      </svg>
    ),
  },
  {
    title: "Full-Spectrum Service Coverage",
    description:
      "300+ tools across ZPA, ZIA, ZDX, ZCC, ZTW, ZIdentity, EASM, Z-Insights, and ZMS — every major service of the Zero Trust Exchange, behind one MCP interface.",
    link: "/docs/services/overview",
    linkLabel: "Browse services",
    icon: (
      <svg viewBox="0 0 24 24" width="48" height="48" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
        <rect x="3" y="3" width="7" height="7" rx="1" />
        <rect x="14" y="3" width="7" height="7" rx="1" />
        <rect x="3" y="14" width="7" height="7" rx="1" />
        <rect x="14" y="14" width="7" height="7" rx="1" />
      </svg>
    ),
  },
  {
    title: "Deploy Anywhere",
    description:
      "Run locally via CLI or Docker, or deploy to Amazon Bedrock AgentCore, Azure Container Apps / AKS / Foundry, or Google Cloud Run / GKE / Vertex AI Agent Engine.",
    link: "/docs/deployment/docker",
    linkLabel: "Deployment options",
    icon: (
      <svg viewBox="0 0 24 24" width="48" height="48" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
        <path d="M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z" />
        <polyline points="3.27 6.96 12 12.01 20.73 6.96" />
        <line x1="12" y1="22.08" x2="12" y2="12" />
      </svg>
    ),
  },
  {
    title: "Secure by Default",
    description:
      "Read-only by default. Write tools are opt-in and individually allowlistable. Destructive actions require HMAC-confirmed elicitation tokens — prompt-injection-proof.",
    link: "/docs/security/write-operations",
    linkLabel: "Security model",
    icon: (
      <svg viewBox="0 0 24 24" width="48" height="48" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
        <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />
      </svg>
    ),
  },
  {
    title: "OneAPI Authentication",
    description:
      "A single set of ZIdentity OAuth credentials authenticates the server to every Zscaler service — no per-product API key juggling.",
    link: "/docs/getting-started/authentication",
    linkLabel: "Authentication guide",
    icon: (
      <svg viewBox="0 0 24 24" width="48" height="48" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
        <rect x="3" y="11" width="18" height="11" rx="2" ry="2" />
        <path d="M7 11V7a5 5 0 0 1 10 0v4" />
      </svg>
    ),
  },
  {
    title: "Native Editor Integrations",
    description:
      "First-class plugins for Claude Desktop, Claude Code, Cursor, Gemini CLI, Kiro IDE, and VS Code + Copilot — install in one command, start prompting.",
    link: "/docs/integrations/claude",
    linkLabel: "Editor integrations",
    icon: (
      <svg viewBox="0 0 24 24" width="48" height="48" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
        <polyline points="16 18 22 12 16 6" />
        <polyline points="8 6 2 12 8 18" />
      </svg>
    ),
  },
];

export default function Features(): React.JSX.Element {
  return (
    <section className={styles.features}>
      <div className={styles.container}>
        <div className={styles.sectionHeader}>
          <span className={styles.sectionEyebrow}>Why MCP for Zscaler</span>
          <h2 className={styles.sectionTitle}>
            One server, every Zscaler service, every agent
          </h2>
          <p className={styles.sectionSubtitle}>
            Production-ready MCP server purpose-built for Zero Trust operations
            — drop it into any MCP-capable client and your agent gets the full
            Zero Trust Exchange as native tools.
          </p>
        </div>

        <div className={styles.featuresGrid}>
          {features.map((feature) => (
            <div key={feature.title} className={styles.featureCard}>
              <div className={styles.featureIcon}>{feature.icon}</div>
              <h3 className={styles.featureTitle}>{feature.title}</h3>
              <p className={styles.featureDescription}>{feature.description}</p>
              <Link to={feature.link} className={styles.learnMore}>
                {feature.linkLabel}
              </Link>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
