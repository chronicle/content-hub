"""Get Alarm Details - Fetch full details of a single alarm."""
from SiemplifyAction import SiemplifyAction
from SiemplifyUtils import output_handler
from SOCRadarManager import SOCRadarManager
INTEGRATION_NAME = "SOCRadar"
@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = "SOCRadar - Get Alarm Details"
    api_root = siemplify.extract_configuration_param(INTEGRATION_NAME, "API Root")
    api_key = siemplify.extract_configuration_param(INTEGRATION_NAME, "API Key")
    company_id = siemplify.extract_configuration_param(INTEGRATION_NAME, "Company ID")
    verify_ssl = siemplify.extract_configuration_param(INTEGRATION_NAME, "Verify SSL", input_type=bool, default_value=True)
    alarm_id = siemplify.extract_action_param("Alarm ID", is_mandatory=True)
    manager = SOCRadarManager(api_root, api_key, company_id, verify_ssl)
    result = manager.get_alarm_details(alarm_id)
    siemplify.result.add_result_json(result)
    title = result.get("alarm_type_details", {}).get("alarm_generic_title", alarm_id)
    siemplify.end(f"Retrieved details for alarm: {title}", True)
if __name__ == "__main__":
    main()
