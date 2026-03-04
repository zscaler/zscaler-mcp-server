---
disable-model-invocation: true
argument-hint: "<location_name> <ip_address> [vpn_type: ufqdn|ip]"
description: "End-to-end onboarding of a new ZIA location with traffic forwarding dependencies."
---

# Onboard Location in ZIA

Onboard a new location: **$ARGUMENTS**

## Step 1: Parse Input

Extract:
- **Location name** (e.g., "New York Office")
- **IP address** for the static IP
- **VPN type**: UFQDN-based or IP-based (default: UFQDN)

If IP address is missing, ask the administrator.

## Step 2: Check Existing Resources

```
zia_list_locations()
```

Verify no duplicate location exists.

## Step 3: Create Static IP

```
zia_create_static_ip(ip_address="<ip>", comment="Static IP for <location>")
```

## Step 4: Create VPN Credentials

**UFQDN-based:**
```
zia_create_vpn_credential(type="UFQDN", fqdn="<location>@company.com", comments="VPN for <location>")
```

**IP-based:**
```
zia_create_vpn_credential(type="IP", ip_address="<ip>", comments="VPN for <location>")
```

## Step 5: Create Location

```
zia_create_location(
  name="<location_name>",
  static_ip_ids=[<static_ip_id>],
  vpn_credential_ids=[<vpn_id>]
)
```

## Step 6: Activate Configuration

**Critical -- ZIA changes require activation:**

```
zia_activate_configuration()
```

## Step 7: Verify

```
zia_get_location(location_id="<id>")
```

Present a summary of all created resources. Remind the administrator to configure IPSec tunnels on their network equipment using the VPN credentials.
