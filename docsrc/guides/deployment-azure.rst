.. _deployment-azure:

Azure
=====

Deploy the Zscaler MCP Server to Azure Container Apps, an Azure Virtual Machine, or Azure Kubernetes Service (Preview); optionally create an Azure AI Foundry agent backed by the deployed MCP server; and configure Microsoft Entra ID as the OIDCProxy identity provider.

Video walkthrough
-----------------

.. image:: https://raw.githubusercontent.com/zscaler/zscaler-mcp-server/master/assets/azure_complete.png
   :alt: Video: Zscaler Integration MCP Server in Azure — complete walkthrough
   :target: https://zscaler.wistia.com/medias/lk72alp7wv
   :align: center
   :width: 720px

End-to-end walkthrough of every deployment target in this guide — Container Apps, Virtual Machine, AKS, and the Azure AI Foundry agent. Click the thumbnail to watch the complete walkthrough, or jump to a per-target walkthrough below:

.. list-table::
   :header-rows: 1
   :widths: 50 50

   * - Target
     - Walkthrough
   * - Azure Container Apps
     - `Watch on Wistia <https://zscaler.wistia.com/medias/4ddig7h580>`__
   * - Azure Virtual Machine
     - `Watch on Wistia <https://zscaler.wistia.com/medias/7zz9cvhga2>`__
   * - Azure Kubernetes Service (Preview)
     - `Watch on Wistia <https://zscaler.wistia.com/medias/yxd5k8hzh3>`__
   * - Azure AI Foundry Agent
     - `Watch on Wistia <https://zscaler.wistia.com/medias/2j2t9twzfb>`__

.. toctree::
   :maxdepth: 1

   azure-deployment
   azure-ai-foundry
   entra-id-oidcproxy

At a glance
-----------

.. list-table::
   :header-rows: 1
   :widths: 30 70

   * - Page
     - When to use
   * - :doc:`Azure Container Apps / VM / AKS <azure-deployment>`
     - The unified ``azure_mcp_operations.py`` script — interactive deploy of the MCP server to any of the three Azure compute surfaces.
   * - :doc:`Azure AI Foundry Agent <azure-ai-foundry>`
     - Create a GPT-4o agent in Foundry that uses the deployed MCP server as a tool. Includes the full portal walkthrough with screenshots.
   * - :doc:`Entra ID OIDCProxy <entra-id-oidcproxy>`
     - End-to-end walkthrough for wiring Microsoft Entra ID as the OIDCProxy IdP, including the Entra-specific ``aud``-claim behaviour.
