"""ZTW (Zscaler Cloud & Branch Connector) tools (v2).

Each module self-registers its tools via the ``@tool`` decorator at import time
(DESIGN.md §6); there is no central catalog. ZTW SDK objects expose ``as_dict()``
like the other write-capable services, except ``account_details`` which already
returns plain dicts (handled in that module).
"""
