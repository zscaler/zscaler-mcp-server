.. _deployment:

Deployment
==========

Run the Zscaler MCP Server everywhere it's expected to run — locally for first-time setup, on every major hyperscaler (AWS, Azure, Google Cloud), or inside any Kubernetes cluster via Helm.

Each branch below is a complete tree: pick your platform on the left, and the per-target installation guide for that platform is one click away.

.. toctree::
   :maxdepth: 2

   ../guides/deployment-local
   ../guides/deployment-aws
   ../guides/deployment-azure
   ../guides/deployment-gcp
   ../guides/deployment-kubernetes

At a glance
-----------

.. list-table::
   :header-rows: 1
   :widths: 22 78

   * - Platform
     - Targets covered
   * - :doc:`Local <../guides/deployment-local>`
     - One-step setup script (guided, recommended) · Raw Docker reference
   * - :doc:`AWS <../guides/deployment-aws>`
     - Bedrock AgentCore · Strands Agent client · AWS Harness (preview) · Secrets Manager + Bedrock
   * - :doc:`Azure <../guides/deployment-azure>`
     - Container Apps / Virtual Machine / AKS (preview) · AI Foundry Agent · Entra ID OIDCProxy
   * - :doc:`Google Cloud <../guides/deployment-gcp>`
     - Cloud Run · GKE · Compute Engine VM · Google ADK Agent
   * - :doc:`Kubernetes <../guides/deployment-kubernetes>`
     - Helm chart — any cluster (EKS, GKE, AKS, OpenShift, k3s, kind, on-prem)
