---
title: Skills
sidebar_label: Skills
---


<!--
  AUTO-GENERATED — do not edit by hand.
  Source of truth: skills/*/*/SKILL.md (frontmatter)
  Regenerate with: make generate-skills-docs
                   (or: python docs-site/scripts/generate_skills_index.py)
-->


Skills are guided multi-step workflows that ship with the Zscaler MCP Server. Unlike individual tools — which are single API operations — a skill encodes the *playbook* for a complete admin task: which tools to call, in which order, with which guardrails, and how to talk to the admin while doing it.

**How skills get loaded.** Every skill carries a `description` in its frontmatter. MCP clients that support skill loading (Claude Code, Claude Desktop, Cursor) auto-activate a skill when the admin's prompt matches that description. You don't need to invoke them manually — describe what you want, and Claude / Cursor pick the right skill.

**Where skills live.** Every skill is a directory under [`skills/`](https://github.com/zscaler/zscaler-mcp-server/tree/master/skills) on GitHub, organised by Zscaler service. Click any skill below to read its full `SKILL.md` (workflow steps, edge cases, validation rules).


## At a glance

| Service | Skills |
|---------|--------|
| [**ZIA — Internet Access**](#service-zia) | 12 |
| [**ZPA — Private Access**](#service-zpa) | 11 |
| [**ZDX — Digital Experience**](#service-zdx) | 7 |
| [**ZCC — Client Connector**](#service-zcc) | 1 |
| [**ZMS — Microsegmentation**](#service-zms) | 5 |
| [**Z-Insights**](#service-zins) | 4 |
| [**EASM — External Attack Surface**](#service-easm) | 1 |
| [**Cross-Product**](#service-cross-product) | 1 |
| **Total** | **42** |

## ZIA — Internet Access {#service-zia}

### [`zia-audit-ssl-inspection-bypass`](https://github.com/zscaler/zscaler-mcp-server/blob/master/skills/zia/audit-ssl-inspection-bypass/SKILL.md)

Audit ZIA SSL inspection rules to identify which applications, URL categories, users, or groups are subject to INSPECT, DO_NOT_INSPECT, or DO_NOT_DECRYPT actions. This skill focuses exclusively on SSL inspection rules and their configuration. Use when a security administrator asks: 'What SSL rules are in decryption mode?', 'What is bypassing SSL inspection?', 'Are there SSL bypass exceptions?', or 'Audit our SSL inspection policy.'

### [`zia-check-user-url-access`](https://github.com/zscaler/zscaler-mcp-server/blob/master/skills/zia/check-user-url-access/SKILL.md)

Determine whether a specific user or group is allowed to access a given URL by evaluating all applicable ZIA policies in order. Performs URL category lookup, then evaluates URL filtering rules, SSL inspection rules, DLP rules, and cloud firewall rules in priority order to produce a definitive access verdict. Use when an administrator asks: 'Can user X access site Y?', 'Why is a URL blocked?', or 'What policies apply to this user and URL?'

### [`zia-create-cloud-app-control-rule`](https://github.com/zscaler/zscaler-mcp-server/blob/master/skills/zia/create-cloud-app-control-rule/SKILL.md)

Create ZIA Cloud App Control rules that enforce granular, action-level decisions on cloud applications (Dropbox, OneDrive, Google Drive, ChatGPT, GitHub, YouTube, Slack, etc.). Cloud App Control is action-level, not block/allow at the connection layer — actions are things like ALLOW_FILE_SHARE_UPLOAD, BLOCK_WEBMAIL_ATTACH, ISOLATE_AI_ML_WEB_USE, DENY_AI_ML_CHAT, BLOCK_SOCIAL_NETWORKING_POST. Each rule belongs to a category (rule_type) such as FILE_SHARE, WEBMAIL, AI_ML, SYSTEM_AND_DEVELOPMENT, SOCIAL_NETWORKING, STREAMING_MEDIA, etc. Action vocabulary is surfaced at the category level, but the API validates per (rule_type, application, action) tuple — combining multiple apps in a single rule frequently fails with INVALID_INPUT_ARGUMENT, so this skill creates one rule per cloud application when the admin names multiple apps. Use when an admin asks to 'allow Dropbox uploads', 'block ChatGPT', 'restrict GitHub edits', 'isolate AI tools', 'block YouTube uploads', 'allow only viewing on OneDrive', 'block file uploads to personal cloud storage (Dropbox, Google Drive, OneDrive)', or 'create a Cloud App Control rule for X'. Chains to `zia-look-up-cloud-app-name` and `zia-manage-time-interval` when needed.

### [`zia-create-firewall-filtering-rule`](https://github.com/zscaler/zscaler-mcp-server/blob/master/skills/zia/create-firewall-filtering-rule/SKILL.md)

Create a ZIA Cloud Firewall Filtering rule that controls network traffic by source/destination IP, country, network application, network service, device trust level, user/group/department, location, and optional time-of-day schedule (Time Interval). Supported actions: ALLOW, BLOCK_DROP, BLOCK_RESET, BLOCK_ICMP, EVAL_NWAPP. Use when an admin asks to 'create a firewall rule', 'block traffic to X', 'allow traffic from Y', 'block country Z', 'restrict access during business hours', or 'add a firewall exception'. This skill creates exactly one Cloud Firewall rule and chains to `zia-manage-time-interval` when the admin's request includes a recurring schedule.

### [`zia-create-ssl-inspection-rule`](https://github.com/zscaler/zscaler-mcp-server/blob/master/skills/zia/create-ssl-inspection-rule/SKILL.md)

Create a ZIA SSL Inspection rule that controls how Zscaler handles SSL/TLS encrypted traffic — BLOCK (drop the SSL connection), DECRYPT (decrypt and inspect), or DO_NOT_DECRYPT (pass through without decryption). Scopes the rule by cloud applications, URL categories, users, groups, departments, locations, device trust levels, platforms, source/destination IP groups, and ZPA application segments. SSL Inspection rules do NOT support a recurring time-of-day schedule — for time-of-day enforcement, use a different rule type (Cloud Firewall Filtering, URL Filtering, etc.). Use when an admin asks to 'create an SSL inspection rule', 'do not decrypt traffic to X', 'decrypt SSL for Y', 'block SSL for Z', or 'add an SSL bypass exception'. For pure auditing of existing SSL bypass posture, see `zia-audit-ssl-inspection-bypass` (read-only).

### [`zia-create-url-filtering-rule`](https://github.com/zscaler/zscaler-mcp-server/blob/master/skills/zia/create-url-filtering-rule/SKILL.md)

Create a ZIA URL Filtering rule that controls user access to web content by URL category, protocol, request method, user agent, user/group/department, location, device trust level, and optional time-of-day schedule (Time Interval). Supported actions: ALLOW, BLOCK, CAUTION, ISOLATE. Use when an admin asks to 'create a URL filtering rule', 'block category X', 'allow category Y', 'show a caution page for Z', 'isolate access to risky sites', 'block social media during work hours', or 'add a URL filtering exception'. Supports both recurring schedules (`time_windows`) and one-shot date-range validity (`enforce_time_validity`). This skill creates exactly one URL Filtering rule and chains to `zia-manage-time-interval` when the admin's request includes a recurring schedule.

### [`zia-investigate-sandbox`](https://github.com/zscaler/zscaler-mcp-server/blob/master/skills/zia/investigate-sandbox/SKILL.md)

Investigate ZIA Sandbox file analysis results, quarantine issues, and security policy enforcement. Uses sandbox report, quota, behavioral analysis, and file hash tools combined with SSL inspection checks to diagnose why files are blocked, allowed, or stuck in quarantine. Incorporates runbook knowledge for Malware Protection, ATP, and Sandbox policy troubleshooting. Use when an administrator asks 'why is this file blocked?', 'check sandbox report for this hash', 'file stuck in quarantine', or 'sandbox is not analyzing files.'

### [`zia-investigate-url-category`](https://github.com/zscaler/zscaler-mcp-server/blob/master/skills/zia/investigate-url-category/SKILL.md)

Investigate where a specific URL or URL category is referenced across all ZIA policy rules. Searches URL filtering rules, DLP web rules, SSL inspection rules, and cloud firewall rules to provide a comprehensive view of how a category is used. Use when an administrator asks: 'Where is this URL category used?', 'What rules apply to this URL?', or 'Show me the policy impact of this category.'

### [`zia-look-up-cloud-app-name`](https://github.com/zscaler/zscaler-mcp-server/blob/master/skills/zia/look-up-cloud-app-name/SKILL.md)

Look up the canonical ZIA cloud-application name (e.g. ONEDRIVE, GOOGLE_DRIVE, SHAREPOINT_ONLINE, DROPBOX) given whatever the admin typed — friendly names like 'OneDrive', 'Google Drive', 'share point online', loose phrasings like 'sharepoint', or even numeric Shadow IT IDs. Cloud App Control, SSL Inspection, Web DLP, File Type Control, Bandwidth Classes, and Advanced Settings rules all require the canonical ZIA name in their `cloud_applications` field; passing the friendly name or a Shadow IT ID silently coerces to `NONE` and the rule does nothing. Use whenever an admin asks to add, remove, or filter on cloud applications in any policy rule, or asks 'what's the right name for X?'.

### [`zia-look-up-rule-targets`](https://github.com/zscaler/zscaler-mcp-server/blob/master/skills/zia/look-up-rule-targets/SKILL.md)

Look up the shared 'who/where/when/what-device' fields that every ZIA rule resource scopes by — users, groups, departments, locations, location_groups, url_categories, devices, device_groups, workload_groups, labels, and time_windows — and return the IDs (or canonical strings) the rule API expects. Use this skill from inside any ZIA rule create/update workflow (Cloud Firewall, DNS, IPS, URL Filtering, SSL Inspection, Web DLP, File Type Control, Sandbox, Cloud App Control) when the admin names a user, group, location, label, etc. by display name and you need the ID before building the rule payload. Centralises the read-before-write lookup convention so individual rule skills stay short and accurate. The skill enforces the project's hard rules: empty list = does not exist, never invent IDs, never silently substitute, never fan-out retries.

### [`zia-manage-time-interval`](https://github.com/zscaler/zscaler-mcp-server/blob/master/skills/zia/manage-time-interval/SKILL.md)

Find an existing ZIA Time Interval by name, or create a new one when no match exists, then return the interval ID so the caller can attach it to a policy rule via its `time_windows` field. Time Intervals are reusable schedule objects (start time, end time, days of the week) that ZIA Cloud Firewall Filtering, URL Filtering, Cloud App Control, File Type Control, and Sandbox rules reference to enforce recurring time-of-day / day-of-week schedules (e.g. 'only between 8am-5pm Monday-Friday'). Note: SSL Inspection rules do NOT support `time_windows` and cannot consume the output of this skill. Use when an admin asks for 'a schedule', 'business hours', 'after-hours', 'weekends only', 'time window', 'time interval', or any rule that should fire on a recurring time pattern. Other ZIA rule-creation skills chain to this one when the admin's request includes a schedule.

### [`zia-onboard-location`](https://github.com/zscaler/zscaler-mcp-server/blob/master/skills/zia/onboard-location/SKILL.md)

End-to-end onboarding of a new ZIA location with its traffic forwarding dependencies. Walks through the full dependency chain: (1) Create a static IP for the site's egress point, (2) Create VPN credentials (UFQDN or IP-based) for the IPSec tunnel, (3) Create the location referencing the static IP and VPN credentials, (4) Optionally create a sub-location. Covers both UFQDN-based (simple) and IP-based (requires static IP first) VPN credential flows. Use when an administrator asks: 'Add a new office location', 'Onboard a branch office', or 'Set up traffic forwarding for a new site.'

## ZPA — Private Access {#service-zpa}

### [`zpa-application_segment-ba-onboard`](https://github.com/zscaler/zscaler-mcp-server/blob/master/skills/zpa/application_segment-ba-onboard/SKILL.md)

End-to-end onboarding of a new Browser Access (BA) application in Zscaler Private Access. Walks through the full dependency chain — App connector group, server group, segment group, BA TLS certificate, BA application segment with apps_config, and access policy rule — for web apps that should be reachable through the browser without Zscaler Client Connector. Use only when the admin explicitly asks for Browser Access. DO NOT USE WHEN: the admin wants a regular client-routed application segment (use zpa-application_segment-onboard instead).

### [`zpa-application_segment-onboard`](https://github.com/zscaler/zscaler-mcp-server/blob/master/skills/zpa/application_segment-onboard/SKILL.md)

End-to-end onboarding of a new application in Zscaler Private Access. Walks through the complete dependency chain: (1) App connector group, (2) Server group, (3) Segment group, (4) Application segment with domain names and ports, (5) Access policy rule to grant user/group access. Use when an administrator needs to make an internal application accessible through ZPA.

### [`zpa-application_segment-pra-onboard`](https://github.com/zscaler/zscaler-mcp-server/blob/master/skills/zpa/application_segment-pra-onboard/SKILL.md)

End-to-end onboarding of a new Privileged Remote Access (PRA) application in Zscaler Private Access. Walks through the full dependency chain — App connector group, server group, segment group, PRA credential, PRA portal, PRA application segment with apps_config (RDP/SSH targets), and access policy rule — for RDP and SSH targets brokered through the PRA portal without requiring a native RDP/SSH client or Zscaler Client Connector. Use only when the admin explicitly asks for Privileged Remote Access (PRA), RDP, SSH, jump-host, or bastion access. DO NOT USE WHEN: the admin wants a regular client-routed application segment (use zpa-application_segment-onboard) or a clientless web app (use zpa-application_segment-ba-onboard).

### [`zpa-audit-baseline-compliance`](https://github.com/zscaler/zscaler-mcp-server/blob/master/skills/zpa/audit-baseline-compliance/SKILL.md)

Read-only audit of a ZPA tenant against the Zscaler ZPA Baseline Recommendations v1.0 document. Inventories app connector groups, server groups, application segments, access policy rules, forwarding policy rules, timeout policy rules, and (when available) LSS configs, then scores ~26 configuration-only checks across 7 categories and renders an interactive Zscaler-styled web report (single-file HTML, plus an optional .jsx component) — searchable, filterable by category, severity, and security framework (NIST SP 800-53 Rev. 5 and CIS Critical Security Controls v8), with per-finding evidence, remediation, and framework citations suitable as supporting evidence for SOC 2, FedRAMP, ISO 27001, and NIST CSF assessments, and printable to PDF from the browser. Use when an administrator asks to audit ZPA against best practices, run a baseline-compliance review, get a ZPA health check, gather compliance evidence, or see how their tenant compares to the recommended baseline. NEVER mutates the tenant — read-only.

### [`zpa-create-access-policy-rule`](https://github.com/zscaler/zscaler-mcp-server/blob/master/skills/zpa/create-access-policy-rule/SKILL.md)

Create ZPA access policy rules with v2 conditions. Supports all condition object types: APP, APP_GROUP, SAML, SCIM, SCIM_GROUP, PLATFORM, COUNTRY_CODE, POSTURE, TRUSTED_NETWORK, RISK_FACTOR_TYPE, CLIENT_TYPE, MACHINE_GRP, LOCATION, and CHROME_ENTERPRISE. Walks through: (1) gathering requirements, (2) looking up identity attributes (SAML/SCIM), (3) building the conditions payload, (4) creating the rule. Includes ready-to-use examples for common scenarios: SCIM group access, SAML attribute matching, platform restrictions, country-based access, posture checks, and combined conditions.

### [`zpa-create-conditional-access-rule`](https://github.com/zscaler/zscaler-mcp-server/blob/master/skills/zpa/create-conditional-access-rule/SKILL.md)

Create a ZPA Access Policy rule that gates access to a private application on multiple combined checks: identity (SCIM group / SAML), one or more named device posture profiles (associated by UDID; ZPA does not introspect what each profile checks), platform reported by ZCC, country, and risk-score level. Use when an admin asks for 'conditional access', 'multi-check access rule', 'attach posture profile X and risk level low to this rule', or 'allow only if posture passes and risk is low' for a private application. For session-duration / re-auth requirements, see `zpa-create-session-duration-rule` (separate ZPA resource type).

### [`zpa-create-forwarding-policy-rule`](https://github.com/zscaler/zscaler-mcp-server/blob/master/skills/zpa/create-forwarding-policy-rule/SKILL.md)

Create ZPA client forwarding policy rules that control how traffic is routed from the Zscaler Client Connector. Supports actions: BYPASS (direct internet), INTERCEPT (route through ZPA), INTERCEPT_ACCESSIBLE (route only if reachable). Conditions support APP, APP_GROUP, SAML, SCIM, SCIM_GROUP, PLATFORM, COUNTRY_CODE, POSTURE, TRUSTED_NETWORK, and CLIENT_TYPE. Use when an administrator asks: 'Bypass ZPA for specific apps', 'Route traffic directly', or 'Create a forwarding exception.'

### [`zpa-create-server-group`](https://github.com/zscaler/zscaler-mcp-server/blob/master/skills/zpa/create-server-group/SKILL.md)

Create a ZPA server group with all required dependencies. Server groups require app connector groups to exist first. This skill walks through the dependency chain: (1) Check for existing app connector groups, (2) Create an app connector group if none exist, (3) Create the server group referencing the connector group IDs, (4) Verify the server group was created correctly. Use when an administrator needs to set up a new server group for application access.

### [`zpa-create-session-duration-rule`](https://github.com/zscaler/zscaler-mcp-server/blob/master/skills/zpa/create-session-duration-rule/SKILL.md)

Create a ZPA Timeout Policy rule that enforces session duration — i.e. forces re-authentication after N minutes/hours/days, optionally with an idle-timeout. Use this skill when an admin asks for 'session duration', 'auto-revoke', 're-authentication interval', 'force re-auth after X hours', or 'session must expire after a workday' for ZPA. Scopes by SCIM group, SAML attribute, application segment, platform, and posture. ZPA Timeout Policy is a separate resource type from Access Policy; this skill creates timeout rules only and does not modify or pair with access rules.

### [`zpa-create-timeout-policy-rule`](https://github.com/zscaler/zscaler-mcp-server/blob/master/skills/zpa/create-timeout-policy-rule/SKILL.md)

Create ZPA timeout policy rules that control session re-authentication and idle timeout behavior. Configures how long a user session remains active (reauth_timeout) and how long an idle session persists (reauth_idle_timeout) before requiring re-authentication. Supports conditions: APP, APP_GROUP, CLIENT_TYPE, SAML, SCIM, SCIM_GROUP, PLATFORM, and POSTURE. Use when an administrator asks: 'Set session timeout', 'Configure idle timeout', 'Require re-authentication after X hours', or 'Set different timeouts per app or user group.'

### [`zpa-troubleshoot-app-connector`](https://github.com/zscaler/zscaler-mcp-server/blob/master/skills/zpa/troubleshoot-app-connector/SKILL.md)

Troubleshoot ZPA App Connector issues including enrollment failures, upgrade problems, Public Service Edge connectivity, and high CPU/memory/disk utilization. Uses MCP tools to inspect connector groups, provisioning keys, server groups, and application segments, then provides runbook-guided remediation steps. Use when an administrator reports 'connector is down', 'connector not enrolling', 'connector upgrade failed', or 'connector high CPU.'

## ZDX — Digital Experience {#service-zdx}

### [`zdx-analyze-application-health`](https://github.com/zscaler/zscaler-mcp-server/blob/master/skills/zdx/analyze-application-health/SKILL.md)

Analyze the health of one or more monitored applications across the organization using ZDX scores, metrics, and affected-user breakdowns. Identifies which applications are degraded, which metrics are the bottleneck, and which users are most impacted. Aligned with ZDX Copilot analytics use cases. Use when an administrator asks: 'How are my applications performing?', 'Which apps have low ZDX scores?', 'Show me the number of applications impacted by alerts', or 'What is the ZDX Score for Zoom?'

### [`zdx-audit-software-inventory`](https://github.com/zscaler/zscaler-mcp-server/blob/master/skills/zdx/audit-software-inventory/SKILL.md)

Audit the software inventory across devices in the organization using ZDX data. Lists installed software, filters by location, department, or user, and drills into specific software version details. Use for compliance audits, security vulnerability assessments, or identifying outdated software. Use when an administrator asks: 'What software is installed on our devices?', 'Find all devices running Chrome version X', 'Audit software versions across the organization', or 'Which departments have outdated Java?'

### [`zdx-compare-location-experience`](https://github.com/zscaler/zscaler-mcp-server/blob/master/skills/zdx/compare-location-experience/SKILL.md)

Compare digital experience across locations, departments, and geolocations using ZDX data. Identifies which offices or regions have the best and worst experience for specific applications, detects location-specific issues, and provides optimization recommendations. Aligned with ZDX Copilot analytics and optimization use cases. Use when an administrator asks: 'Which office has the worst experience?', 'Compare application performance between locations', 'Is the Dallas office having network issues?', or 'Show me ZDX scores by department.'

### [`zdx-diagnose-deeptrace`](https://github.com/zscaler/zscaler-mcp-server/blob/master/skills/zdx/diagnose-deeptrace/SKILL.md)

Run a ZDX deep trace diagnostics session to investigate network and device issues. Start new sessions, analyze web probe metrics, cloud path topology, device health, top processes, and event timelines to pinpoint root cause. Use when an administrator asks: 'Start a deep trace for this user', 'Analyze the diagnostics session', 'Why is the network path slow?', 'Check cloud path for packet loss', or 'What happened during the trace?'

### [`zdx-investigate-alerts`](https://github.com/zscaler/zscaler-mcp-server/blob/master/skills/zdx/investigate-alerts/SKILL.md)

Investigate active and historical ZDX alerts to understand their scope, root cause, and impact. Drills into affected devices, correlates with application metrics, and identifies patterns across time. Aligned with ZDX Copilot troubleshooting use cases. Use when an administrator asks: 'Show me ongoing alerts', 'What incidents happened in the last 48 hours?', 'How many users are affected by this alert?', or 'Is there an ISP issue?'

### [`zdx-investigate-multi-app-outage`](https://github.com/zscaler/zscaler-mcp-server/blob/master/skills/zdx/investigate-multi-app-outage/SKILL.md)

Diagnose a multi-application outage scoped to one location by correlating ZDX alerts, affected devices, and shared cloud-path hops. Identifies the devices affected at a specific office, compares the per-application network path across multiple SaaS apps to surface the common network bottleneck, and produces an evidence-backed recommendation. Use when an admin reports: 'A ZDX alert shows users in the Columbus office cannot reach Salesforce and ServiceNow', 'Identify affected devices and the common network path issue', 'Multiple users at Dallas are having issues with several SaaS apps', 'What do these failing apps have in common at this office?', or 'Find the shared network bottleneck for the New York users hitting Workday and Box.'

### [`zdx-troubleshoot-user-experience`](https://github.com/zscaler/zscaler-mcp-server/blob/master/skills/zdx/troubleshoot-user-experience/SKILL.md)

Troubleshoot a user's digital experience using ZDX data. Investigates device health, application scores, network path metrics, and active alerts to identify performance bottlenecks. Use when an administrator reports: 'User says app is slow', 'Check user experience', or 'Why is the application score low?'

## ZCC — Client Connector {#service-zcc}

### [`zcc-generate-logout-otp`](https://github.com/zscaler/zscaler-mcp-server/blob/master/skills/zcc/generate-logout-otp/SKILL.md)

Generate a One-Time Logout Password (OTP) for a Zscaler Client Connector (ZCC) user. Walks the admin from a user identifier (email or device name) through device lookup → confirmation → OTP retrieval → secure delivery, surfacing logout_otp from the ZCC OTP bundle. Use when an admin needs to remotely sign a specific user out of ZCC — for example after a credential reset, lost / decommissioned device, suspected compromise (incident response), or routine offboarding. DO NOT USE WHEN: the admin needs to uninstall ZCC, exit ZCC, revert to a prior ZCC version, or temporarily disable a service (ZIA/ZPA/ZDX/ZDP) on the device — those use other OTPs from the same bundle and warrant their own confirmation flow.

## ZMS — Microsegmentation {#service-zms}

### [`zms-analyze-policy-rules`](https://github.com/zscaler/zscaler-mcp-server/blob/master/skills/zms/analyze-policy-rules/SKILL.md)

Analyze Zscaler Microsegmentation (ZMS) policy rules for optimization opportunities. Reviews custom and default policy rules, identifies stale or unused rules, detects overly permissive rules, maps cross-zone communication patterns, and assesses default security posture. Use when an administrator asks: 'Are there unused policy rules?', 'Which rules are too broad?', 'Optimize our segmentation policies', 'Review our default deny posture', 'Show me policy rule coverage', or 'Analyze our ZMS policies.'

### [`zms-assess-workload-protection`](https://github.com/zscaler/zscaler-mcp-server/blob/master/skills/zms/assess-workload-protection/SKILL.md)

Assess Zscaler Microsegmentation (ZMS) workload protection coverage and identify protection gaps. Investigates resource protection status, resource group membership, unprotected workloads by cloud and region, and resource group coverage gaps. Use when an administrator asks: 'Which workloads are unprotected?', 'What is our microsegmentation coverage?', 'Find protection gaps', 'Which resource groups have no policies?', 'Show me unprotected resources', or 'What is our workload coverage percentage?'

### [`zms-audit-microsegmentation-posture`](https://github.com/zscaler/zscaler-mcp-server/blob/master/skills/zms/audit-microsegmentation-posture/SKILL.md)

Audit the overall Zscaler Microsegmentation (ZMS) deployment posture. Reviews agent fleet health, workload protection coverage, resource group structure, policy rules, app zones, application catalog, and tag-based classification. Use when an administrator asks: 'What is our microsegmentation coverage?', 'How many workloads are protected?', 'Show me our ZMS policies', 'Review our microsegmentation deployment', or 'Audit our ZMS posture.'

### [`zms-review-tag-classification`](https://github.com/zscaler/zscaler-mcp-server/blob/master/skills/zms/review-tag-classification/SKILL.md)

Review Zscaler Microsegmentation (ZMS) tag classification, application discovery, and tag-to-resource-group mapping. Investigates tag namespaces (CUSTOM, EXTERNAL, ML), tag keys and values, application catalog entries, and how tags drive managed resource group membership. Use when an administrator asks: 'Show me our tag structure', 'What cloud tags are imported?', 'How are resource groups using tags?', 'What applications were discovered?', 'Review tag classification', or 'Are ML tags being used?'

### [`zms-troubleshoot-agent-deployment`](https://github.com/zscaler/zscaler-mcp-server/blob/master/skills/zms/troubleshoot-agent-deployment/SKILL.md)

Troubleshoot Zscaler Microsegmentation (ZMS) agent deployment and connectivity issues. Investigates agent fleet health, connection status, version compliance, agent group configuration, provisioning keys, and TOTP secrets. Use when an administrator reports: 'Agents are disconnected', 'Agent enrollment failing', 'How do I provision new agents?', 'Check agent versions', or 'Agent not connecting.'

## Z-Insights {#service-zins}

### [`zins-analyze-web-traffic`](https://github.com/zscaler/zscaler-mcp-server/blob/master/skills/zins/analyze-web-traffic/SKILL.md)

Analyze web traffic patterns using Zscaler Analytics (Z-Insights). Examines traffic distribution by location, protocol breakdown (HTTP vs HTTPS), threat categories, DLP violations, and volume trends over time. Use when an administrator asks: 'Show me web traffic by location', 'What protocols are in use?', 'Are there any DLP violations?', 'What does our traffic look like?', or 'Show traffic trends.'

### [`zins-assess-network-security`](https://github.com/zscaler/zscaler-mcp-server/blob/master/skills/zins/assess-network-security/SKILL.md)

Assess network security posture using Zscaler Analytics (Z-Insights). Analyzes Zero Trust Firewall effectiveness by action distribution (allow/block ratios), location-based firewall activity, network service usage, and firewall rule hit counts. Use when a security team asks: 'How effective is our firewall?', 'What is being blocked?', 'Show firewall activity by location', 'Which network services are in use?', or 'Generate a firewall report.'

### [`zins-audit-shadow-it`](https://github.com/zscaler/zscaler-mcp-server/blob/master/skills/zins/audit-shadow-it/SKILL.md)

Audit shadow IT and SaaS application usage using Zscaler Analytics (Z-Insights). Discovers unsanctioned applications, assesses risk scores, monitors CASB-protected SaaS usage, tracks data transfers to shadow apps, and reviews IoT device inventory. Use when a security team asks: 'What shadow IT apps are being used?', 'Show me unsanctioned SaaS usage', 'What is our SaaS risk exposure?', 'How many IoT devices are on our network?', or 'Generate a shadow IT report.'

### [`zins-investigate-security-incident`](https://github.com/zscaler/zscaler-mcp-server/blob/master/skills/zins/investigate-security-incident/SKILL.md)

Investigate security incidents using Zscaler Z-Insights analytics. Correlates threat categories, cyber incident trends, firewall actions, web traffic patterns, and shadow IT data to build a comprehensive incident timeline. Use when a security analyst asks: 'What threats were detected?', 'Show me incident trends', 'Investigate this security event', or 'What shadow IT is being used?'

## EASM — External Attack Surface {#service-easm}

### [`easm-review-attack-surface`](https://github.com/zscaler/zscaler-mcp-server/blob/master/skills/easm/review-attack-surface/SKILL.md)

Review the organization's external attack surface using Zscaler EASM. Lists organizations, retrieves findings (exposed services, vulnerabilities, misconfigurations), checks for lookalike domains, and generates a prioritized risk summary. Use when a security team asks: 'What is our external exposure?', 'Are there any critical findings?', or 'Check for lookalike domains.'

## Cross-Product {#service-cross-product}

### [`cross-product-troubleshoot-user-connectivity`](https://github.com/zscaler/zscaler-mcp-server/blob/master/skills/cross-product/troubleshoot-user-connectivity/SKILL.md)

Cross-product troubleshooting of user connectivity issues spanning ZPA, ZIA, ZDX, and ZCC. Investigates end-to-end: (1) ZCC client status and enrollment, (2) ZDX digital experience scores and metrics, (3) ZPA application segment and access policy configuration, (4) ZIA URL filtering and SSL inspection policies. Use when an administrator reports 'user cannot access application', 'connectivity issues', or 'application is slow.'
