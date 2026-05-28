# Zscaler MCP Server on AWS EC2

Deploy the [Zscaler MCP Server](https://github.com/zscaler/zscaler-mcp-server) on a single **Amazon Linux 2023 EC2 instance**, fronted by an Application Load Balancer with TLS termination. The server is installed straight from PyPI (`pip install zscaler-mcp-server`) — **no container runtime, no Docker, no Kubernetes** — and managed by `systemd`. Same end-result topology as the sibling [`../ecs-fargate/`](../ecs-fargate/) deployment, just on a plain VM. Same Python orchestrator UX, same CloudFormation pattern, same 7-client auto-config.

> **When to use this deployment**
> You want the lightest-weight self-hosted option: no container hosting service to learn, no Kubernetes, full SSH/SSM access to the box, and a server you can debug with familiar tools (`journalctl`, `top`, `python3`). The trade-off is that scaling is manual — bump the instance type, or migrate to ECS-Fargate/EKS when you need horizontal scaling.

---

## Topology

```text
                            ┌─────────────────────────────────────────┐
   User / MCP client ───►   │ Application Load Balancer (TLS @ 443)   │
                            └────────────────┬────────────────────────┘
                                             │ HTTP :8000
                                             ▼
                            ┌─────────────────────────────────────────┐
                            │ EC2 instance (Amazon Linux 2023)        │
                            │   • systemd unit: zscaler-mcp.service   │
                            │   • venv at /opt/zscaler-mcp/venv       │
                            │   • Runs as the `zscaler-mcp` user      │
                            │   • Creds fetched from Secrets Manager  │
                            │     by the launcher on boot             │
                            └────────────────┬────────────────────────┘
                                             │ HTTPS
                                             ▼
                                       Zscaler OneAPI
```

What the stack creates:

- **VPC** (optional): 2 public + 2 private subnets across 2 AZs, IGW, single NAT gateway. Or attach to an existing VPC.
- **ALB**: HTTPS listener (with optional ACM TLS), HTTP→HTTPS redirect, target group registered with the EC2 instance.
- **ACM cert + Route53 alias** (AcmManaged mode): full DNS-validated certificate, all in the same stack.
- **EC2 instance** (default `t3.small`, 16 GiB encrypted gp3 root): cloud-init installs Python, creates a venv, `pip install zscaler-mcp-server`, writes a launcher + systemd unit, and starts the service.
- **IAM instance profile**: scoped `secretsmanager:GetSecretValue` on the specific secret + SSM Managed Instance Core + CloudWatch Agent.
- **CloudWatch Agent**: forwards three streams to a single dedicated log group (`/aws/ec2/<prefix>`): `bootstrap-<instance-id>` (cloud-init / pip-install output from `/var/log/zscaler-mcp-bootstrap.log`), `mcp-server-<instance-id>` (MCP service stdout/stderr from `/var/log/zscaler-mcp/server.log`, written by a journald → file bridge unit), and `system-<instance-id>` (`/var/log/messages`).
- **Security groups**: ALB SG (80/443 from 0.0.0.0/0); Instance SG (8000 from ALB SG, optional SSH from operator CIDR).
- **Secrets Manager secret** (optional): script creates one from your `.env`, or you point at an existing ARN.

---

## File layout

```text
ec2/
├── README.md                          # this file
├── env.properties                     # config template
├── requirements.txt                   # Python deps (boto3)
├── ec2_mcp_operations.py              # interactive orchestrator
└── cloudformation/
    ├── zscaler-mcp-root.yaml          # root nested stack
    ├── network.yaml                   # VPC + subnets + NAT (CreateNew mode)
    ├── iam.yaml                       # instance role + profile (SSM + CW + SM read)
    ├── secrets.yaml                   # Secrets Manager (CreateNew mode)
    └── instance.yaml                  # EC2 + ALB + listeners + cloud-init bootstrap
```

---

## Prerequisites

- **AWS credentials** with permission to create VPC, EC2, IAM, ELBv2, ACM (if AcmManaged), Route53 (if AcmManaged), Secrets Manager, CloudWatch Logs, SSM, and S3 resources.
- **Python 3.9+** with `boto3` (installed by `requirements.txt`). The `logs` subcommand uses boto3 directly — no AWS CLI required.
- **AWS CLI + Session Manager plugin** only if you want to use `ssh` (the script shells out to `aws ssm start-session`; `ssh` pre-flights both and prints an OS-specific install hint when either is missing):
  ```bash
  # macOS:
  brew install --cask session-manager-plugin
  # Ubuntu/Debian:
  curl "https://s3.amazonaws.com/session-manager-downloads/plugin/latest/ubuntu_64bit/session-manager-plugin.deb" -o sm.deb
  sudo dpkg -i sm.deb
  # Amazon Linux / RHEL:
  sudo dnf install -y https://s3.amazonaws.com/session-manager-downloads/plugin/latest/linux_64bit/session-manager-plugin.rpm
  ```
  > **Why SSM instead of plain SSH?** The instance lives in a *private* subnet (no public IP, no inbound 22 from the internet). SSM gives the same SSH UX without the attack surface — no key files to rotate, no IP allowlists, every session audited in CloudTrail. If you only need to read MCP service logs, skip the plugin entirely and use `python ec2_mcp_operations.py logs --stream mcp -f` (boto3-only, no AWS CLI).

---

## Quick start

```bash
cd integrations/aws/ec2
pip install -r requirements.txt
cp env.properties .env        # then edit .env
python ec2_mcp_operations.py deploy
```

The script walks you through:

1. **Region + stack name + resource prefix**
2. **Credentials** — reuse an existing Secrets Manager secret OR create a new one from your `.env`
3. **VPC** — create a new one OR pick existing VPC + subnets (interactive picker)
4. **TLS** — Route53-validated ACM cert OR existing cert ARN OR plaintext HTTP (demo)
5. **MCP auth mode** — `zscaler`, `jwt`, `api-key`, `oidcproxy`, or `none`
6. **Instance type + SSH access** — t3 family by default; SSM-only access by default (no inbound 22)
7. **Review** of every choice before launching the stack
8. **Deploy** — uploads CFN templates, runs `create-stack`, waits with live status
9. **Configure MCP clients** — picks from any clients detected on your machine

Total runtime is typically **8–15 minutes**, dominated by ALB + ACM provisioning. The instance itself takes ~60–180 seconds after `CREATE_COMPLETE` to finish `pip install` and start the systemd unit — `status` will report `unhealthy` until the bootstrap finishes, then flip to `healthy`.

---

## Commands

| Command | What it does |
|---------|--------------|
| `deploy [--fresh] [--non-interactive] [--skip-client-config] [--env-file PATH]` | Build asset bucket, upload nested templates, launch the root stack, write client configs. **Re-deploys are auto-detected**: when a state file from a prior deploy is found, all saved values (region, stack name, prefix, network mode, credential ARN, TLS mode, auth mode) are reused so CFN runs an in-place update with whatever changed in `.env` (new auth mode, write-tool toggle, new feature flags, etc.). Pass `--fresh` to ignore the state file (e.g. when the prior stack was destroyed via the AWS console). |
| `status` | Show stack status, MCP URL, EC2 state, ALB target health. |
| `logs [-f] [--since N] [--stream {mcp,bootstrap,system,all}]` | Stream the EC2 instance's CloudWatch log group. `--stream mcp` (default) reads the MCP service stdout/stderr (`mcp-server-<instance-id>` stream — what you want to debug a running deploy), `--stream bootstrap` reads cloud-init / pip-install output, `--stream system` reads `/var/log/messages`, `--stream all` interleaves every stream in the group. `-f` keeps polling; `--since` controls how many minutes of history to dump on first read (default 30). Uses boto3 directly — works with AWS CLI v1, v2, or no AWS CLI installed. |
| `ssh` | Pre-flights the AWS CLI + Session Manager plugin and prints an OS-specific install hint if either is missing, then shells out to `aws ssm start-session --target <instance-id>` — no SSH key needed, no inbound 22. The instance is in a private subnet (no public IP), so SSM is the only path in. |
| `destroy [-y] [--stack-name X] [--region Y]` | `cloudformation delete-stack` and wait for completion; deletes the state file. Resilient to missing/partial state. |
| `configure [--env-file PATH]` | Re-write MCP client configs on this machine (no AWS calls). Useful after re-installing a client. |

Flags:

- `--env-file PATH` — load a specific env file (defaults to `.env`/`env.properties` in the script directory).
- `--non-interactive` — never prompt; rely entirely on env vars. Required for CI.
- `--fresh` (deploy only) — ignore any existing state file and treat the run as a first-time deploy. See "Re-deploying" below.
- `--skip-client-config` (deploy only) — don't touch any local MCP client configs.
- `--yes` / `-y` (destroy only) — skip the destroy confirmation prompt.
- `--stack-name X` / `--region Y` (destroy only) — override the stack name / region when no state file is present.
- `-f` / `--follow` (logs only) — keep polling for new events.
- `--since MINUTES` (logs only) — how many minutes of history to dump on first read. Default `30`.
- `--stream {mcp,bootstrap,system,all}` (logs only) — which on-instance log stream to read. Default `mcp` (the MCP service's stdout/stderr — what operators want 95% of the time).

---

## Re-deploying / pushing updates to an existing stack

Re-running `python ec2_mcp_operations.py deploy` against an already-deployed environment **is the intended way to push updates**. The script detects the state file from your prior deploy and:

1. Prints `Found existing deployment (stack=..., region=...). Re-using saved values — CFN will run an in-place update.`
2. Pins the locked dimensions to their saved values: region, stack name, prefix, network mode (CFN cannot change these without a destroy).
3. Forces `CredentialSource=UseExisting` pointing at the saved Secrets Manager ARN — secret stays untouched, no re-prompt for sensitive values. To rotate the secret, update it in Secrets Manager and force a re-deploy of the instance with `systemctl restart zscaler-mcp` (via `python ec2_mcp_operations.py ssh`).
4. Allows soft overrides via `.env` for TLS mode, auth mode, feature flags. Typical update scenarios:
   - Flip `ZSCALER_MCP_AUTH_MODE=jwt` to enable MCP-client auth (the user-data block re-templates the systemd unit on the next instance refresh, OR you `ssh` in and restart manually).
   - Toggle `ZSCALER_MCP_WRITE_ENABLED=true` and `ZSCALER_MCP_WRITE_TOOLS=zia_*` for write tools.
5. Runs `update-stack` on CloudFormation. For env-var-only changes, CFN updates the launch template and rolling-replaces the instance via the AutoScaling group; for IAM / network / TLS changes it computes the appropriate diff.

If the prior stack was destroyed out-of-band, pass `--fresh` to start over.

---

## Inside the instance

**Service unit:** `/etc/systemd/system/zscaler-mcp.service`
- `Type=simple`, restarts on failure, runs as the dedicated `zscaler-mcp` user.
- Calls `/usr/local/bin/zscaler-mcp-launch`, which:
  1. Loads static env from `/etc/zscaler-mcp/static.env`.
  2. Pulls the Zscaler creds out of Secrets Manager (via boto3) into the process env.
  3. `exec`'s `/opt/zscaler-mcp/venv/bin/zscaler-mcp`.
- Standard output/error → `journald` → `/var/log/zscaler-mcp/server.log` (via a small forwarder unit) → CloudWatch Logs.

**Inspecting the live service from inside the instance** (after `ssh`):

```bash
sudo systemctl status zscaler-mcp
sudo journalctl -u zscaler-mcp -f
sudo /opt/zscaler-mcp/venv/bin/zscaler-mcp --version
cat /etc/zscaler-mcp/static.env
```

**Restarting after a configuration change** (e.g. you edited `static.env`):

```bash
sudo systemctl restart zscaler-mcp
```

**Picking up rotated credentials from Secrets Manager**: just restart the service. The launcher re-fetches on every start. No instance redeploy needed.

```bash
sudo systemctl restart zscaler-mcp
```

---

## Credentials — three paths

| Path | When to use | Setup |
|------|-------------|-------|
| **Existing Secrets Manager secret** | Production. Secret lifecycle is managed outside the deploy. | Pre-create the secret as a JSON object with keys `ZSCALER_CLIENT_ID`, `ZSCALER_CLIENT_SECRET`, `ZSCALER_VANITY_DOMAIN`, `ZSCALER_CUSTOMER_ID`, `ZSCALER_CLOUD`. Set `ZSCALER_SECRET_NAME` in `.env`. Script auto-resolves the ARN via `DescribeSecret`. |
| **Script creates a new secret** | Dev / test / quick PoC. Values appear in the CloudFormation parameters during deploy. | Populate the five `ZSCALER_*` env vars in `.env`. Leave `ZSCALER_SECRET_NAME` unset. |
| **Interactive prompts** | First-time exploration. | Skip the `.env` entirely; let the script ask. |

The instance role policy is scoped to **exactly the secret ARN** — no `*` wildcard, no cross-secret access. Rotating Zscaler credentials is a two-step:
1. Update the JSON in Secrets Manager.
2. `sudo systemctl restart zscaler-mcp` on the instance (via `ssh` subcommand).

---

## VPC — existing vs new

| Choice | What gets provisioned | When to use |
|--------|----------------------|-------------|
| **CreateNew** | New `/16` VPC (`10.42.0.0/16` by default), 2 public subnets + 2 private subnets across 2 AZs, IGW, single NAT gateway, route tables. | Fastest path. Single NAT in one AZ is acceptable for single-instance EC2 — the instance lives in one AZ anyway. |
| **UseExisting** | None — you point at an existing VPC + subnet IDs. | Required when the workload must share networking with existing resources. |

When choosing **UseExisting**, the private subnets must already have a route to a NAT gateway (or VPC endpoints for SM + S3 + CloudWatch + EC2 Messages) — the instance bootstrap needs outbound HTTPS to install Python packages from PyPI and to talk to Zscaler OneAPI at runtime.

---

## TLS — three paths

| Choice | What gets provisioned | When to use |
|--------|----------------------|-------------|
| **AcmManaged** | ACM cert + DNS validation CNAME (automatic) + Route53 A-alias pointing your FQDN at the ALB. End-to-end HTTPS. | You own a Route53 hosted zone. |
| **AcmExisting** | The 443 listener attached to the cert ARN you supply. No DNS record is created — you point your CNAME at the ALB DNS name. | DNS lives outside Route53. |
| **None** | ALB listener on port 80, plaintext HTTP. | Demos and quick PoCs only. |

---

## MCP-client authentication

Same five modes as the ECS-Fargate deployment:

| Mode | Client sends | Server validates | Setup |
|------|--------------|------------------|-------|
| `zscaler` (default) | `Authorization: Basic <base64(client_id:client_secret)>` | Zscaler OneAPI `/oauth2/v1/token` (cached) | Zero — uses your OneAPI creds. |
| `jwt` | `Authorization: Bearer <jwt>` | JWKS lookup | Configure JWKS / issuer / audience in `.env`. |
| `api-key` | `X-Api-Key` or `Authorization: Bearer <key>` | String comparison | Set the key in `.env` or let the script generate one. |
| `oidcproxy` | Full OAuth 2.1 with DCR | An IdP you control | Configure `OIDCPROXY_*` env vars. |
| `none` | nothing | nothing | Cluster-internal use only. |

---

## MCP client auto-configuration

After a successful deploy the script detects which of these clients are installed on your machine and offers to wire each one up to the new URL with the right auth header:

| Client | Config file written |
|--------|---------------------|
| Claude Desktop | `~/Library/Application Support/Claude/claude_desktop_config.json` |
| Claude Code (CLI) | `~/.claude.json` |
| Cursor | `~/.cursor/mcp.json` |
| Gemini CLI | `~/.gemini/settings.json` |
| VS Code (MCP) | `~/Library/Application Support/Code/User/mcp.json` |
| Windsurf | `~/.codeium/windsurf/mcp_config.json` |
| GitHub Copilot CLI | `~/Library/Application Support/github-copilot/mcp.json` |

Re-run `configure` whenever you reinstall a client on a fresh machine — loads the URL from the state file, no AWS calls.

---

## State file

`.aws-deploy-state.json` lives in this directory after a successful deploy. It tracks:

- Stack name, region, account, asset bucket, resource prefix
- MCP URL, ALB DNS, log group, secret name
- Instance ID + type + VPC ID
- Auth mode, server name registered into MCP clients
- Configured-client paths (used by `destroy` to optionally clean them up)

Not secret on its own (resource IDs only). Per-developer — `.gitignore` excludes it.

---

## Cost ballpark (us-east-1)

| Component | Approx monthly |
|-----------|---------------:|
| EC2 instance (t3.small, on-demand, 24/7) | ~$15 |
| EBS gp3 root volume (16 GiB) | ~$1.30 |
| Application Load Balancer | ~$22 + LCU |
| NAT gateway (when CreateNew network) | ~$33 + per-GB |
| ACM certificate | $0 |
| Route53 hosted zone | $0.50 (zone) + per-query |
| Secrets Manager secret | $0.40 per secret |
| CloudWatch Logs | $0.50 per GiB ingested + storage |
| **Total (idle, no traffic)** | **~$70–80 / month** |

To bring costs down for a non-prod instance, drop to `t4g.small` (~$12/mo) or use an existing NAT in a shared VPC.

---

## Troubleshooting

**`Health checks failing`** — the bootstrap is still running. Check:
```bash
python ec2_mcp_operations.py ssh
sudo tail -f /var/log/zscaler-mcp-bootstrap.log
```
Typical first-deploy timeline: 30s OS-update → 60s `pip install` → 5s service start → first healthy.

**`Bootstrap log shows pip install failure`** — usually a NAT routing issue. Confirm the private subnet has a route to a NAT gateway (`aws ec2 describe-route-tables`).

**`Secret not found`** — when using `UseExisting`, the script auto-resolves the ARN via `secretsmanager:DescribeSecret`. If your caller can't describe the secret, set `ZSCALER_SECRET_ARN` manually in `.env`.

**Service won't start after credential rotation** — check `journalctl -u zscaler-mcp -n 50`. The most common failure is a JSON key missing from the rotated secret. The launcher exports every JSON key as an env var; missing required keys → `zscaler-mcp` crashes on startup.

**`ssh` says `SessionManagerPlugin is not found`** — the AWS CLI ships separately from the Session Manager plugin and the CLI installer does *not* pull it in. The `ssh` subcommand now pre-flights both binaries and emits an OS-specific install hint, so if you're seeing the raw AWS CLI message you're on an older version of this script — `git pull` and retry. The install command is `brew install --cask session-manager-plugin` on macOS, `sudo dnf install -y https://s3.amazonaws.com/session-manager-downloads/plugin/latest/linux_64bit/session-manager-plugin.rpm` on AL/RHEL, and the `.deb` from `s3.amazonaws.com/session-manager-downloads/plugin/latest/ubuntu_64bit/` on Ubuntu/Debian. The instance lives in a *private* subnet — there is no public IP and plain SSH from your laptop is not a supported topology. If you only need MCP service logs (not a shell), skip the plugin entirely: `python ec2_mcp_operations.py logs --stream mcp -f` reads them straight from CloudWatch with no AWS CLI required.

**`logs --stream mcp` returns no events** — two common causes:
1. **The instance was deployed before the `mcp-server-*` stream was added to the CloudWatch Agent config.** Run `python ec2_mcp_operations.py deploy` to push the updated template (the saved state file is reused, so it runs as an in-place update; the CFN `UserData` change forces CFN to replace the instance and the new stream appears on first boot). To see logs from the *current* instance while you wait, use `--stream bootstrap` (the cloud-init output is always there) or `ssh` in and `sudo journalctl -u zscaler-mcp -f`.
2. **The service genuinely hasn't logged anything yet.** Check `python ec2_mcp_operations.py status` — if the ALB target health is `unhealthy`, bootstrap is still running and the service hasn't started.

---

## Tear-down

```bash
python ec2_mcp_operations.py destroy
```

Deletes the root stack and (transitively):

- EC2 instance + EBS volume
- ALB + target group + listeners
- ACM cert (AcmManaged)
- Route53 A-record (AcmManaged)
- Security groups
- IAM role + instance profile
- CloudWatch log group
- Secrets Manager secret (CreateNew only; soft-delete with 7-day recovery window)
- VPC + subnets + NAT + IGW (CreateNew only)

`destroy` does not remove the S3 asset bucket (reused across deploys) or existing Secrets Manager / VPC resources (UseExisting paths). Local MCP client config entries are left in place — re-run `configure` or edit manually.
