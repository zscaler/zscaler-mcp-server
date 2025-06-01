# ZPA Tools
from .tools.zpa.app_segments import app_segment_manager as app_segments_py
from .tools.zpa.get_segments_by_type import app_segments_by_type_manager as app_segments_by_type_py
from .tools.zpa.application_servers import application_server_manager as application_server_py
from .tools.zpa.ba_certificate import ba_certificate_manager as ba_certificates_py
from .tools.zpa.segment_groups import segment_group_manager as segment_groups_py
from .tools.zpa.server_groups import server_group_manager as server_groups_py
from .tools.zpa.app_connector_groups import connector_group_manager as app_connector_groups_py
from .tools.zpa.service_edge_groups import service_edge_group_manager as service_edge_groups_py
from .tools.zpa.access_policy_rules import access_policy_manager as access_policy_py
from .tools.zpa.access_forwarding_rules import forwarding_policy_manager as forwarding_policy_py
from .tools.zpa.access_timeout_rules import timeout_policy_manager as timeout_policy_py
from .tools.zpa.access_isolation_rules import isolation_policy_manager as isolation_policy_py
from .tools.zpa.get_isolation_profile import isolation_profile_manager as isolation_profile_py
from .tools.zpa.get_app_protection_profile import app_protection_profile_manager as app_protection_profile_py
from .tools.zpa.get_enrollment_certificate import enrollment_certificate_manager as enrollment_certificate_py
from .tools.zpa.provisioning_key import provisioning_key_manager as provisioning_key_py
from .tools.zpa.pra_portal import pra_portal_manager as pra_portal_py
from .tools.zpa.pra_credential import pra_credential_manager as pra_credential_py
from .tools.zpa.get_scim_groups import scim_group_manager as scim_group_py
from .tools.zpa.get_scim_attributes import scim_attribute_manager as scim_attribute_py
from .tools.zpa.get_saml_attributes import saml_attribute_manager as saml_attribute_py
from .tools.zpa.get_trusted_networks import trusted_network_manager as trusted_network_py
from .tools.zpa.get_posture_profiles import posture_profile_manager as posture_profile_py

# ZIA Tools
from .tools.zia.activation import zia_activation_manager as zia_activation_py
from .tools.zia.rule_labels import rule_label_manager as rule_labels_py
from .tools.zia.vpn_credentials import vpn_credential_manager as vpn_credentials_py
from .tools.zia.static_ips import static_ip_manager as static_ip_py
from .tools.zia.gre_tunnels import gre_tunnel_manager as gre_tunnel_py
from .tools.zia.gre_ranges import gre_range_discovery_manager as gre_range_discovery_py
from .tools.zia.get_sandbox_info import sandbox_manager as sandbox_py
from .tools.zia.sandbox_file_submit import sandbox_file_submit as sandbox_file_submit_py

def register_all_tools(app):
    # ZPA Tools
    app.tool(name="zpa_application_segments")(app_segments_py)
    app.tool(name="zpa_app_segments_by_type")(app_segments_by_type_py)
    app.tool(name="zpa_application_servers")(application_server_py)
    app.tool(name="zpa_ba_certificates")(ba_certificates_py)
    app.tool(name="zpa_segment_groups")(segment_groups_py)
    app.tool(name="zpa_server_groups")(server_groups_py)
    app.tool(name="zpa_app_connector_groups")(app_connector_groups_py)
    app.tool(name="zpa_service_edge_groups")(service_edge_groups_py)
    app.tool(name="zpa_access_policy")(access_policy_py)
    app.tool(name="zpa_forwarding_policy")(forwarding_policy_py)
    app.tool(name="zpa_timeout_policy")(timeout_policy_py)
    app.tool(name="zpa_isolation_policy")(isolation_policy_py)
    app.tool(name="zpa_isolation_profile")(isolation_profile_py)
    app.tool(name="zpa_app_protection_profiles")(app_protection_profile_py)
    app.tool(name="zpa_enrollment_certificates")(enrollment_certificate_py)
    app.tool(name="zpa_provisioning_key")(provisioning_key_py)
    app.tool(name="zpa_pra_portals")(pra_portal_py)
    app.tool(name="zpa_pra_credentials")(pra_credential_py)
    app.tool(name="zpa_scim_groups")(scim_group_py)
    app.tool(name="zpa_scim_attributes")(scim_attribute_py)
    app.tool(name="zpa_saml_attributes")(saml_attribute_py)
    app.tool(name="zpa_trusted_networks")(trusted_network_py)
    app.tool(name="zpa_posture_profiles")(posture_profile_py)

    # ZIA Tools
    app.tool(name="zia_zia_activation")(zia_activation_py)
    app.tool(name="zia_rule_labels")(rule_labels_py)
    app.tool(name="zia_vpn_credentials")(vpn_credentials_py)
    app.tool(name="zia_static_ips")(static_ip_py)
    app.tool(name="zia_gre_tunnels")(gre_tunnel_py)
    app.tool(name="zia_gre_range_discovery")(gre_range_discovery_py)
    app.tool(name="zia_sandbox")(sandbox_py)
    app.tool(name="sandbox_file_submit")(sandbox_file_submit_py)
