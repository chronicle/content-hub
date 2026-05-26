"""Add Comment - Add a comment to a SOCRadar alarm."""
from __future__ import annotations
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler
from ..core.SOCRadarManager import SOCRadarManager
INTEGRATION_NAME = "SOCRadar"
@output_handler
def main() -> None:
    siemplify = SiemplifyAction()
    siemplify.script_name = "SOCRadar - Add Comment"
    api_root = siemplify.extract_configuration_param(INTEGRATION_NAME, "API Root")
    api_key = siemplify.extract_configuration_param(INTEGRATION_NAME, "API Key")
    company_id = siemplify.extract_configuration_param(INTEGRATION_NAME, "Company ID")
    verify_ssl = siemplify.extract_configuration_param(INTEGRATION_NAME, "Verify SSL", input_type=bool, default_value=True)
    alarm_id = siemplify.extract_action_param("Alarm ID", is_mandatory=True)
    comment = siemplify.extract_action_param("Comment", is_mandatory=True)
    user_email = siemplify.extract_action_param("User Email", default_value="")
    try:
        manager = SOCRadarManager(api_root, api_key, company_id, verify_ssl)
        result = manager.add_comment(alarm_id, comment, user_email)
        siemplify.result.add_result_json(result)
        siemplify.end(f"Comment added to alarm {alarm_id}.", True)
    except Exception as e:
        siemplify.end(f'Error executing action "Add Comment". Reason: {e}', False)

if __name__ == "__main__":
    main()
