# Kiro Power Integration

The Zscaler MCP Server is available as a **Kiro Power**, providing AI-assisted management of the Zscaler Zero Trust Exchange platform directly within the [Kiro IDE](https://kiro.dev).

## What's Included

| Component | Location | Purpose |
|-----------|----------|---------|
| Power manifest | `integrations/kiro/POWER.md` | Power metadata, tool reference, workflows, and best practices |
| MCP config | `integrations/kiro/mcp.json` | MCP server connection configuration |
| Steering files | `integrations/kiro/steering/` | 9 service-specific context files for on-demand loading |

### Steering Files

Unlike skills (which are guided workflows), Kiro uses **steering files** — service-specific knowledge documents that the AI loads on demand based on your request:

| Steering File | Service | Tools |
|---------------|---------|-------|
| `zpa.md` | ZPA (Private Access) | 59 — app segments, access/forwarding/timeout/isolation policies, connectors, PRA |
| `zia.md` | ZIA (Internet Access) | 76 — cloud firewall, URL filtering, SSL inspection, DLP, locations, sandbox |
| `zdx.md` | ZDX (Digital Experience) | 18 — app scores, device health, alerts, deep traces (read-only) |
| `z-insights.md` | Z-Insights (Analytics) | 16 — web traffic, cyber incidents, shadow IT, firewall analytics (read-only) |
| `zcc.md` | ZCC (Client Connector) | 4 — device enrollment, forwarding profiles (read-only) |
| `ztw.md` | ZTW (Workload Segmentation) | 19 — IP groups, network services, cloud accounts |
| `easm.md` | EASM (Attack Surface) | 7 — findings, lookalike domains, scan evidence (read-only) |
| `zidentity.md` | ZIdentity | 10 — users, groups, identity management (read-only) |
| `cross-product.md` | Cross-product | ZCC + ZDX + ZPA + ZIA correlation workflow |

## Installation

1. Open [Kiro IDE](https://kiro.dev)
2. Go to the **Powers** panel → **Add Custom Power**
3. Select **Local Directory** or provide the GitHub URL
4. Point to `integrations/kiro/`

For official listing in the Kiro Powers marketplace, submit via https://kiro.dev/powers/

## Prerequisites

- [Kiro IDE](https://kiro.dev) installed
- [uv](https://docs.astral.sh/uv/) installed (for `uvx` method) or Docker
- Zscaler OneAPI credentials configured in `.env`

## Configuration

The MCP server is configured via `integrations/kiro/mcp.json`:

```json
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
```

### Alternative: Docker

```json
{
  "mcpServers": {
    "zscaler": {
      "command": "docker",
      "args": [
        "run", "-i", "--rm",
        "--env-file", "/path/to/your/.env",
        "quay.io/zscaler/zscaler-mcp-server:latest"
      ]
    }
  }
}
```

## Common Workflows

The `POWER.md` includes detailed workflows for:

- **Application onboarding** (ZPA) — connector group → server group → segment group → app segment → access policy
- **Location onboarding** (ZIA) — static IP → VPN credential → location → activate
- **User troubleshooting** (Cross-product) — ZCC device → ZDX health → ZPA/ZIA policies
- **Security investigation** (Z-Insights) — incidents → locations → timeline → threat breakdown
- **Attack surface review** (EASM) — findings → details → lookalike domains

## Verification

After installation, verify by asking Kiro:

> "What Zscaler tools are available?"

or

> "List my ZPA application segments"

## Resources

- [Main README](../../README.md)
- [Supported Tools Reference](../../docs/guides/supported-tools.md)
- [Authentication & Deployment Guide](../../docs/deployment/authentication-and-deployment.md)
- [Troubleshooting](../../docs/guides/TROUBLESHOOTING.md)
