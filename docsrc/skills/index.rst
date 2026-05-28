.. _skills:

Skills
======

Skills are guided multi-step workflows that an AI agent loads when it recognizes a matching user request. Each skill is a Markdown file (``SKILL.md``) with YAML frontmatter that lives under ``skills/`` in the repository — the same file is consumed by Claude Code, Cursor, and any MCP client that supports the Anthropic skill spec.

The Zscaler MCP Server ships **42 skills** across 8 services and one cross-product workflow.

How skills work
---------------

Each skill has a name, a description (the trigger phrases an admin would use), and a body of step-by-step instructions that reference specific tool names. The matching client auto-activates the skill when the user's prompt fits the description, so an admin can say "block ChatGPT for everyone" and the matching ``zia-create-cloud-app-control-rule`` skill runs without anyone having to remember the tool sequence.

Skills are organized by service. The ``skills/`` directory tree:

.. code-block:: text

   skills/
   ├── zpa/              # 11 skills — application onboarding, policy rules
   ├── zia/              # 12 skills — rule creation, lookups, schedules
   ├── zdx/              #  7 skills — user experience, deep traces, alerts
   ├── zms/              #  5 skills — microsegmentation audits, agents
   ├── zins/             #  4 skills — analytics, shadow IT, incidents
   ├── easm/             #  1 skill  — attack surface review
   ├── zcc/              #  1 skill  — logout OTP for offboarding
   └── cross-product/    #  1 skill  — end-to-end user connectivity

ZPA — Zscaler Private Access (11 skills)
----------------------------------------

.. list-table::
   :header-rows: 1
   :widths: 35 65

   * - Skill
     - What it does
   * - ``zpa-application_segment-onboard``
     - Walk through the full onboarding chain for a standard ZPA application segment: app connector group → server group → segment group → application segment → access policy rule.
   * - ``zpa-application_segment-ba-onboard``
     - Onboard a **Browser Access (BA)** application segment, including BA certificate selection.
   * - ``zpa-application_segment-pra-onboard``
     - Onboard a **Privileged Remote Access (PRA)** application segment, including PRA portal + credentials.
   * - ``zpa-create-access-policy-rule``
     - Create an access policy rule with v2 conditions (APP, APP_GROUP, SAML, SCIM, SCIM_GROUP, PLATFORM, COUNTRY_CODE, POSTURE, TRUSTED_NETWORK, RISK_FACTOR_TYPE, CLIENT_TYPE, MACHINE_GRP, LOCATION, CHROME_ENTERPRISE).
   * - ``zpa-create-conditional-access-rule``
     - Create a conditional access rule that combines identity + device + network conditions.
   * - ``zpa-create-forwarding-policy-rule``
     - Create a client forwarding policy rule.
   * - ``zpa-create-server-group``
     - Create a server group with the right app-connector-group association and optional servers.
   * - ``zpa-create-session-duration-rule``
     - Create a session duration policy rule (also known as Re-Auth policy).
   * - ``zpa-create-timeout-policy-rule``
     - Create a timeout policy rule for idle-session disconnect.
   * - ``zpa-audit-baseline-compliance``
     - Audit a tenant against ZPA security baseline (default rules, posture profiles, isolation policies).
   * - ``zpa-troubleshoot-app-connector``
     - Diagnose app connector connectivity and health.

ZIA — Zscaler Internet Access (12 skills)
-----------------------------------------

.. list-table::
   :header-rows: 1
   :widths: 35 65

   * - Skill
     - What it does
   * - ``zia-create-url-filtering-rule``
     - Create a URL filtering rule with action (ALLOW / BLOCK / CAUTION / ISOLATE), scoped by category, user, group, location, device trust level, and optional schedule.
   * - ``zia-create-firewall-filtering-rule``
     - Create a Cloud Firewall rule (network services, network apps, IP groups, time windows, locations, users).
   * - ``zia-create-ssl-inspection-rule``
     - Create an SSL Inspection policy rule. Auto-resolves friendly cloud-app names to canonical enums.
   * - ``zia-create-cloud-app-control-rule``
     - Create a Cloud App Control rule for a specific application class (file sharing, social, AI/ML, etc.).
   * - ``zia-onboard-location``
     - Onboard a new ZIA location: static IP → VPN credential → location, in the right order.
   * - ``zia-audit-ssl-inspection-bypass``
     - Audit which categories, applications, and URL classifications are bypassed in SSL Inspection.
   * - ``zia-check-user-url-access``
     - Determine whether a given user can reach a given URL (URL categorization + rule simulation).
   * - ``zia-investigate-sandbox``
     - Pull a Sandbox report for an MD5/SHA-256 and surface the verdict.
   * - ``zia-investigate-url-category``
     - Look up a URL's category, super-category, and any custom-category overrides.
   * - ``zia-look-up-cloud-app-name``
     - Resolve a friendly cloud-application name (e.g. ``ChatGPT``) to its canonical enum (e.g. ``OPEN_AI_CHATGPT``) used by SSL Inspection / Web DLP / Cloud App Control / File Type Control rules.
   * - ``zia-look-up-rule-targets``
     - Resolve user / group / department / location / time-window names to the IDs the rule API requires.
   * - ``zia-manage-time-interval``
     - Create / update / list reusable Time Interval objects referenced by policy rules via the ``time_windows`` field.

ZDX — Digital Experience (7 skills)
-----------------------------------

