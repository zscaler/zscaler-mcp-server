:orphan:

.. _guides-legacy-index:

Guides (legacy index — content moved)
=====================================

The flat "Guides" tree has been reorganized to mirror the Docusaurus information architecture. Use the top-level sidebar to navigate:

- **Deployment** — every cloud (AWS / Azure / GCP), Kubernetes (Helm), and local (setup script / Docker) target. See :doc:`../deployment/index`.
- **Integrations** — MCP clients (Claude / Cursor / Gemini / Kiro / VS Code) and registries (Cursor / Claude / Official MCP / Docker / GitHub). See :doc:`../integrations/index`.
- **Security** — write operations, MCP client auth, TLS / hardening, output sanitization, process lifecycle. See :doc:`../security/index`.
- **Development** — contributing, building from source, MCP server internals (JMESPath, audit logging). See :doc:`../development/index`.
- **Help & Support** — troubleshooting, support channels. See :doc:`../help-and-support/index`.
- **Changelog** — :doc:`release-notes`.

This page is kept as an orphan so existing inbound links still resolve, but it is no longer surfaced in the sidebar. All former targets remain reachable via the categories above.

.. toctree::
   :hidden:

   configuration
   examples
   docker
   jmespath-filtering
   audit-logging
   gcp-cloud-run
   gcp-gke
   gcp-compute-engine-vm
   gcp-adk-agent
   azure-deployment
   azure-ai-foundry
   amazon-bedrock-agentcore
   aws-harness
   strands-agentcore
   secrets-manager
   helm-chart
   setup-script
   entra-id-oidcproxy
   claude-desktop-extension
   troubleshooting
   support
   release-notes
   deployment-aws
   deployment-azure
   deployment-gcp
   deployment-kubernetes
   deployment-local
