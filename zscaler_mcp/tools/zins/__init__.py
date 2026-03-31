"""
Z-Insights Analytics Tools

Provides analytics and reporting capabilities through the Z-Insights GraphQL API.
All tools in this module are read-only operations.

Available domains in Z-Insights API:
- WEB_TRAFFIC: Web traffic analytics and threat data
- CYBER_SECURITY: Cybersecurity incidents and threat analysis
- ZERO_TRUST_FIREWALL: Firewall activity and rule analytics
- SAAS_SECURITY: Cloud Access Security Broker (CASB) data
- SHADOW_IT: Unsanctioned application discovery
- IOT: IoT device visibility and statistics
"""

# Web Traffic Analytics
# Cyber Security Analytics
from .cyber_security import (
    zins_get_cyber_incidents,
    zins_get_cyber_incidents_by_location,
    zins_get_cyber_incidents_by_threat_and_app,
    zins_get_cyber_incidents_daily,
)

# Firewall Analytics
from .firewall import (
    zins_get_firewall_by_action,
    zins_get_firewall_by_location,
    zins_get_firewall_network_services,
)

# IoT Analytics
from .iot import (
    zins_get_iot_device_stats,
)

# SaaS Security / CASB Analytics
from .saas_security import (
    zins_get_casb_app_report,
)

# Shadow IT Analytics
from .shadow_it import (
    zins_get_shadow_it_apps,
    zins_get_shadow_it_summary,
)
from .web_traffic import (
    zins_get_threat_class,
    zins_get_threat_super_categories,
    zins_get_web_protocols,
    zins_get_web_traffic_by_location,
    zins_get_web_traffic_no_grouping,
)

__all__ = [
    # Web Traffic Analytics
    "zins_get_web_traffic_by_location",
    "zins_get_web_traffic_no_grouping",
    "zins_get_web_protocols",
    "zins_get_threat_super_categories",
    "zins_get_threat_class",
    # Cyber Security Analytics
    "zins_get_cyber_incidents",
    "zins_get_cyber_incidents_by_location",
    "zins_get_cyber_incidents_daily",
    "zins_get_cyber_incidents_by_threat_and_app",
    # Firewall Analytics
    "zins_get_firewall_by_action",
    "zins_get_firewall_by_location",
    "zins_get_firewall_network_services",
    # SaaS Security / CASB Analytics
    "zins_get_casb_app_report",
    # Shadow IT Analytics
    "zins_get_shadow_it_apps",
    "zins_get_shadow_it_summary",
    # IoT Analytics
    "zins_get_iot_device_stats",
]
