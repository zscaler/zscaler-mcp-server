---
name: zia-onboard-location
description: "End-to-end onboarding of a new ZIA location with its traffic forwarding dependencies. Walks through the full dependency chain: (1) Create a static IP for the site's egress point, (2) Create VPN credentials (UFQDN or IP-based) for the IPSec tunnel, (3) Create the location referencing the static IP and VPN credentials, (4) Optionally create a sub-location. Covers both UFQDN-based (simple) and IP-based (requires static IP first) VPN credential flows. Use when an administrator asks: 'Add a new office location', 'Onboard a branch office', or 'Set up traffic forwarding for a new site.'"
---

# ZIA: Onboard Location

## Keywords

onboard location, new location, add location, branch office, zia location, traffic forwarding, vpn credentials, static ip, ipsec tunnel, site onboarding, sub-location, office setup

## Overview

Onboard a new location in Zscaler Internet Access by walking through the full traffic forwarding dependency chain. Locations require either static IPs or VPN credentials (or both) before they can be created. This skill covers both UFQDN-based and IP-based VPN credential flows, sub-location creation, and location configuration options.

**Use this skill when:** An administrator wants to add a new office, branch, or datacenter location to ZIA, configure traffic forwarding for a new site, or set up IPSec VPN tunnels for location-based security.

---

## Dependency Chain

```text
Static IP (optional, required for IP-based VPN)
     │
     ▼
VPN Credentials (UFQDN or IP type)
     │
     ▼
Location (references VPN credentials and/or static IPs)
     │
     ▼
Sub-Location (optional, references parent location)
```text

**Two flows:**

- **UFQDN flow** (simpler): Create VPN credential (UFQDN) -> Create location with VPN credential
- **IP flow** (full chain): Create static IP -> Create VPN credential (IP) referencing static IP -> Create location with both static IP and VPN credential

---

## Workflow

### Step 1: Gather Site Information

Ask the administrator:

**Required:**

- Location name (e.g., "USA_SJC_37", "London_Office_01")
- Country (e.g., "UNITED_STATES", "CANADA", "UNITED_KINGDOM")
- Timezone (e.g., "UNITED_STATES_AMERICA_LOS_ANGELES", "CANADA_AMERICA_VANCOUVER")
- Traffic forwarding method: UFQDN-based VPN or IP-based VPN

**For UFQDN-based VPN:**

- FQDN identifier (e.g., "<sjc-37@acme.com>")
- Pre-shared key for the IPSec tunnel

**For IP-based VPN:**

- Public IP address of the site's egress point
- Pre-shared key for the IPSec tunnel

**Optional:**

- Description
- State (e.g., "California")
- Profile: `CORPORATE`, `SERVER`, `GUESTWIFI`, `IOT`, `WORKLOAD`, or `NONE`
- Authentication settings (auth_required, idle_time_in_minutes)
- Firewall/IPS settings (ofw_enabled, ips_control)
- Bandwidth limits (up_bandwidth, dn_bandwidth)
- Surrogate IP settings
- XFF forwarding

---

### Step 2: Check for Existing Resources

Before creating anything, list existing resources to avoid duplicates.

**Check existing locations:**

```text
zia_list_locations()
```text

**Check existing static IPs:**

```text
zia_list_static_ips()
```text

**Check existing VPN credentials:**

```text
zia_list_vpn_credentials()
```text

---

### Step 3: Create Static IP (IP-based VPN only)

If using IP-based VPN credentials, the static IP must be created first.

```text
zia_create_static_ip(
  ip_address="203.0.113.10",
  routable_ip=True,
  comment="SJC-37 Office Egress IP",
  geo_override=False
)
```text

Save the returned `ip_address` and `id` for the next steps.

**Verify:**

```text
zia_get_static_ip(static_ip_id="<returned_id>")
```text

**Note:** Geolocation is automatically determined from the IP address. Set `geo_override=True` with explicit `latitude`/`longitude` only if you need custom coordinates.

---

### Step 4: Create VPN Credentials

#### Option A: UFQDN-Based VPN (simpler, no static IP needed)

```text
zia_create_vpn_credential(
  credential_type="UFQDN",
  fqdn="sjc-37@acme.com",
  pre_shared_key="<pre_shared_key>",
  comments="USA - San Jose IPSec Tunnel"
)
```text

Save the returned `id` and `type` for the location creation.

#### Option B: IP-Based VPN (requires static IP from Step 3)

```text
zia_create_vpn_credential(
  credential_type="IP",
  ip_address="203.0.113.10",
  pre_shared_key="<pre_shared_key>",
  comments="USA - San Jose IPSec Tunnel"
)
```text

Save the returned `id` and `type`.

**Verify:**

```text
zia_get_vpn_credential(credential_id="<returned_id>")
```text

---

### Step 5: Create the Location

#### With UFQDN VPN Credentials

