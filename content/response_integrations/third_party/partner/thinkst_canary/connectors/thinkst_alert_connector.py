# ==============================================================================
# This connector retrieves Incidents from a Thinkst Canary Console and creates
# alerts/cases in Google SecOps SOAR. Each Canary Incident generates one alert.
# ==============================================================================
import sys

from soar_sdk.SiemplifyConnectors import SiemplifyConnectorExecution
from soar_sdk.SiemplifyUtils import output_handler

from ..core.constants import (
    THINKST_CONNECTOR_NAME,
    THINKST_DEFAULT_API_KEY,
    THINKST_DEFAULT_CONSOLE,
)
from ..core.thinkst_manager import ThinkstConnectorManager, str_to_bool


@output_handler
def main(is_test_run):
    alerts = []
    siemplify = SiemplifyConnectorExecution()
    siemplify.script_name = THINKST_CONNECTOR_NAME

    if is_test_run:
        siemplify.LOGGER.info(
            '***** This is an "IDE Play Button"\\"Run Connector once" test run ******'
        )

    siemplify.LOGGER.info("==================== Main - Param Init ====================")

    console_api_key = siemplify.extract_connector_param("API Key", THINKST_DEFAULT_API_KEY)
    if console_api_key == THINKST_DEFAULT_API_KEY:
        siemplify.LOGGER.error("Please provide a valid API Key")
        return

    console_hash = siemplify.extract_connector_param("Console Hash", THINKST_DEFAULT_CONSOLE)
    if console_hash == THINKST_DEFAULT_CONSOLE:
        siemplify.LOGGER.error("Please provide a valid Console Hash")
        return

    ssl_verify = siemplify.extract_connector_param("Verify SSL")
    ssl = str_to_bool(ssl_verify)

    manager = ThinkstConnectorManager(console_api_key, console_hash, siemplify, ssl)
    alerts = manager.fetch_alerts()
    siemplify.return_package(alerts)


if __name__ == "__main__":
    # Connectors are run in iterations. The interval is configurable from the ConnectorsScreen UI.
    is_test_run = not (len(sys.argv) < 2 or sys.argv[1] == "True")
    main(is_test_run)
