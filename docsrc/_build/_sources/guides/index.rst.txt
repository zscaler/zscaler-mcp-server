Guides
======

This section contains comprehensive guides for using the Zscaler Integrations MCP Server.

.. toctree::
   :maxdepth: 1

   configuration
   examples
   gcp-cloud-run
   gcp-gke
   gcp-compute-engine-vm
   gcp-adk-agent
   azure-deployment
   amazon-bedrock-agentcore
   troubleshooting
   support
   release-notes

Configuration Guide
-------------------

Learn how to configure the Zscaler Integrations MCP Server for your environment.

Examples
--------

See practical examples of using the MCP server with various Zscaler services.

GCP Cloud Run Deployment
------------------------

Deploy the Zscaler Integrations MCP Server to Google Cloud Run with optional GCP Secret Manager integration, automated deployment script, and Zscaler auth mode for client authentication.

GCP GKE Deployment
------------------

Deploy the Zscaler Integrations MCP Server to Google Kubernetes Engine (Autopilot or existing cluster) with GCP Secret Manager integration, Workload Identity, and a LoadBalancer Service for external access.

GCP Compute Engine VM Deployment
--------------------------------

Deploy the Zscaler Integrations MCP Server to a Debian 12 Compute Engine VM with the PyPI package, ``systemd``, and optional GCP Secret Manager integration. The VM target avoids Cloud Run's IAM constraints in enterprise GCP organizations.

GCP ADK Agent Deployment
------------------------

Deploy the Gemini-powered Zscaler ADK Agent (built with Google's Agent Development Kit) to local development, Cloud Run, Vertex AI Agent Engine, or Google Agentspace. The MCP server runs as a co-located subprocess inside the agent container.

Azure Deployment
----------------

Deploy the Zscaler Integrations MCP Server to Azure Container Apps, an Azure Virtual Machine, or Azure Kubernetes Service (Preview), and optionally create an Azure AI Foundry agent that uses the MCP server as a tool — all through the unified ``azure_mcp_operations.py`` script.

Amazon Bedrock AgentCore Deployment
-----------------------------------

Learn how to deploy the Zscaler Integrations MCP Server to Amazon Bedrock AgentCore with proper IAM configuration and environment setup.

Troubleshooting
---------------

Common issues and their solutions.

Support
-------

Support information and resources.

Release Notes
-------------

Information about releases and changes.