```text
zia_create_location(
  location={
    "name": "USA_SJC_37",
    "description": "San Jose Office - Branch 37",
    "country": "UNITED_STATES",
    "tz": "UNITED_STATES_AMERICA_LOS_ANGELES",
    "state": "California",
    "profile": "CORPORATE",
    "authRequired": True,
    "idleTimeInMinutes": 720,
    "displayTimeUnit": "HOUR",
    "surrogateIP": True,
    "xffForwardEnabled": True,
    "ofwEnabled": True,
    "ipsControl": True,
    "vpnCredentials": [
      {
        "id": <vpn_credential_id>,
        "type": "UFQDN"
      }
    ]
  }
)
```text

#### With IP VPN Credentials and Static IP

```text
zia_create_location(
  location={
    "name": "USA_SJC_37",
    "description": "San Jose Office - Branch 37",
    "country": "UNITED_STATES",
    "tz": "UNITED_STATES_AMERICA_LOS_ANGELES",
    "state": "California",
    "profile": "CORPORATE",
    "authRequired": True,
    "idleTimeInMinutes": 720,
    "displayTimeUnit": "HOUR",
    "surrogateIP": True,
    "xffForwardEnabled": True,
    "ofwEnabled": True,
    "ipsControl": True,
    "ipAddresses": ["203.0.113.10"],
    "vpnCredentials": [
      {
        "id": <vpn_credential_id>,
        "type": "IP",
        "ipAddress": "203.0.113.10"
      }
    ]
  }
)
```text

Save the returned location `id` for sub-location creation if needed.

**Verify:**

```text
zia_get_location(location_id="<returned_id>")
```text

---

### Step 6: Create Sub-Location (Optional)

Sub-locations segment traffic within a parent location (e.g., by subnet or VLAN).

```text
zia_create_location(
  location={
    "name": "USA_SJC37_Office-Branch01",
    "description": "SJC37 Office Branch 01 - Engineering VLAN",
    "country": "UNITED_STATES",
    "tz": "UNITED_STATES_AMERICA_LOS_ANGELES",
    "profile": "CORPORATE",
    "parentId": <parent_location_id>,
    "authRequired": True,
    "idleTimeInMinutes": 720,
    "displayTimeUnit": "HOUR",
    "surrogateIP": True,
    "ofwEnabled": True,
    "ipAddresses": ["10.5.0.0-10.5.255.255"],
    "upBandwidth": 10000,
    "dnBandwidth": 10000
  }
)
```text

**Sub-location notes:**

- Must reference `parentId` of an existing location
- Uses internal IP ranges (e.g., `10.5.0.0-10.5.255.255`) not public IPs
- Can have different bandwidth limits and policy settings than the parent
- Inherits VPN credentials from the parent location

---

### Step 7: Activate Configuration

After creating locations, activate the configuration to push changes to the Zscaler cloud:

```text
zia_activate_configuration()
```text

---

### Step 8: Verify and Summarize

```text
Location onboarding complete.

**Location:** USA_SJC_37
- Country: United States
- Timezone: US/Pacific
- Profile: CORPORATE
- Firewall: Enabled
- IPS: Enabled
- XFF Forwarding: Enabled

**Traffic Forwarding:**
- Static IP: 203.0.113.10 (ID: <id>)
- VPN Credential: IP-based (ID: <id>)
- IPSec Tunnel: Configured

**Sub-Location:**
- Name: USA_SJC37_Office-Branch01
- IP Range: 10.5.0.0 - 10.5.255.255
- Bandwidth: 10Mbps up / 10Mbps down

**Configuration:** Activated

**Next Steps:**
1. Configure IPSec tunnel on the branch router pointing to Zscaler
2. Verify traffic is flowing through the ZIA service
3. Assign the location to URL filtering, firewall, or DLP rules if needed
```text

---

## Location Configuration Options

### Profile Types

| Profile | Use Case |
|---|---|
| `CORPORATE` | Standard corporate office |
| `SERVER` | Data center or server farm |
| `GUESTWIFI` | Guest wireless network |
| `IOT` | IoT device network |
| `WORKLOAD` | Cloud workload (AWS, Azure) |
| `NONE` | Unassigned (default) |

### Security Settings

| Setting | Description | Recommended |
|---|---|---|
| `authRequired` | Enforce user authentication | `True` for CORPORATE |
| `ofwEnabled` | Enable cloud firewall | `True` |
| `ipsControl` | Enable IPS (requires firewall) | `True` |
| `surrogateIP` | Map users to device IPs | `True` for auth |
| `xffForwardEnabled` | Forward X-Forwarded-For header | `True` |
| `cautionEnabled` | Show caution notifications | Per policy |

### Authentication Settings

| Setting | Description |
|---|---|
| `idleTimeInMinutes` | Surrogate IP idle timeout (e.g., 720 = 12 hours) |
| `displayTimeUnit` | Display unit: `MINUTE`, `HOUR`, `DAY` |
| `surrogateRefreshTimeInMinutes` | Re-validate surrogate IP interval |
| `digestAuthEnabled` | Enable digest authentication |
| `kerberosAuth` | Enable Kerberos authentication |

