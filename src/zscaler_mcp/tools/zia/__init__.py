"""ZIA (Zscaler Internet Access) tools (v2).

Each module self-registers its tools via the ``@tool`` decorator at import time
(DESIGN.md §6); there is no central catalog. ZIA SDK objects expose ``as_dict()``.

v1 multiplexed ``*_manager`` tools (sandbox, dlp dictionary/engine, user
departments/groups/users) are split into explicit ``list`` / ``get`` tools here to
honour the Zero-Trust "one tool = one explicit action" invariant.

ZIA writes are staged until activation — every create/update/delete tool's
docstring reminds the agent to call ``zia_activate_configuration`` afterwards.
"""
