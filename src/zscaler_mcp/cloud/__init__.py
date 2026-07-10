"""Cloud-platform integration helpers (GCP Secret Manager, …).

Mirrors v1's ``zscaler_mcp/cloud/`` package. Optional, opt-in: nothing here runs
unless the matching env flag is set, so the dependency footprint stays light for
the common stdio / local case.
"""

from zscaler_mcp.cloud.gcp_secrets import is_enabled, load_secrets

__all__ = ["is_enabled", "load_secrets"]
