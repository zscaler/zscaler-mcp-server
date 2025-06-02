# ZCC Tools
from .tools.zcc.list_devices import zcc_devices_manager as zcc_list_devices
from .tools.zcc.download_devices import zcc_devices_csv_exporter as zcc_devices_csv_exporter

# ZPA Tools
from .tools.zpa.app_segments import app_segment_manager as app_segments
from .tools.zpa.get_segments_by_type import app_segments_by_type_manager as app_segments_by_type
from .tools.zpa.application_servers import application_server_manager as application_server
from .tools.zpa.ba_certificate import ba_certificate_manager as ba_certificates
from .tools.zpa.segment_groups import segment_group_manager as segment_groups
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
from .tools.zia.cloud_firewall_rules import zia_firewall_rule_manager as cloud_firewall_rule
from .tools.zia.ip_source_groups import zia_ip_source_group_manager as ip_source_groups
from .tools.zia.ip_destination_groups import zia_ip_destination_group_manager as ip_destination_groups
from .tools.zia.network_app_groups import zia_network_app_group_manager as network_app_group
from .tools.zia.vpn_credentials import vpn_credential_manager as vpn_credentials
from .tools.zia.static_ips import static_ip_manager as static_ip
from .tools.zia.gre_tunnels import gre_tunnel_manager as gre_tunnel
from .tools.zia.gre_ranges import gre_range_discovery_manager as gre_range_discovery
from .tools.zia.get_sandbox_info import sandbox_manager as sandbox
from .tools.zia.sandbox_file_submit import sandbox_file_submit as sandbox_file_submit

def register_all_tools(app):
    # ZCC Tools
    app.tool(name="zcc_list_devices")(zcc_list_devices)
    app.tool(name="zcc_devices_csv_exporter")(zcc_devices_csv_exporter)

    # ZPA Tools
    app.tool(name="zpa_application_segments")(app_segments)
    app.tool(name="zpa_app_segments_by_type")(app_segments_by_type)
    app.tool(name="zpa_application_servers")(application_server)
    app.tool(name="zpa_ba_certificates")(ba_certificates)
    app.tool(name="zpa_segment_groups")(segment_groups)
    app.tool(name="zpa_server_groups")(server_groups)
    app.tool(name="zpa_app_connector_groups")(app_connector_groups)
    app.tool(name="zpa_service_edge_groups")(service_edge_groups)
    app.tool(name="zpa_access_policy")(access_policy)
    app.tool(name="zpa_forwarding_policy")(forwarding_policy)
    app.tool(name="zpa_timeout_policy")(timeout_policy)
    app.tool(name="zpa_isolation_policy")(isolation_policy)
    app.tool(name="zpa_isolation_profile")(isolation_profile)
    app.tool(name="zpa_app_protection_profiles")(app_protection_profile)
    app.tool(name="zpa_enrollment_certificates")(enrollment_certificate)
    app.tool(name="zpa_provisioning_key")(provisioning_key)
    app.tool(name="zpa_pra_portals")(pra_portal)
    app.tool(name="zpa_pra_credentials")(pra_credential)
    app.tool(name="zpa_scim_groups")(scim_group)
    app.tool(name="zpa_scim_attributes")(scim_attribute)
    app.tool(name="zpa_saml_attributes")(saml_attribute)
    app.tool(name="zpa_trusted_networks")(trusted_network)
    app.tool(name="zpa_posture_profiles")(posture_profile)

    # ZIA Tools
    app.tool(name="zia_activation")(zia_activation)
    app.tool(name="zia_atp_malicious_urls")(atp_malicious_urls)
    app.tool(name="zia_auth_exempt_urls")(auth_exempt_urls)
    app.tool(name="zia_rule_labels")(rule_labels)
    app.tool(name="zia_cloud_firewall_rule")(cloud_firewall_rule)
    app.tool(name="zia_ip_source_group")(ip_source_groups)
    app.tool(name="zia_ip_destination_groups")(ip_destination_groups)
    app.tool(name="zia_network_app_group")(network_app_group)
    app.tool(name="zia_vpn_credentials")(vpn_credentials)
    app.tool(name="zia_static_ips")(static_ip)
    app.tool(name="zia_gre_tunnels")(gre_tunnel)
    app.tool(name="zia_gre_range_discovery")(gre_range_discovery)
    app.tool(name="zia_sandbox")(sandbox)
    app.tool(name="zia_sandbox_file_submit")(sandbox_file_submit)
