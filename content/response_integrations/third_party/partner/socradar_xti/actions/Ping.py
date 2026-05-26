"""Ping - Test SOCRadar API connectivity."""
from SiemplifyAction import SiemplifyAction
from SiemplifyUtils import output_handler
from SOCRadarManager import SOCRadarManager
INTEGRATION_NAME = "SOCRadar"
@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = "SOCRadar - Ping"
    api_root = siemplify.extract_configuration_param(INTEGRATION_NAME, "API Root")
    api_key = siemplify.extract_configuration_param(INTEGRATION_NAME, "API Key")
    company_id = siemplify.extract_configuration_param(INTEGRATION_NAME, "Company ID")
    verify_ssl = siemplify.extract_configuration_param(INTEGRATION_NAME, "Verify SSL", input_type=bool, default_value=True)
    manager = SOCRadarManager(api_root, api_key, company_id, verify_ssl)
    manager.test_connectivity()
    siemplify.end("Successfully connected to SOCRadar API.", True)
if __name__ == "__main__":
    main()
