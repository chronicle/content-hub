"""Remove Tag - Remove a tag from a SOCRadar alarm."""
from __future__ import annotations
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler
from ..core.SOCRadarManager import SOCRadarManager
INTEGRATION_NAME = "SOCRadar"
@output_handler
def main() -> None:
    siemplify = SiemplifyAction()
    siemplify.script_name = "SOCRadar - Remove Tag"
    api_root = siemplify.extract_configuration_param(INTEGRATION_NAME, "API Root")
    api_key = siemplify.extract_configuration_param(INTEGRATION_NAME, "API Key")
    company_id = siemplify.extract_configuration_param(INTEGRATION_NAME, "Company ID")
    verify_ssl = siemplify.extract_configuration_param(INTEGRATION_NAME, "Verify SSL", input_type=bool, default_value=True)
    alarm_id = siemplify.extract_action_param("Alarm ID", is_mandatory=True)
    tag = siemplify.extract_action_param("Tag", is_mandatory=True)
    manager = SOCRadarManager(api_root, api_key, company_id, verify_ssl)
    result = manager.remove_tag(alarm_id, tag)
    siemplify.result.add_result_json(result)
    siemplify.end(f"Tag '{tag}' removed from alarm {alarm_id}.", True)
if __name__ == "__main__":
    main()
