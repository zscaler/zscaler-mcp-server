---
id: authentication
title: Authentication
sidebar_label: Authentication
sidebar_position: 3
---

# Authentication

The Zscaler MCP Server uses **OneAPI authentication exclusively**. A single set of ZIdentity credentials authenticates the server to every Zscaler product.

## Create an API client in Zidentity

1. Sign in to the [Zidentity console](https://help.zscaler.com/zidentity/about-api-clients) for your tenant.
2. Navigate to **Integration → API Clients**.
3. Click **Add API Client**.
4. Give the client a descriptive name (e.g. `mcp-server-prod`).
5. Assign the **roles** the MCP server needs for the services you intend to use. (Read-only roles are sufficient for the default read-only mode.)
6. Save and copy the generated **Client ID** and **Client Secret**.

:::tip Where do I find my vanity domain?
Your Zidentity vanity domain is the prefix of your sign-in URL. If your console is at `https://acme.zidentity.net`, your vanity domain is `acme`.
:::

## Configure the credentials

Create a `.env` file in your project root:

```env
ZSCALER_CLIENT_ID=your_client_id
ZSCALER_CLIENT_SECRET=your_client_secret
ZSCALER_VANITY_DOMAIN=your_vanity_domain
ZSCALER_CUSTOMER_ID=your_customer_id     # ZPA only
```

For the `beta` tenant:

```env
ZSCALER_CLOUD=beta
```

## OneAPI authentication parameters

| Argument | Description | Environment variable |
|---|---|---|
| `clientId` | Zscaler API client ID | `ZSCALER_CLIENT_ID` |
| `clientSecret` | API client secret (OAuth client_credentials) | `ZSCALER_CLIENT_SECRET` |
| `privateKey` | PEM-encoded private key (JWT-based OneAPI auth, alternative to client_secret) | `ZSCALER_PRIVATE_KEY` |
| `vanityDomain` | Your organization's Zidentity vanity domain (e.g. `acme`) | `ZSCALER_VANITY_DOMAIN` |
| `cloud` | Zidentity cloud (e.g. `beta`) | `ZSCALER_CLOUD` |
| `customerId` | ZPA customer/tenant ID — required only for ZPA tools | `ZSCALER_CUSTOMER_ID` |

## JWT-based authentication

For environments that prefer JWT (private-key) auth over client_secret, set `ZSCALER_PRIVATE_KEY` to the PEM-encoded private key registered in Zidentity:

```env
ZSCALER_CLIENT_ID=your_client_id
ZSCALER_PRIVATE_KEY=-----BEGIN RSA PRIVATE KEY-----...
ZSCALER_VANITY_DOMAIN=your_vanity_domain
```

You can pass a path to a PEM file using your shell:

```bash
export ZSCALER_PRIVATE_KEY="$(cat /path/to/private_key.pem)"
```

## Entitlements

Your OneAPI client only sees products it's entitled to. The MCP server applies an **OneAPI entitlement filter** at startup that silently drops toolsets for products the credentials cannot call. If your client is only entitled to ZIA + ZPA, every `zdx_*` / `zcc_*` / `zid_*` / `zeasm_*` / `zins_*` / `zms_*` toolset is filtered out — even with `--toolsets all`.

See the [Toolsets guide](../guides/toolsets) for details on the entitlement filter.

## MCP client authentication (HTTP transports)

The credentials above authenticate the MCP server **to Zscaler APIs**. They are separate from the credentials clients use to authenticate **to the MCP server itself** when running over HTTP. See [MCP client auth](../security/mcp-client-auth) for the four supported modes (`api-key`, `jwt`, `zscaler`, `OIDCProxy`).
