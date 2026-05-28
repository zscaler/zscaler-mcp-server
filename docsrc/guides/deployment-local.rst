.. _deployment-local:

Local
=====

Run the Zscaler MCP Server locally — fastest path for first-time setup and for connecting AI clients on the same machine. Choose the interactive setup script for a guided experience, or the raw Docker reference when you need fine control.

.. toctree::
   :maxdepth: 1

   setup-script
   docker

At a glance
-----------

.. list-table::
   :header-rows: 1
   :widths: 30 70

   * - Page
     - When to use
   * - :doc:`One-step setup script <setup-script>`
     - Recommended starting point. Interactive — picks transport, auth mode, ``.env`` file, pulls the image, verifies the endpoint, and writes the MCP client config for every AI agent detected on your machine.
   * - :doc:`Docker <docker>`
     - Raw ``docker run`` reference. Use when integrating into existing infrastructure (Compose, Kubernetes, systemd, init containers).
