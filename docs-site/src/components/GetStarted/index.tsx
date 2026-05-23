import React from "react";
import Link from "@docusaurus/Link";
import styles from "./styles.module.css";

type Step = {
  number: number | null;
  title: string;
  description: string;
  link?: string;
  linkUrl?: string;
  isSuccess?: boolean;
};

const steps: Step[] = [
  {
    number: 1,
    title: "Get OneAPI Credentials",
    description:
      "Create an API client in the Zidentity console — a single set of credentials (client ID, client secret, vanity domain) authenticates the server to every Zscaler service.",
    link: "Authentication guide",
    linkUrl: "/docs/getting-started/authentication",
  },
  {
    number: 2,
    title: "Install the Server",
    description:
      "Install with uv, pip, or Docker. Configure with a .env file and choose your transport (stdio, SSE, or streamable-HTTP).",
    link: "Installation",
    linkUrl: "/docs/getting-started/installation",
  },
  {
    number: 3,
    title: "Wire Into Your Editor",
    description:
      "Drop a single MCP config snippet into Claude Desktop, Cursor, Gemini CLI, VS Code Copilot, or Kiro IDE. The server appears as a tool your agent can call.",
    link: "Editor integrations",
    linkUrl: "/docs/usage/editor-integration",
  },
  {
    number: null,
    title: "Start Prompting",
    isSuccess: true,
    description:
      'Try "List my ZPA application segments", "Show the last 10 ZIA URL filtering rules", or "Run a ZDX deep trace from my San Francisco office".',
  },
];

export default function GetStarted(): React.JSX.Element {
  return (
    <section className={styles.getStartedSection}>
      <div className={styles.getStartedContainer}>
        <h2 className={styles.sectionTitle}>Get Started in 3 Steps</h2>
        <p className={styles.sectionSubtitle}>
          From zero to AI-driven Zscaler operations in under five minutes.
        </p>

        <div className={styles.stepsWrapper}>
          <div className={styles.stepsContainer}>
            {steps.map((step, index) => (
              <div key={index} className={styles.stepColumn}>
                <div className={styles.stepCircleWrapper}>
                  <div
                    className={`${styles.stepCircle} ${
                      step.isSuccess ? styles.success : ""
                    }`}
                  >
                    {step.isSuccess ? (
                      <div className={styles.checkIcon}>✓</div>
                    ) : (
                      <span>{step.number}</span>
                    )}
                  </div>
                  {index < steps.length - 1 && (
                    <div className={styles.lineConnector}></div>
                  )}
                </div>
                <div className={styles.stepContent}>
                  <h3 className={styles.stepTitle}>{step.title}</h3>
                  <p className={styles.stepDescription}>{step.description}</p>
                  {step.link && step.linkUrl && (
                    <Link to={step.linkUrl} className={styles.stepLink}>
                      {step.link}
                    </Link>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </section>
  );
}
