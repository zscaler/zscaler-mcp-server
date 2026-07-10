"""ZCell (Zscaler Cellular) tools (v2). Service code: zcell.

Read-only surface over the Zscaler Cellular OneAPI. Tools are grouped into nine
toolsets that mirror the Cellular API's own categories (Anomaly Policy, Sim
Location Groups, Sim Analytics, Customer Region Handling, Audit Data Handling,
Network Events, Sim Handling, Tag Handling, Customer Data Handling).

ZCell is scoped to a dedicated customer id (``zcellCustomerId``) that is
independent from ZPA's ``customerId``. The SDK resolves it from the
``ZCELL_CUSTOMER_ID`` environment variable (or the client config), so tools do
not carry a per-call customer-id parameter — it is injected by the client
factory (see ``zscaler_mcp.client.get_zscaler_client``).
"""
