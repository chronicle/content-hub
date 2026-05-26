"""Change Severity - Change severity of a SOCRadar alarm."""
from __future__ import annotations
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler
from ..core.SOCRadarManager import SOCRadarManager
INTEGRATION_NAME = "SOCRadar"
@output_handler
def main() -> None:
    siemplify = SiemplifyAction()
    siemplify.script_name = "SOCRadar - Change Severity"
    api_root = siemplify.extract_configuration_param(INTEGRATION_NAME, "API Root")
    api_key = siemplify.extract_configuration_param(INTEGRATION_NAME, "API Key")
    company_id = siemplify.extract_configuration_param(INTEGRATION_NAME, "Company ID")
    verify_ssl = siemplify.extract_configuration_param(INTEGRATION_NAME, "Verify SSL", input_type=bool, default_value=True)
    alarm_id = siemplify.extract_action_param("Alarm ID", is_mandatory=True)
    severity = siemplify.extract_action_param("Severity", is_mandatory=True)
    manager = SOCRadarManager(api_root, api_key, company_id, verify_ssl)
    result = manager.change_severity(alarm_id, severity)
    siemplify.result.add_result_json(result)
    siemplify.end(f"Alarm {alarm_id} severity changed to {severity}.", True)
if __name__ == "__main__":
    main()