.. list-table::
   :header-rows: 1
   :widths: 35 65

   * - Skill
     - What it does
   * - ``zdx-troubleshoot-user-experience``
     - Investigate a user's experience: device health, app scores, network path, active alerts.
   * - ``zdx-analyze-application-health``
     - Score an application across the user base and surface affected users / locations.
   * - ``zdx-compare-location-experience``
     - Compare experience metrics across two or more office locations.
   * - ``zdx-investigate-alerts``
     - Walk active and historical alerts, with affected devices and root-cause hints.
   * - ``zdx-investigate-multi-app-outage``
     - Correlate scores across multiple applications to identify a common path-of-failure.
   * - ``zdx-diagnose-deeptrace``
     - Start a deep trace, wait for the result, and interpret the trace output.
   * - ``zdx-audit-software-inventory``
     - Inventory installed software across the device fleet and identify outdated or unauthorized packages.

ZMS — Microsegmentation (5 skills)
-----------------------------------

.. list-table::
   :header-rows: 1
   :widths: 35 65

   * - Skill
     - What it does
   * - ``zms-audit-microsegmentation-posture``
     - Audit the microsegmentation posture across resources, policy rules, and agent groups.
   * - ``zms-analyze-policy-rules``
     - Walk the active policy rules and flag default-allow / overly-broad CIDRs.
   * - ``zms-assess-workload-protection``
     - Surface unprotected workloads (resources without applicable policy rules).
   * - ``zms-review-tag-classification``
     - Audit the tag-namespace hierarchy and surface unclassified resources.
   * - ``zms-troubleshoot-agent-deployment``
     - Diagnose ZMS agent enrollment and connection issues.

Z-Insights — Analytics (4 skills)
---------------------------------

.. list-table::
   :header-rows: 1
   :widths: 35 65

   * - Skill
     - What it does
   * - ``zins-investigate-security-incident``
     - Walk a security incident across firewall, threats, and cyber-incident streams.
   * - ``zins-audit-shadow-it``
     - Surface unsanctioned applications discovered by Z-Insights with risk scoring.
   * - ``zins-analyze-web-traffic``
     - Break down web traffic by protocol, location, and content category.
   * - ``zins-assess-network-security``
     - Score the tenant against firewall posture and surface high-risk gaps.

EASM — Attack Surface (1 skill)
-------------------------------

.. list-table::
   :header-rows: 1
   :widths: 35 65

   * - Skill
     - What it does
   * - ``easm-review-attack-surface``
     - Review external attack surface findings, lookalike domains, and surface critical exposures.

ZCC — Client Connector (1 skill)
--------------------------------

.. list-table::
   :header-rows: 1
   :widths: 35 65

   * - Skill
     - What it does
   * - ``zcc-generate-logout-otp``
     - Generate a logout OTP for offboarding a ZCC-enrolled device.

Cross-product (1 skill)
-----------------------

.. list-table::
   :header-rows: 1
   :widths: 35 65

   * - Skill
     - What it does
   * - ``cross-product-troubleshoot-user-connectivity``
     - End-to-end user connectivity troubleshooting that combines ZCC (device), ZDX (experience), ZPA (private apps), and ZIA (internet) data into a single root-cause analysis.

Skill chaining
--------------

Some skills are deliberately small and intended to **chain** — the parent skill recognizes when a sub-step needs work, and the agent loads the matching helper skill. The most-used chains today:

- ``zia-look-up-rule-targets`` — chained from every ZIA rule-creation skill to resolve user / group / location names to IDs.
- ``zia-look-up-cloud-app-name`` — chained from SSL Inspection / Web DLP / Cloud App Control / File Type Control rule creation to resolve friendly app names to canonical enums.
- ``zia-manage-time-interval`` — chained when a rule needs a recurring schedule.

Skill frontmatter constraints
-----------------------------

The Anthropic skill spec enforces a hard ceiling on the YAML frontmatter ``description`` field of **1024 characters**. Skills exceeding this are rejected by the Claude skill uploader with the error ``field 'description' in SKILL.md must be at most 1024 characters``. When you need more keywords than 1024 characters can carry, the right move is to **split into two chained skills** instead of cramming everything into one description.

How to invoke a skill
---------------------

In any MCP client that supports the skill spec (Claude Desktop, Claude Code, Cursor, Gemini CLI, Kiro IDE), the skill description doubles as the matcher. You don't invoke a skill by name — you describe the task and the matching skill activates.

Examples:

- *"Block ChatGPT for everyone outside the engineering group"* → activates ``zia-create-cloud-app-control-rule`` (which chains to ``zia-look-up-cloud-app-name`` for the canonical enum).
- *"Why is the SAP app slow for users in Frankfurt?"* → activates ``zdx-troubleshoot-user-experience`` (and chains to ``zdx-diagnose-deeptrace`` if the data requires it).
- *"Onboard a new HR app over ZPA"* → activates ``zpa-application_segment-onboard``.

Where skills live
-----------------

The canonical source of every skill is the ``skills/`` directory in the repository: `github.com/zscaler/zscaler-mcp-server/tree/master/skills <https://github.com/zscaler/zscaler-mcp-server/tree/master/skills>`_. The integration plugins (``claude-code-plugin``, ``cursor-plugin``, ``gemini-extension``, ``kiro/``) reference these files directly — there is no separate per-client copy.

See also
--------

- :doc:`../toolsets/index` — the toolset grouping system that scopes which tools are loaded
- :doc:`../tools/index` — the underlying tool catalog
- :ref:`platform-integrations` — how skills are wired into each MCP client
