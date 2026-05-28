.. _deployment-gcp:

Google Cloud
============

Deploy the Zscaler MCP Server to Google Cloud Run, Google Kubernetes Engine, or a Compute Engine VM. The Google ADK Agent path runs the MCP server as a co-located subprocess inside a Gemini-powered agent container.

Video walkthrough
-----------------

.. image:: https://raw.githubusercontent.com/zscaler/zscaler-mcp-server/master/assets/gcp_complete.png
   :alt: Video: Zscaler Integration MCP Server in GCP — complete walkthrough
   :target: https://zscaler.wistia.com/medias/13jxjizk3r
   :align: center
   :width: 720px

End-to-end walkthrough covering every Google Cloud deployment option in this guide — Cloud Run, GKE, Compute Engine VM, and the ADK Agent (local + Cloud Run). Click the thumbnail to watch the complete walkthrough, or jump to a per-target walkthrough below:

.. list-table::
   :header-rows: 1
   :widths: 50 50

   * - Target
     - Walkthrough
   * - Google Cloud Run
     - `Watch on Wistia <https://zscaler.wistia.com/medias/ns3qmngu25>`__
   * - Google Kubernetes Engine (GKE)
     - `Watch on Wistia <https://zscaler.wistia.com/medias/n6w0uy6v8o>`__
   * - Google ADK Agent (Cloud Run)
     - `Watch on Wistia <https://zscaler.wistia.com/medias/modpfk1blb>`__

.. note::

   Compute Engine VM has no dedicated walkthrough yet — see the complete walkthrough above for full coverage.

.. toctree::
   :maxdepth: 1

   gcp-cloud-run
   gcp-gke
   gcp-compute-engine-vm
   gcp-adk-agent

At a glance
-----------

.. list-table::
   :header-rows: 1
   :widths: 30 70

   * - Page
     - When to use
   * - :doc:`Cloud Run <gcp-cloud-run>`
     - Managed, serverless container deployment. Fastest path; pulls the Docker Hub image directly.
   * - :doc:`GKE <gcp-gke>`
     - Kubernetes Deployment on Autopilot (or existing cluster) with Workload Identity and a LoadBalancer Service.
   * - :doc:`Compute Engine VM <gcp-compute-engine-vm>`
     - Debian 12 VM with the PyPI package and ``systemd``. Bypasses Cloud Run's IAM constraints in enterprise GCP organizations.
   * - :doc:`Google ADK Agent <gcp-adk-agent>`
     - Gemini-powered ADK agent that bundles the MCP server as a co-located subprocess. Supports local, Cloud Run, Agent Engine, and Agentspace.
