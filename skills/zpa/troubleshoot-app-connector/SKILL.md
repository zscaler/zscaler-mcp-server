---
name: zpa-troubleshoot-app-connector
description: "Troubleshoot ZPA App Connector issues including enrollment failures, upgrade problems, Public Service Edge connectivity, and high CPU/memory/disk utilization. Uses MCP tools to inspect connector groups, provisioning keys, server groups, and application segments, then provides runbook-guided remediation steps. Use when an administrator reports 'connector is down', 'connector not enrolling', 'connector upgrade failed', or 'connector high CPU.'"
---

# ZPA: Troubleshoot App Connector

## Keywords

app connector, connector down, connector not enrolling, enrollment failure, connector upgrade, connector high cpu, connector memory, connector troubleshoot, connector status, connector group, provisioning key, broker connection, public service edge, connector health

## Overview

Troubleshoot ZPA App Connector issues by combining MCP API inspection (connector groups, provisioning keys, server groups) with operational runbook knowledge. This skill covers the four major App Connector failure categories: enrollment failures, upgrade issues, Public Service Edge connectivity, and resource utilization.

**Use this skill when:** An administrator reports App Connector problems -- connector not appearing, enrollment failures, upgrade failures, high resource usage, or application unreachability traced to a connector issue.

---

## Workflow

### Step 1: Gather Issue Details

Collect from the administrator:

**Required:**

- Connector name or the App Connector Group it belongs to
- Symptom: not enrolling, showing disconnected, upgrade failed, high CPU/memory, applications unreachable

**Helpful:**

- When did the issue start?
- Was anything changed recently (provisioning key, network, firewall)?
- Is it one connector or multiple connectors in the group?
- Cloud name (e.g., prod.zpath.net, zpatwo.net)

---

### Step 2: Inspect Connector and Connector Group Status via API

**List individual app connectors** to get their runtime status directly:

```text
zpa_list_app_connectors(search="<connector_name>")
```text

Get detailed info for a specific connector:

```text
zpa_get_app_connector(connector_id="<connector_id>")
```text

**Check for:**

- `runtime_status` -- `ZPN_STATUS_AUTHENTICATED` (healthy), `ZPN_STATUS_DISCONNECTED`, `ZPN_STATUS_NOT_ENROLLED`
- `current_version` -- software version running
- `expected_version` -- version it should be running (upgrade needed if different)
- `last_broker_connect_time` -- when it last connected to ZPA cloud
- `last_broker_disconnect_time` -- when it last disconnected
- `control_channel_status` -- control connection state
- `connector_group_id` -- which group this connector belongs to
- `private_ip` / `public_ip` -- network addresses
- `platform` -- OS/hypervisor platform
- `enrollment_cert` -- certificate details and expiry

**Then inspect the connector group** for group-level settings:

```text
zpa_list_app_connector_groups(search="<connector_group_name>")
zpa_get_app_connector_group(group_id="<group_id>")
```text

**Check group settings:**

- `enabled` -- is the group enabled?
- `upgrade_day` and `upgrade_time_in_secs` -- maintenance window
- `version_profile` -- version track (Default, Previous Default, New Release)

**Connector status values:**

| Status | Meaning |
|--------|---------|
| `ZPN_STATUS_AUTHENTICATED` | Healthy, control connection established |
| `ZPN_STATUS_DISCONNECTED` | Lost connection to ZPA cloud |
| `ZPN_STATUS_NOT_ENROLLED` | Never enrolled or enrollment failed |
| `ZPN_STATUS_PENDING` | Enrollment in progress |

---

### Step 3: Check Provisioning Keys

Provisioning key issues are the #1 cause of enrollment failures.

```text
zpa_list_provisioning_keys(key_type="connector")
```text

For a specific key:

```text
zpa_get_provisioning_key(key_id="<key_id>", key_type="connector")
```text

**Check for:**

- `max_usage` vs current enrollment count -- if equal, no new enrollments can use this key
- `enabled` -- is the key active?
- The `component_id` must match the target App Connector Group
- Key must not be expired

**If max usage is reached:**

```text
The provisioning key has reached its maximum enrollment count.

Resolution: Increase the max_usage value or create a new provisioning key
for this connector group.
```text

```text
zpa_update_provisioning_key(
  key_id="<key_id>",
  key_type="connector",
  max_usage=<current + needed>
)
```text

Or create a new key:

```text
zpa_create_provisioning_key(
  name="<name>",
  key_type="connector",
  max_usage=10,
  component_id="<connector_group_id>",
  enrollment_cert_id="<cert_id>"
)
```text

