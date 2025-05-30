from .tools.zpa.python.app_segments import app_segment_manager as app_segments_py
from .tools.zpa.python.segment_groups import segment_group_manager as segment_groups_py
from .tools.zpa.python.server_groups import server_group_manager as server_groups_py
from .tools.zpa.python.app_connector_groups import connector_group_manager as app_connector_groups_py
from .tools.zpa.python.service_edge_groups import service_edge_group_manager as service_edge_groups_py
from .tools.zpa.python.access_policy import access_policy_manager as access_policy_py
from .tools.zpa.python.access_forwarding_rule import forwarding_policy_manager as forwarding_policy_py
from .tools.zpa.python.access_timeout_rule import timeout_policy_manager as timeout_policy_py
from .tools.zpa.python.access_isolation_rule import isolation_policy_manager as isolation_policy_py
from .tools.zia.python.get_rule_labels import get_rule_labels as get_rule_labels_py
# from .tools.zpa.golang.get_app_segments import get_app_segments as get_app_segments_go

def register_all_tools(app):
    app.tool(name="app_segments_python")(app_segments_py)
    app.tool(name="segment_groups_python")(segment_groups_py)
    app.tool(name="server_groups_python")(server_groups_py)
    app.tool(name="app_connector_groups_python")(app_connector_groups_py)
    app.tool(name="service_edge_groups_python")(service_edge_groups_py)
    app.tool(name="access_policy_python")(access_policy_py)
    app.tool(name="forwarding_policy_python")(forwarding_policy_py)
    app.tool(name="timeout_policy_python")(timeout_policy_py)
    app.tool(name="isolation_policy_python")(isolation_policy_py)
    app.tool(name="get_rule_labels_py")(get_rule_labels_py)
    # app.tool(name="get_app_segments_go")(get_app_segments_go)