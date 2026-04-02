# GCP Secret Manager Integration

The Zscaler MCP Server Docker image includes built-in support for loading
credentials from [GCP Secret Manager](https://cloud.google.com/secret-manager)
at container startup. When enabled, the server fetches Zscaler API credentials
from Secret Manager and injects them as environment variables before
initializing — no wrapper scripts or container modifications required.

## Overview

```text
GCP Secret Manager                         Container (Cloud Run / GKE)
──────────────────                         ─────────────────────────────
zscaler-client-id      ──┐
zscaler-client-secret  ──┤   startup     ┌─────────────────────────────┐
zscaler-vanity-domain  ──┼──────────────▶│  env vars set automatically │
zscaler-customer-id    ──┤               │  then: zscaler-mcp starts   │
zscaler-cloud          ──┘               └─────────────────────────────┘
```

The loader is activated by setting a single environment variable:

```bash
ZSCALER_MCP_GCP_SECRET_MANAGER=true
```

## How It Works

1. Container starts and the `zscaler-mcp` process begins
2. Before initializing the SDK client, the server checks
   `ZSCALER_MCP_GCP_SECRET_MANAGER`
3. If `true`, it uses the `google-cloud-secret-manager` SDK to fetch each
   credential from Secret Manager using [Application Default Credentials](https://cloud.google.com/docs/authentication/application-default-credentials)
4. Fetched values are set as environment variables
5. The MCP server then initializes normally

### Naming Convention

Environment variable names are converted to Secret Manager IDs by
lowercasing and replacing underscores with hyphens:

| Environment Variable | Secret Manager ID |
|---------------------|-------------------|
| `ZSCALER_CLIENT_ID` | `zscaler-client-id` |
| `ZSCALER_CLIENT_SECRET` | `zscaler-client-secret` |
| `ZSCALER_VANITY_DOMAIN` | `zscaler-vanity-domain` |
| `ZSCALER_CUSTOMER_ID` | `zscaler-customer-id` |
| `ZSCALER_CLOUD` | `zscaler-cloud` |
| `ZSCALER_MCP_WRITE_ENABLED` | `zscaler-mcp-write-enabled` |
| `ZSCALER_MCP_WRITE_TOOLS` | `zscaler-mcp-write-tools` |

Secrets that don't exist are silently skipped. Only `ZSCALER_CLIENT_ID` and
`ZSCALER_CLIENT_SECRET` are required — if missing from both Secret Manager
and the environment, the server exits with an error.

---

## Setup

### Step 1: Create Secrets

Store each credential as an individual secret in your GCP project:

```bash
PROJECT_ID="your-gcp-project"

echo -n "your-client-id" | \
  gcloud secrets create zscaler-client-id \
    --data-file=- --replication-policy=automatic --project=$PROJECT_ID

echo -n "your-client-secret" | \
  gcloud secrets create zscaler-client-secret \
    --data-file=- --replication-policy=automatic --project=$PROJECT_ID

echo -n "your-vanity-domain" | \
  gcloud secrets create zscaler-vanity-domain \
    --data-file=- --replication-policy=automatic --project=$PROJECT_ID

echo -n "your-customer-id" | \
  gcloud secrets create zscaler-customer-id \
    --data-file=- --replication-policy=automatic --project=$PROJECT_ID

echo -n "production" | \
  gcloud secrets create zscaler-cloud \
    --data-file=- --replication-policy=automatic --project=$PROJECT_ID
```

### Step 2: Grant IAM Access

Grant the service account running the container access to the secrets:

```bash
# For Cloud Run (default compute service account)
PROJECT_NUMBER=$(gcloud projects describe $PROJECT_ID --format="value(projectNumber)")
SA_EMAIL="${PROJECT_NUMBER}-compute@developer.gserviceaccount.com"

# For GKE (your workload identity service account)
# SA_EMAIL="your-sa@your-project.iam.gserviceaccount.com"

for SECRET in zscaler-client-id zscaler-client-secret zscaler-vanity-domain \
              zscaler-customer-id zscaler-cloud; do
  gcloud secrets add-iam-policy-binding $SECRET \
    --member="serviceAccount:$SA_EMAIL" \
    --role="roles/secretmanager.secretAccessor" \
    --project=$PROJECT_ID --quiet
done
```

### Step 3: Deploy

Pull the image and deploy with Secret Manager enabled. The only
environment variables you need to pass directly are the non-sensitive
configuration — all Zscaler API credentials come from Secret Manager.

#### Cloud Run

```bash
gcloud run deploy zscaler-mcp-server \
  --image=marketplace.gcr.io/zscaler/zscaler-mcp-server:latest \
  --region=us-central1 \
  --platform=managed \
  --port=8000 \
  --args="--transport,streamable-http,--host,0.0.0.0,--port,8000" \
  --set-env-vars="\
ZSCALER_MCP_GCP_SECRET_MANAGER=true,\
GCP_PROJECT_ID=$PROJECT_ID,\
ZSCALER_MCP_ALLOW_HTTP=true,\
ZSCALER_MCP_DISABLE_HOST_VALIDATION=true" \
  --memory=512Mi \
  --allow-unauthenticated
```

#### GKE

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: zscaler-mcp-server
spec:
  replicas: 1
  selector:
    matchLabels:
      app: zscaler-mcp-server
  template:
    metadata:
      labels:
        app: zscaler-mcp-server
    spec:
      serviceAccountName: zscaler-mcp-sa  # must have secretAccessor role
      containers:
      - name: zscaler-mcp
        image: marketplace.gcr.io/zscaler/zscaler-mcp-server:latest
        args: ["--transport", "streamable-http", "--host", "0.0.0.0", "--port", "8000"]
        ports:
        - containerPort: 8000
        env:
        - name: ZSCALER_MCP_GCP_SECRET_MANAGER
          value: "true"
        - name: GCP_PROJECT_ID
          value: "your-gcp-project"
        - name: ZSCALER_MCP_ALLOW_HTTP
          value: "true"
```

---

## Authentication

The MCP server supports multiple authentication modes for client connections.
Choose the mode that fits your environment — Secret Manager handles the
Zscaler API credentials, while these settings control who can connect to
the MCP server itself.

### Zscaler Auth (Recommended)

Uses your existing Zscaler OneAPI credentials — clients authenticate with
`Authorization: Basic base64(client_id:client_secret)`. No external IdP setup
required:

```bash
ZSCALER_MCP_AUTH_ENABLED=true
ZSCALER_MCP_AUTH_MODE=zscaler
```

The server validates credentials against Zscaler's `/oauth2/v1/token` endpoint
and caches the result for the token's lifetime (~1 hour).

### No Authentication (Testing Only)

```bash
ZSCALER_MCP_AUTH_ENABLED=false
```

### JWT Authentication

Validate client JWTs against any OIDC-compliant provider (Auth0, Okta,
Azure AD, Google IAP, etc.):

```bash
ZSCALER_MCP_AUTH_ENABLED=true
ZSCALER_MCP_AUTH_MODE=jwt
ZSCALER_MCP_AUTH_JWKS_URI=https://your-provider/.well-known/jwks.json
ZSCALER_MCP_AUTH_ISSUER=https://your-provider/
ZSCALER_MCP_AUTH_AUDIENCE=zscaler-mcp-server
```

### API Key Authentication

Simple shared-secret authentication:

```bash
ZSCALER_MCP_AUTH_ENABLED=true
ZSCALER_MCP_AUTH_MODE=api-key
ZSCALER_MCP_AUTH_API_KEY=your-secret-key
```

You can also store the API key in Secret Manager by creating a secret named
`zscaler-mcp-auth-api-key`.

### Cloud Run IAM

When deploying to Cloud Run without `--allow-unauthenticated`, Cloud Run
enforces IAM-based authentication at the infrastructure level. In this case
you may disable MCP-level auth:

```bash
ZSCALER_MCP_AUTH_ENABLED=false
```

---

## Alternative: Cloud Run Native `--set-secrets`

Cloud Run can mount Secret Manager values directly as environment variables
without the runtime loader. This is simpler but only works on Cloud Run:

```bash
gcloud run deploy zscaler-mcp-server \
  --image=marketplace.gcr.io/zscaler/zscaler-mcp-server:latest \
  --set-secrets="\
ZSCALER_CLIENT_ID=zscaler-client-id:latest,\
ZSCALER_CLIENT_SECRET=zscaler-client-secret:latest,\
ZSCALER_VANITY_DOMAIN=zscaler-vanity-domain:latest,\
ZSCALER_CUSTOMER_ID=zscaler-customer-id:latest,\
ZSCALER_CLOUD=zscaler-cloud:latest" \
  --set-env-vars="ZSCALER_MCP_ALLOW_HTTP=true,ZSCALER_MCP_DISABLE_HOST_VALIDATION=true" \
  --args="--transport,streamable-http,--host,0.0.0.0,--port,8000" \
  --port=8000 --region=us-central1 --platform=managed
```

With this approach, `ZSCALER_MCP_GCP_SECRET_MANAGER` is not needed — Cloud
Run injects the values before the container starts.

| | Runtime Loader (`ZSCALER_MCP_GCP_SECRET_MANAGER`) | Cloud Run `--set-secrets` |
|--|--|--|
| Works on Cloud Run | Yes | Yes |
| Works on GKE | Yes | No |
| Works on Compute Engine | Yes | No |
| Container changes needed | None (built into image) | None |
| Requires GCP SDK in image | Yes (included) | No |

---

## Without Secret Manager

If you prefer to pass credentials directly as environment variables (not
recommended for production):

```bash
gcloud run deploy zscaler-mcp-server \
  --image=marketplace.gcr.io/zscaler/zscaler-mcp-server:latest \
  --set-env-vars="\
ZSCALER_CLIENT_ID=your-client-id,\
ZSCALER_CLIENT_SECRET=your-client-secret,\
ZSCALER_VANITY_DOMAIN=your-domain,\
ZSCALER_CUSTOMER_ID=your-customer-id,\
ZSCALER_CLOUD=production,\
ZSCALER_MCP_ALLOW_HTTP=true,\
ZSCALER_MCP_DISABLE_HOST_VALIDATION=true" \
  --args="--transport,streamable-http,--host,0.0.0.0,--port,8000" \
  --port=8000 --region=us-central1 --platform=managed
```

> **Warning**: Credentials passed as `--set-env-vars` are visible in the
> Cloud Console. Use Secret Manager for production deployments.

---

## Credential Rotation

### With Runtime Loader

```bash
# Update the secret value
echo -n "new-client-secret" | \
  gcloud secrets versions add zscaler-client-secret --data-file=-

# Restart the service to pick up the new version
gcloud run services update zscaler-mcp-server --region=us-central1
```

### With Cloud Run `--set-secrets`

```bash
# Update the secret value (same as above)
echo -n "new-client-secret" | \
  gcloud secrets versions add zscaler-client-secret --data-file=-

# Redeploy to mount the new version
gcloud run deploy zscaler-mcp-server \
  --image=marketplace.gcr.io/zscaler/zscaler-mcp-server:latest \
  --set-secrets="ZSCALER_CLIENT_SECRET=zscaler-client-secret:latest" \
  --region=us-central1
```

---

## Connecting Clients

Once the server is deployed, configure your MCP client to connect. The default auth mode is `zscaler`, which uses your Zscaler OneAPI credentials as Basic auth.

Generate the Base64 credential string:

```bash
echo -n "your-client-id:your-client-secret" | base64
```

### Claude Desktop

```json
{
  "mcpServers": {
    "zscaler-mcp-server": {
      "command": "npx",
      "args": [
        "-y", "mcp-remote",
        "https://your-service-url.run.app/mcp",
        "--header",
        "Authorization: Basic <base64(client_id:client_secret)>"
      ]
    }
  }
}
```

### Cursor

```json
{
  "mcpServers": {
    "zscaler-mcp-server": {
      "url": "https://your-service-url.run.app/mcp",
      "headers": {
        "Authorization": "Basic <base64(client_id:client_secret)>"
      }
    }
  }
}
```

> **Tip**: The `scripts/deploy-gcp.py` script generates these configs automatically, including the Base64-encoded credentials.

Omit the `Authorization` header if authentication is disabled.

---

## Troubleshooting

### "google-cloud-secret-manager is not installed"

The GCP extras are included in the marketplace image. If you're building
a custom image, install with:

```bash
pip install zscaler-mcp[gcp]
```

### "Permission denied accessing secret"

Grant the service account access:

```bash
gcloud secrets add-iam-policy-binding zscaler-client-secret \
  --member="serviceAccount:YOUR_SA_EMAIL" \
  --role="roles/secretmanager.secretAccessor"
```

### "Required credentials not found"

At minimum, `zscaler-client-id` and `zscaler-client-secret` must exist in
Secret Manager (or be passed as environment variables). Verify:

```bash
gcloud secrets versions access latest --secret=zscaler-client-id
gcloud secrets versions access latest --secret=zscaler-client-secret
```

### Viewing Logs

```bash
# Cloud Run
gcloud run services logs read zscaler-mcp-server --region=us-central1 --limit=50

# GKE
kubectl logs deployment/zscaler-mcp-server
```

Look for lines like:

```text
Loading credentials from GCP Secret Manager (project: your-project)
  ZSCALER_CLIENT_ID = ipm2ol7od...
  ZSCALER_CLIENT_SECRET = ********
Loaded 5 credential(s) from GCP Secret Manager
```
