.. _integration-kiro:

Kiro IDE
========

The Zscaler MCP Server is available as a **Kiro Power**, providing AI-assisted management of the Zscaler Zero Trust Exchange platform directly within the `Kiro IDE <https://kiro.dev>`__.

What's Included
---------------

.. list-table::
   :header-rows: 1
   :widths: 25 35 40

   * - Component
     - Location
     - Purpose
   * - Power manifest
     - ``integrations/kiro/POWER.md``
     - Power metadata, tool reference, workflows, and best practices
   * - MCP config
     - ``integrations/kiro/mcp.json``
     - MCP server connection configuration
   * - Steering files
     - ``integrations/kiro/steering/``
     - 10 service-specific context files for on-demand loading

Steering Files
~~~~~~~~~~~~~~

Steering files are service-specific knowledge documents that Kiro loads on demand based on your request. Each per-service steering file enumerates the **guided skills** (multi-step playbooks under ``skills/``) relevant to that service so Kiro can autoload the right skill before composing an ad-hoc tool sequence.

.. list-table::
   :header-rows: 1
   :widths: 22 28 12 38

   * - Steering File
     - Service
     - Skills
     - Tools
   * - ``zpa.md``
     - ZPA (Private Access)
     - 11
     - 104 — app segments (standard / BA / PRA), policies, connectors, PRA, LSS
   * - ``zia.md``
     - ZIA (Internet Access)
     - 12
     - 149 — cloud firewall, URL filtering, SSL inspection, DLP, ATP, Cloud App Control
   * - ``zdx.md``
     - ZDX (Digital Experience)
     - 7
     - 31 — app scores, device health, alerts, deep traces
   * - ``zins.md``
     - Z-Insights (Analytics)
     - 4
     - 16 — web traffic, cyber incidents, shadow IT, firewall analytics (read-only)
   * - ``zms.md``
     - ZMS (Microsegmentation)
     - 5
     - 20 — agents, resource groups, policy rules, app zones, tags (read-only)
   * - ``zcc.md``
     - ZCC (Client Connector)
     - 1
     - 4 — devices, forwarding profiles, OTP (read-only)
   * - ``ztw.md``
     - ZTW (Workload Segmentation)
     - —
     - 19 — IP groups, network services, cloud accounts
   * - ``easm.md``
     - EASM (Attack Surface)
     - 1
     - 7 — findings, lookalike domains, scan evidence (read-only)
   * - ``zid.md``
     - ZIdentity
     - —
     - 10 — users, groups, identity management (read-only)
   * - ``cross-product.md``
     - Cross-product
     - 1
     - ZCC + ZDX + ZPA + ZIA correlation workflow

Installation
------------

1. Open `Kiro IDE <https://kiro.dev>`__
2. Go to the **Powers** panel → **Add Custom Power**
3. Select **Local Directory** or provide the GitHub URL
4. Point to ``integrations/kiro/``

For official listing in the Kiro Powers marketplace, submit via `kiro.dev/powers/ <https://kiro.dev/powers/>`__.

Prerequisites
-------------

- `Kiro IDE <https://kiro.dev>`__ installed
- `uv <https://docs.astral.sh/uv/>`__ installed (for ``uvx`` method) or Docker
- Zscaler OneAPI credentials configured in ``.env``

Configuration
-------------

The MCP server is configured via ``integrations/kiro/mcp.json``:

.. code-block:: json

   {
     "mcpServers": {
       "zscaler": {
         "command": "uvx",
         "args": ["zscaler-mcp"],
         "env": {
           "ZSCALER_CLIENT_ID": "${ZSCALER_CLIENT_ID}",
           "ZSCALER_CLIENT_SECRET": "${ZSCALER_CLIENT_SECRET}",
           "ZSCALER_CUSTOMER_ID": "${ZSCALER_CUSTOMER_ID}",
           "ZSCALER_VANITY_DOMAIN": "${ZSCALER_VANITY_DOMAIN}"
         }
       }
     }
   }

Alternative: Docker
~~~~~~~~~~~~~~~~~~~

.. code-block:: json

   {
     "mcpServers": {
       "zscaler": {
         "command": "docker",
         "args": [
           "run", "-i", "--rm",
           "--env-file", "/path/to/your/.env",
           "zscaler/zscaler-mcp-server:latest"
         ]
       }
     }
   }

Common Workflows
----------------

The ``POWER.md`` includes detailed workflows for:

- **Application onboarding** (ZPA) — connector group → server group → segment group → app segment → access policy
- **Location onboarding** (ZIA) — static IP → VPN credential → location → activate
- **User troubleshooting** (Cross-product) — ZCC device → ZDX health → ZPA/ZIA policies
- **Security investigation** (Z-Insights) — incidents → locations → timeline → threat breakdown
- **Attack surface review** (EASM) — findings → details → lookalike domains
- **Microsegmentation posture** (ZMS) — agents → resources → resource groups → policies → app zones

Verification
------------

After installation, verify by asking Kiro:

   *"What Zscaler tools are available?"*

or

   *"List my ZPA application segments"*

Resources
---------

- `Kiro IDE documentation <https://kiro.dev>`__
- :doc:`../../skills/index`
- :doc:`../../guides/troubleshooting`
