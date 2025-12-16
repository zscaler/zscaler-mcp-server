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
    zinsights_get_cyber_incidents,
    zinsights_get_cyber_incidents_by_location,
    zinsights_get_cyber_incidents_by_threat_and_app,
    zinsights_get_cyber_incidents_daily,
)

# Firewall Analytics
from .firewall import (
    zinsights_get_firewall_by_action,
    zinsights_get_firewall_by_location,
    zinsights_get_firewall_network_services,
)

# IoT Analytics
from .iot import (
    zinsights_get_iot_device_stats,
)

# SaaS Security / CASB Analytics
from .saas_security import (
    zinsights_get_casb_app_report,
)

# Shadow IT Analytics
from .shadow_it import (
    zinsights_get_shadow_it_apps,
    zinsights_get_shadow_it_summary,
)
from .web_traffic import (
    zinsights_get_threat_class,
    zinsights_get_threat_super_categories,
    zinsights_get_web_protocols,
    zinsights_get_web_traffic_by_location,
    zinsights_get_web_traffic_no_grouping,
)

__all__ = [
    # Web Traffic Analytics
    "zinsights_get_web_traffic_by_location",
    "zinsights_get_web_traffic_no_grouping",
    "zinsights_get_web_protocols",
    "zinsights_get_threat_super_categories",
    "zinsights_get_threat_class",
    # Cyber Security Analytics
    "zinsights_get_cyber_incidents",
    "zinsights_get_cyber_incidents_by_location",
    "zinsights_get_cyber_incidents_daily",
    "zinsights_get_cyber_incidents_by_threat_and_app",
    # Firewall Analytics
    "zinsights_get_firewall_by_action",
    "zinsights_get_firewall_by_location",
    "zinsights_get_firewall_network_services",
    # SaaS Security / CASB Analytics
    "zinsights_get_casb_app_report",
    # Shadow IT Analytics
    "zinsights_get_shadow_it_apps",
    "zinsights_get_shadow_it_summary",
    # IoT Analytics
    "zinsights_get_iot_device_stats",
]
