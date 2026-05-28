.. _development:

Development
===========

Contributor-facing documentation: development workflow, build steps, and the deeper "MCP server internals" reference. If you're consuming the server (not modifying it), the :doc:`Getting Started <../getting-started>` and :doc:`Integrations <../integrations/index>` trees are the better starting points.

.. toctree::
   :maxdepth: 1

   contributing
   building-from-source

.. toctree::
   :maxdepth: 1
   :caption: MCP Server Internals

   ../guides/jmespath-filtering
   ../guides/audit-logging

At a glance
-----------

.. list-table::
   :header-rows: 1
   :widths: 30 70

   * - Page
     - When to use
   * - :doc:`Contributing <contributing>`
     - Project conventions: Conventional Commits, lint / format / tests, how to add a new tool. *External PRs are paused during the public preview* — see the page for the current contribution scope.
   * - :doc:`Building from Source <building-from-source>`
     - Clone, ``uv sync``, ``pip install -e .``, Docker build, ``make`` targets, auto-generated docs refresh, the semantic-release workflow.
   * - :doc:`JMESPath Filtering on List Tools <../guides/jmespath-filtering>`
     - Use the ``query`` parameter on every ``*_list_*`` tool to filter and project results client-side. Standard `JMESPath <https://jmespath.org/>`_ syntax — works the same way for ZIA, ZPA, ZDX, ZCC, ZTW, ZID, EASM, Z-Insights, and ZMS.
   * - :doc:`Tool-Call Audit Logging <../guides/audit-logging>`
     - Opt-in tool-call audit logging via ``--log-tool-calls`` / ``ZSCALER_MCP_LOG_TOOL_CALLS``. Captures every tool invocation (sensitive arguments redacted), duration, and result summary on the ``zscaler_mcp.audit`` logger.
