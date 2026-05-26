"""Change Assignee - Assign users to a SOCRadar alarm."""
from __future__ import annotations
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler
from ..core.SOCRadarManager import SOCRadarManager
INTEGRATION_NAME = "SOCRadar"
@output_handler
def main() -> None:
    siemplify = SiemplifyAction()
    siemplify.script_name = "SOCRadar - Change Assignee"
    api_root = siemplify.extract_configuration_param(INTEGRATION_NAME, "API Root")
    api_key = siemplify.extract_configuration_param(INTEGRATION_NAME, "API Key")
    company_id = siemplify.extract_configuration_param(INTEGRATION_NAME, "Company ID")
    verify_ssl = siemplify.extract_configuration_param(INTEGRATION_NAME, "Verify SSL", input_type=bool, default_value=True)
    alarm_id = siemplify.extract_action_param("Alarm ID", is_mandatory=True)
    user_emails_str = siemplify.extract_action_param("User Emails", default_value="")
    user_ids_str = siemplify.extract_action_param("User IDs", default_value="")
    user_emails = [e.strip() for e in user_emails_str.split(",") if e.strip()] or None
    user_ids = [int(i.strip()) for i in user_ids_str.split(",") if i.strip().isdigit()] or None
    try:
        manager = SOCRadarManager(api_root, api_key, company_id, verify_ssl)
        result = manager.change_assignee(alarm_id, user_ids=user_ids, user_emails=user_emails)
        siemplify.result.add_result_json(result)
        siemplify.end(f"Assignee updated for alarm {alarm_id}.", True)
    except Exception as e:
        siemplify.end(f'Error executing action "Change Assignee". Reason: {e}', False)

if __name__ == "__main__":
    main()
