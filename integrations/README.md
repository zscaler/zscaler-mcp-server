# Platform Integrations

This directory contains official integrations for the Zscaler MCP Server with various AI development platforms.

## Available Integrations

### [Kiro Power](./kiro/)

**AWS Kiro IDE Integration**

The Zscaler Kiro Power enables AI-assisted management of the Zscaler Zero Trust Exchange platform directly within the [Kiro IDE](https://kiro.dev).

**Features:**
- 110+ read-only tools and 85+ write tools across 7 Zscaler services
- Service-specific steering files for ZPA, ZIA, ZDX, ZCC, ZTW, EASM, and ZIdentity
- Natural language queries for security configuration management

**Installation:**
1. Open Kiro IDE
2. Go to Powers panel → Add Custom Power
3. Select "Local Directory" or provide the GitHub URL
4. Point to `integrations/kiro/`

**Submission:**
For official listing in the Kiro Powers marketplace, submit via https://kiro.dev/powers/

---

## Adding New Integrations

When adding a new platform integration:

1. Create a new directory with the platform name
2. Include all necessary configuration files
3. Add a README.md with setup instructions
4. Update this file with the new integration details
