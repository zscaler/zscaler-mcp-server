---
disable-model-invocation: true
argument-hint: "<connector_group_name_or_connector_name> [symptom: not-enrolling|disconnected|upgrade-failed|high-cpu|high-memory|high-disk]"
description: "Troubleshoot ZPA App Connector issues -- enrollment, connectivity, upgrades, and resource utilization."
---

# Troubleshoot App Connector

Troubleshoot connector: **$ARGUMENTS**

## Step 1: Parse Input

Extract:

- **Connector or connector group name**
- **Symptom**: not enrolling, disconnected, upgrade failed, high CPU/memory/disk, applications unreachable

## Step 2: Inspect Connector Status

List and inspect individual connectors directly:

```text
zpa_list_app_connectors(search="<name>")
zpa_get_app_connector(connector_id="<id>")
```text

Check `runtime_status`:

- `ZPN_STATUS_AUTHENTICATED` = healthy
- `ZPN_STATUS_DISCONNECTED` = lost connection
- `ZPN_STATUS_NOT_ENROLLED` = enrollment failed

Also check `current_version`, `expected_version`, `last_broker_connect_time`, `private_ip`, `public_ip`.

Then inspect the connector group for group-level settings:

```text
zpa_list_app_connector_groups(search="<group_name>")
zpa_get_app_connector_group(group_id="<id>")
```text

## Step 3: Check Provisioning Keys

```text
zpa_list_provisioning_keys(key_type="connector")
```text

Verify:

- Key `max_usage` vs current count (exhausted = no new enrollments)
- Key is enabled and not expired
- Key `component_id` matches the target connector group

## Step 4: Verify Infrastructure Chain

```text
zpa_list_server_groups()
zpa_list_application_segments()
```text

Confirm server groups reference this connector group and application segments use those server groups.

## Step 5: Diagnose by Symptom

**Not Enrolling:**

- Provisioning key exhausted → increase `max_usage` or create new key
- DNS failure → connector must resolve `co2br.<cloud>.net`
- SSL interception on path → allowlist ZPA domains
- Clock skew → sync NTP
- VM migration → wipe and re-provision

**Disconnected:**

- Network/firewall blocking TCP 443 to ZPA Public Service Edges
- SSL interception breaking TLS to brokers
- Check firewall requirements at `config.zscaler.com/<cloud>/zpa`

**Upgrade Failed:**

- Cannot reach `dist.private.zscaler.com` or `yum.private.zscaler.com`
- Revert: remove `/opt/zscaler/var/image.bin`, `/opt/zscaler/var/version`, `/opt/zscaler/var/metadata` and restart
- Full rebuild: wipe `/opt/zscaler/var/*` and re-provision

**High CPU/Memory/Disk:**

- Check if `zpa-connector-child` is the top consumer (another process may be the cause)
- Normalize CPU by core count
- Check memory: `curl -s 127.0.0.1:9000/memory/status`
- Check disk: `sudo df -h` (min 100MB free required)
- Scale: add connectors to group, increase VM resources, or create dedicated groups

## Step 6: Present Report

Provide structured diagnosis with: connector group status, connector states, provisioning key status, infrastructure chain, root cause, CLI commands for on-host remediation, and escalation guidance if needed.
