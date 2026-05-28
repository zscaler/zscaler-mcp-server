.. _deployment-aws:

AWS
===

Deploy the Zscaler MCP Server on Amazon Bedrock AgentCore, drive the deployed runtime from a local Strands client, manage the deployment via the preview AgentCore Harness service, and store credentials in AWS Secrets Manager.

.. toctree::
   :maxdepth: 1

   amazon-bedrock-agentcore
   strands-agentcore
   aws-harness
   secrets-manager

At a glance
-----------

.. list-table::
   :header-rows: 1
   :widths: 30 70

   * - Page
     - When to use
   * - :doc:`Amazon Bedrock AgentCore <amazon-bedrock-agentcore>`
     - Canonical container path on AWS. CloudFormation one-click + manual AWS CLI methods.
   * - :doc:`Strands Agent client <strands-agentcore>`
     - Local terminal client that talks to a deployed AgentCore Runtime via SigV4-signed ``InvokeAgentRuntime``.
   * - :doc:`AWS Harness <aws-harness>`
     - AgentCore Harness (preview) deployment. Two topologies: ECS Express + ``remote_mcp`` or AgentCore Runtime + Gateway + Cognito.
   * - :doc:`Secrets Manager + Bedrock <secrets-manager>`
     - Three approaches to integrating AWS Secrets Manager with the AgentCore deployment.
