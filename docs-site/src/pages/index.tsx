import React from "react";
import Layout from "@theme/Layout";
import useDocusaurusContext from "@docusaurus/useDocusaurusContext";
import Hero from "../components/Hero";
import Features from "../components/Features";
import GetStarted from "../components/GetStarted";

export default function Home(): React.JSX.Element {
  const { siteConfig } = useDocusaurusContext();
  return (
    <Layout
      title={siteConfig.title}
      description="Zscaler MCP Server — connect AI agents to the Zscaler Zero Trust Exchange via the Model Context Protocol."
    >
      <Hero />
      <Features />
      <GetStarted />
    </Layout>
  );
}