---

## Ready-to-Use Templates

### Corporate Office (UFQDN VPN)

```python
# Step 1: VPN Credential
zia_create_vpn_credential(
  credential_type="UFQDN",
  fqdn="london-office@company.com",
  pre_shared_key="<psk>",
  comments="London Office IPSec"
)

# Step 2: Location
zia_create_location(location={
  "name": "UK_London_01",
  "description": "London Head Office",
  "country": "UNITED_KINGDOM",
  "tz": "EUROPE_LONDON",
  "profile": "CORPORATE",
  "authRequired": True,
  "idleTimeInMinutes": 720,
  "displayTimeUnit": "HOUR",
  "surrogateIP": True,
  "xffForwardEnabled": True,
  "ofwEnabled": True,
  "ipsControl": True,
  "vpnCredentials": [{"id": <vpn_id>, "type": "UFQDN"}]
})
```text

### Data Center (IP VPN with Static IP)

```python
# Step 1: Static IP
zia_create_static_ip(
  ip_address="198.51.100.1",
  routable_ip=True,
  comment="DC East Egress"
)

# Step 2: VPN Credential
zia_create_vpn_credential(
  credential_type="IP",
  ip_address="198.51.100.1",
  pre_shared_key="<psk>",
  comments="DC East IPSec"
)

# Step 3: Location
zia_create_location(location={
  "name": "US_DC_East_01",
  "description": "US East Data Center",
  "country": "UNITED_STATES",
  "tz": "UNITED_STATES_AMERICA_NEW_YORK",
  "profile": "SERVER",
  "ofwEnabled": True,
  "ipsControl": True,
  "ipAddresses": ["198.51.100.1"],
  "vpnCredentials": [{"id": <vpn_id>, "type": "IP", "ipAddress": "198.51.100.1"}]
})
```text

### Guest WiFi (minimal security)

```python
zia_create_location(location={
  "name": "US_SJC_GuestWifi",
  "description": "Guest WiFi - San Jose Office",
  "country": "UNITED_STATES",
  "tz": "UNITED_STATES_AMERICA_LOS_ANGELES",
  "profile": "GUESTWIFI",
  "parentId": <parent_location_id>,
  "authRequired": False,
  "ofwEnabled": True,
  "ipsControl": False,
  "ipAddresses": ["10.100.0.0-10.100.255.255"]
})
```text

---

## Edge Cases

### Location Without VPN Credentials

A location can be created with only `ipAddresses` (no VPN credentials). This is for sites forwarding traffic via GRE tunnels or proxy chaining rather than IPSec VPN:

```text
zia_create_location(location={
  "name": "US_SJC_GRE",
  "country": "UNITED_STATES",
  "tz": "UNITED_STATES_AMERICA_LOS_ANGELES",
  "ipAddresses": ["203.0.113.10"]
})
```text

### Multiple VPN Credentials per Location

A location can have multiple VPN credentials for redundancy:

```json
"vpnCredentials": [
  {"id": <primary_vpn_id>, "type": "UFQDN"},
  {"id": <secondary_vpn_id>, "type": "UFQDN"}
]
```text

### Sub-Location with Bandwidth Control

Sub-locations can enforce bandwidth limits in bytes:

```json
"upBandwidth": 10000,
"dnBandwidth": 10000
```text

A value of `0` means no bandwidth enforcement.

---

## When NOT to Use This Skill

- Just creating a static IP (not a full location) -- use `zia_create_static_ip` directly
- Just creating VPN credentials (not a location) -- use `zia_create_vpn_credential` directly
- Looking up existing locations -- use `zia_list_locations` directly
- Creating GRE tunnels -- use `zia_create_gre_tunnel` directly
- Creating URL filtering or firewall rules for a location -- use the respective rule creation tools

---

## Quick Reference

**Dependency chain:**

1. `zia_create_static_ip(ip_address, ...)` -- only for IP-based VPN
2. `zia_create_vpn_credential(credential_type, ...)` -- UFQDN or IP
3. `zia_create_location(location={...})` -- the location itself
4. `zia_create_location(location={..., "parentId": ...})` -- optional sub-location
5. `zia_activate_configuration()` -- push changes live

**Verification tools:**

- `zia_list_locations()` -- list all locations
- `zia_get_location(location_id)` -- get location details
- `zia_list_static_ips()` -- list all static IPs
- `zia_get_static_ip(static_ip_id)` -- get static IP details
- `zia_list_vpn_credentials()` -- list all VPN credentials
- `zia_get_vpn_credential(credential_id)` -- get credential details
- `zia_get_activation_status()` -- check activation status

**VPN types:**

- `UFQDN`: Simpler, no static IP needed, identified by FQDN
- `IP`: Requires static IP first, identified by IP address