---

### Step 4: Check Server Groups and Application Segments

If applications are unreachable through the connector, verify the infrastructure chain.

```text
zpa_list_server_groups()
```text

Find server groups that reference the affected connector group:

```text
zpa_get_server_group(group_id="<server_group_id>")
```text

**Check for:**

- `app_connector_groups` -- does it reference the affected connector group?
- `enabled` -- is the server group active?
- `servers` -- are application servers configured?

Then check which application segments use this server group:

```text
zpa_list_application_segments()
```text

**If applications are unreachable:**

- Verify the domain names in the application segment match what users access
- Verify ports are correct
- Confirm the server group → connector group → connector chain is intact
- Check that connectors can reach the internal application servers (network-level)

---

### Step 5: Diagnose by Symptom Category

#### 5A: Enrollment Failure

If the connector shows `ZPN_STATUS_NOT_ENROLLED`:

1. **Provisioning key issues** (most common):
   - Key max_usage reached (Step 3 above)
   - Key copied incorrectly -- administrator should re-copy the exact key
   - Key associated with wrong connector group

2. **DNS resolution failure:**
   - Connector must resolve `co2br.<cloudname>.net`
   - Check DNS servers in `/etc/resolv.conf` on the connector
   - Common clouds: `prod.zpath.net`, `zpatwo.net`

3. **Network connectivity:**
   - Connector needs outbound TCP 443 to ZPA Public Service Edges
   - Check firewall rules per `config.zscaler.com/<cloudname>/zpa`
   - SSL interception on the path will break enrollment (connector logs show "self signed certificate in certificate chain")

4. **Certificate/time issues:**
   - If connector clock is skewed, certificate validation fails
   - Logs show: "certificate is not yet valid" or similar
   - Resolution: sync NTP on the connector host

5. **VM migration issues:**
   - If connector was cloned/migrated (changed MAC/hardware ID), enrollment breaks
   - Logs show: "Cannot decrypt data from instance_id.crypt"
   - Resolution: wipe and re-provision the connector

**Wipe and re-provision procedure:**

```text
1. Stop: sudo systemctl stop zpa-connector
2. Wipe: sudo rm /opt/zscaler/var/*
3. Create key file: sudo touch /opt/zscaler/var/provision_key && sudo chmod 644 /opt/zscaler/var/provision_key
4. Paste provisioning key into the file
5. Start: sudo systemctl start zpa-connector
```text

#### 5B: Upgrade Failure

If connector upgrade failed:

1. **Check current version** via the connector group API response (Step 2)
2. **Network connectivity to upgrade servers:**
   - Connector needs to reach `dist.private.zscaler.com` and `yum.private.zscaler.com`
   - Test: `ping dist.private.zscaler.com` and `telnet dist.private.zscaler.com 443`

3. **Revert to default version:**

```text
1. sudo systemctl stop zpa-connector
2. sudo rm /opt/zscaler/var/image.bin
3. sudo rm /opt/zscaler/var/version
4. sudo rm /opt/zscaler/var/metadata
5. sudo systemctl start zpa-connector
```text

The connector will re-download a clean default version from the CDN.

4. **Full rebuild** if revert doesn't work (follow wipe procedure in 5A)

#### 5C: Public Service Edge Connectivity

If connector shows `ZPN_STATUS_DISCONNECTED`:

1. **DNS check:** Verify `co2br.<cloudname>.net` resolves correctly
2. **ICMP check:** `ping co2br.<cloudname>.net`
3. **TCP check:** `telnet <broker_ip> 443`
4. **TLS check:** `openssl s_client -servername <company>.com.server1.net -connect <broker_ip>:443`
   - Should return a Zscaler certificate (CN=broker*.*.prod.zpath.net)
   - If it returns a different CA, SSL interception is occurring
5. **Packet capture:** `sudo tcpdump -i any -w output.pcap`
   - Look for TCP RSTs or connection timeouts
   - Compare TTL of RST packets with expected hop count from MTR

**Firewall requirements:**

- All ZPA IP ranges must be allowed: check `config.zscaler.com/<cloudname>/zpa`
- Common ports: TCP 443 outbound to brokers
- SSL interception devices must allowlist all ZPA domains

#### 5D: High CPU / Memory / Disk

1. **CPU:**
   - Check if `zpa-connector-child` is the top consumer: `ps aux --sort=-pcpu | head -5`
   - If another process is high, the issue is not Zscaler-related
   - Normalize CPU % by core count (4 cores = 400% max)
   - If consistently >80% normalized CPU, collect logs and contact Zscaler Support

