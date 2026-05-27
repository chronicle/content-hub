"""Ping - Test SOCRadar API connectivity."""
from __future__ import annotations
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler
from ..core.SOCRadarManager import SOCRadarManager
INTEGRATION_NAME = "SOCRadar"
@output_handler
def main() -> None:
    siemplify = SiemplifyAction()
    siemplify.script_name = "SOCRadar - Ping"
    api_root = siemplify.extract_configuration_param(INTEGRATION_NAME, "API Root")
    api_key = siemplify.extract_configuration_param(INTEGRATION_NAME, "API Key")
    company_id = siemplify.extract_configuration_param(INTEGRATION_NAME, "Company ID")
    verify_ssl = siemplify.extract_configuration_param(INTEGRATION_NAME, "Verify SSL", input_type=bool, default_value=True)
    try:
        manager = SOCRadarManager(api_root, api_key, company_id, verify_ssl)
        manager.test_connectivity()
        siemplify.end("Successfully connected to the SOCRadar CTI server with the provided connection parameters!", True)
    except Exception as e:
        siemplify.end(f"Failed to connect to the SOCRadar CTI server! Error is {e}", False)
if __name__ == "__main__":
    main()
