.. _guide-jmespath-filtering:

JMESPath Filtering on List Tools
================================

Every ``*_list_*`` tool across every service accepts an optional ``query`` parameter that takes a `JMESPath <https://jmespath.org/>`_ expression. The expression is applied **client-side, after** the API call returns — so it filters and projects the results without changing what the Zscaler API sees.

The use case
------------

Tenants with thousands of locations, hundreds of policy rules, or large user populations return paginated results that an agent has to walk. JMESPath lets the operator (or the agent acting on their behalf) narrow the result set before it lands in the model's context.

A concrete example. Without filtering, listing every ZIA location returns the full page:

.. code-block:: text

   zia_list_locations(page=1, page_size=100)
   → [{id: ..., name: "HQ", country: "USA", ...}, {id: ..., name: "Frankfurt", ...}, …]

With a JMESPath expression:

.. code-block:: text

   zia_list_locations(query="[?country=='USA'].{id: id, name: name}")
   → [{id: 123, name: "HQ"}, {id: 124, name: "Boston"}, …]

The agent gets exactly the fields it needs, scoped to exactly the rows that match.

Expression syntax
-----------------

Standard JMESPath syntax applies. Field names use **snake_case** because the Zscaler SDK converts camelCase API responses to snake_case before the expression runs.

Common patterns:

.. list-table::
   :header-rows: 1
   :widths: 30 35 35

   * - Goal
     - Expression
     - Service example
   * - Filter rows
     - ``[?field=='value']``
     - ``zia_list_locations(query="[?country=='USA']")``
   * - Project fields
     - ``[*].{a: a, b: b}``
     - ``zpa_list_application_segments(query="[*].{id: id, name: name}")``
   * - Filter + project
     - ``[?enabled==`true`].{name: name, id: id}``
     - ``zpa_list_segment_groups(query="[?enabled==\`true\`].{name: name, id: id}")``
   * - Count rows
     - ``length(@)``
     - ``zia_list_url_filtering_rules(query="length(@)")``
   * - Contains substring
     - ``[?contains(name, 'prod')]``
     - ``zpa_list_application_segments(query="[?contains(name, 'prod')]")``
   * - First match
     - ``[?name=='HQ'] | [0]``
     - ``zia_list_locations(query="[?name=='HQ'] | [0]")``

.. note::

   Booleans in JMESPath are backtick-quoted — write ``[?enabled==\`true\`]`` and ``[?enabled==\`false\`]``. That's a JMESPath syntax quirk, not a mistake.

Service-specific examples
-------------------------

.. list-table::
   :header-rows: 1
   :widths: 12 88

   * - Service
     - Expression
   * - ZIA
     - ``[?name=='HQ'].{name: name, id: id}`` — find location named "HQ", project name + id
   * - ZPA
     - ``[?enabled==\`true\`]`` — filter to enabled application segments
   * - ZDX
     - ``[?platform=='Windows'].{user_name: user_name}`` — Windows devices only, just usernames
   * - ZCC
     - ``[*].{name: name, os_type: os_type}`` — name + OS for all devices
   * - ZMS
     - ``nodes[?cloud_provider=='AWS']`` — AWS workloads only (note the ``nodes`` envelope)
   * - EASM
     - ``results[?severity=='critical']`` — filter findings to critical severity

For ZMS specifically, the GraphQL response is wrapped in a ``nodes[]`` + ``page_info`` envelope. The JMESPath expression starts inside that envelope, so use ``nodes[?...]`` instead of ``[?...]``.

How the agent should use this
-----------------------------

The user is asking a **business question**. The JMESPath plumbing is internal optimization. Never narrate it.

**Plain-language answers only.** Translate tool output into the answer the admin actually wanted.

- User: *"How many ZIA DNS rules exist?"*

  Agent: *"There are 19 ZIA DNS firewall rules in the tenant."*

  ❌ Do **not** say *"The JMESPath ``length(@)`` returned 19."*

- User: *"List the names of my SSL inspection rules"*

  Agent lists the names directly.

  ❌ Do not mention *"I projected ``[*].name``."*

The ``query`` parameter is a tool, not a presentation device.

Empty results are authoritative
-------------------------------

If a filter returns an empty list, **that is the answer**. The agent should not fan out retries with different filters, broader projections, or larger page sizes "to double-check". Each retry costs a round trip and adds zero information.

- ❌ Five calls in sequence: ``search="DataCenter Switches SSH"`` → empty → ``query="[?contains(name,'DataCenter') || contains(name,'SSH')]"`` → ``query="[*].{id,name}", page_size=200`` → unfiltered list → "let me drop the projection in case it's too aggressive".
- ✅ One call: ``search="DataCenter Switches SSH"`` → empty → *"I can't find an application segment named 'DataCenter Switches SSH'. Want me to use a different name?"*

This pairs naturally with the ``search`` parameter (server-side substring match on the ``name`` field). The two are complementary, not redundant.

Invalid expressions
-------------------

A malformed JMESPath expression returns a structured error response instead of crashing:

.. code-block:: text

   zia_list_locations(query="not a valid expression")
   → [{"error": "Invalid JMESPath expression: ..."}]

The agent should treat this like any other tool error — surface a plain-language version to the user and stop, don't retry.

Implementation
--------------

The shared helper lives at ``zscaler_mcp/common/jmespath_utils.py``:

- ``apply_jmespath(data, expression)`` — used by non-ZMS list tools (where the API result is a list of dicts).
- ZMS list tools use a dedicated wrapper in ``zscaler_mcp/tools/zms/__init__.py`` that preserves the ``nodes[]`` + ``page_info`` envelope so expressions can target either the envelope or the data.

When ``query`` is ``None``, results pass through unchanged — full backward compatibility with callers that don't use the parameter.

Return types
------------

JMESPath expressions can produce scalars (``length(@)``), differently-shaped lists (``[*].name``), or filtered subsets of the original shape. Tools that accept ``query`` declare a permissive return type (``Any``) so the MCP / Pydantic output validator accepts whichever shape the expression produces.

If you write a tool that accepts ``query``, never declare its return type as ``List[dict]`` / ``List[str]`` — that causes the validator to reject expressions like ``length(@)`` (which returns an int).

See also
--------

- :doc:`../tools/index` — the full list of tools that accept ``query``.
- `JMESPath documentation <https://jmespath.org/>`_ — the upstream syntax reference.
- :doc:`audit-logging` — the audit log captures the ``query`` value (redacted if it contains sensitive substrings).