2. **Memory:**
   - Check process memory: `ps aux --sort=-pmem | head -5`
   - Check connector internal memory: `curl -s 127.0.0.1:9000/memory/status`
   - Consider adding more connectors to the group to distribute load

3. **Disk:**
   - Check space: `sudo df -h`
   - Find large consumers: `sudo du -a / | sort -n -r | head -n 20`
   - Common culprit: `/var/log` and `/var/cache/yum`
   - Clean journals: `sudo journalctl --vacuum-size=1G`
   - Minimum 100MB free required; connector auto-restarts below this

4. **Scaling recommendations:**
   - Increase VM resources (CPU/RAM) per Zscaler sizing guide
   - Add more connectors to the group to distribute users
   - Create dedicated connector groups for high-traffic application segments

---

### Step 6: Present Diagnosis

#### Report Format

```text
App Connector Troubleshooting Report
======================================

**Connector Group:** <name> (ID: <id>)
**Affected Connector(s):** <connector_name(s)>
**Symptom:** <enrollment failure / disconnected / upgrade failed / high resource>
**Status:** <ZPN_STATUS_*>

---

## Diagnosis: <ROOT CAUSE>

---

## API Findings

### Connector Group Status
- Group enabled: Yes/No
- Total connectors: X
- Healthy (AUTHENTICATED): Y
- Disconnected: Z
- Version: X.Y.Z
- Upgrade window: <day> at <time>

### Provisioning Keys
- Key "<name>": <current_usage>/<max_usage> enrollments used
- Key status: Active/Exhausted/Expired

### Server Groups Using This Connector Group
- "<server_group_name>": enabled, X application servers
- Application segments: <list>

---

## Root Cause

<Explanation based on API findings and symptom analysis>

---

## Remediation Steps

1. <Actionable step with specific commands/API calls>
2. <Next step>
3. <Verification step>

---

## If Issue Persists

Collect the following and contact Zscaler Support:
- Connector journalctl logs: sudo journalctl -u zpa-connector > connector-logs.txt
- Memory status: curl -s 127.0.0.1:9000/memory/status
- Memory argo: curl -s 127.0.0.1:9000/memory/argo
- System info: lscpu, free -h, df -h
```text

---

## Healthy Connector Indicators

A healthy App Connector shows these in its journalctl status block (repeated every 60 seconds):

- `Control connection state: fohh_connection_connected` -- connected to ZPA cloud
- Certificate expiry > 30 days
- `uptime` continuously incrementing (no resets)
- `Broker data connection count` > 0 with `backed_off connections = 0`
- `Registered apps count = N, alive app = N` (all apps alive)

---

## Quick Reference

**API Tools -- App Connectors (individual):**

- `zpa_list_app_connectors(search)` -- list connectors with runtime status, version, health
- `zpa_get_app_connector(connector_id)` -- detailed connector info (status, version, IPs, cert)
- `zpa_update_app_connector(connector_id, enabled)` -- enable/disable a connector
- `zpa_delete_app_connector(connector_id)` -- remove a connector from ZPA cloud
- `zpa_bulk_delete_app_connectors(connector_ids)` -- remove multiple connectors

**API Tools -- App Connector Groups:**

- `zpa_list_app_connector_groups(search)` -- find connector groups
- `zpa_get_app_connector_group(group_id)` -- group settings (upgrade window, version profile)

**API Tools -- Provisioning & Infrastructure:**

- `zpa_list_provisioning_keys(key_type="connector")` -- list provisioning keys
- `zpa_get_provisioning_key(key_id, key_type)` -- key details including usage count
- `zpa_create_provisioning_key(...)` -- create new provisioning key
- `zpa_update_provisioning_key(...)` -- update key (e.g., increase max_usage)
- `zpa_list_server_groups()` -- find server groups using this connector group
- `zpa_get_server_group(group_id)` -- server group details
- `zpa_list_application_segments()` -- find affected application segments

**CLI Commands (run on the connector host):**

- `sudo journalctl -u zpa-connector -f` -- live connector logs
- `dig co2br.<cloud>.net` -- DNS resolution check
- `openssl s_client -connect <broker_ip>:443` -- TLS connectivity check
- `curl -s 127.0.0.1:9000/memory/status` -- internal memory stats
- `ps aux --sort=-pcpu | head -5` -- top CPU consumers
- `sudo df -h` -- disk usage
