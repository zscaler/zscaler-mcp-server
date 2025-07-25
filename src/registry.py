# ZCC Tools
from .tools.zcc.list_devices import zcc_devices_v1_manager as zcc_devices_v1_manager
from .tools.zcc.download_devices import zcc_devices_csv_exporter as zcc_devices_csv_exporter

# ZDX Tools
from .tools.zdx.administration import zdx_admin_discovery_tool as administration
from .tools.zdx.active_devices import zdx_device_discovery_tool as active_devices

# ZPA Tools
from .tools.zpa.app_segments import app_segment_manager as app_segments
from .tools.zpa.get_segments_by_type import app_segments_by_type_manager as app_segments_by_type
from .tools.zpa.application_servers import application_server_v2_manager as application_server_v2_manager
from .tools.zpa.ba_certificate import ba_certificate_manager as ba_certificates
from .tools.zpa.segment_groups import segment_group_v6_manager as segment_group_v6_manager
from .tools.zpa.server_groups import server_group_manager as server_groups
from .tools.zpa.app_connector_groups import connector_group_manager as app_connector_groups
from .tools.zpa.service_edge_groups import service_edge_group_manager as service_edge_groups
from .tools.zpa.access_policy_rules import access_policy_manager as access_policy
from .tools.zpa.access_forwarding_rules import forwarding_policy_manager as forwarding_policy
from .tools.zpa.access_timeout_rules import timeout_policy_manager as timeout_policy
from .tools.zpa.access_isolation_rules import isolation_policy_manager as isolation_policy
from .tools.zpa.get_isolation_profile import isolation_profile_manager as isolation_profile
from .tools.zpa.get_app_protection_profile import app_protection_profile_manager as app_protection_profile
from .tools.zpa.get_enrollment_certificate import enrollment_certificate_manager as enrollment_certificate
from .tools.zpa.provisioning_key import provisioning_key_manager as provisioning_key
from .tools.zpa.pra_portal import pra_portal_manager as pra_portal
from .tools.zpa.pra_credential import pra_credential_manager as pra_credential
from .tools.zpa.get_scim_groups import scim_group_manager as scim_group
from .tools.zpa.get_scim_attributes import scim_attribute_manager as scim_attribute
from .tools.zpa.get_saml_attributes import saml_attribute_manager as saml_attribute
from .tools.zpa.get_trusted_networks import trusted_network_manager as trusted_network
from .tools.zpa.get_posture_profiles import posture_profile_manager as posture_profile

# ZIA Tools
from .tools.zia.activation import zia_activation_manager as zia_activation
from .tools.zia.atp_malicious_urls import zia_atp_malicious_urls_manager as atp_malicious_urls
from .tools.zia.auth_exempt_urls import zia_auth_exempt_urls_manager as auth_exempt_urls
from .tools.zia.rule_labels import rule_label_manager as rule_labels
from .tools.zia.url_categories import url_category_manager as url_categories
from .tools.zia.cloud_firewall_rules import zia_firewall_rule_manager as cloud_firewall_rule
from .tools.zia.ip_source_groups import zia_ip_source_group_manager as ip_source_groups
from .tools.zia.ip_destination_groups import zia_ip_destination_group_manager as ip_destination_groups
from .tools.zia.network_app_groups import zia_network_app_group_manager as network_app_group
from .tools.zia.location_management import zia_locations_manager as location_management
from .tools.zia.vpn_credentials import vpn_credential_manager as vpn_credentials
from .tools.zia.static_ips import static_ip_manager as static_ip
from .tools.zia.gre_tunnels import gre_tunnel_manager as gre_tunnel
from .tools.zia.gre_ranges import gre_range_discovery_manager as gre_range_discovery
from .tools.zia.geo_search import zia_geo_search_tool as geo_search
from .tools.zia.get_sandbox_info import sandbox_manager as sandbox

def register_all_tools(app):
    # All tools are automatically registered via @app.tool decorators
    # when their modules are imported above
    pass
