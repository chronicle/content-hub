from __future__ import annotations
import sys

from ..core.APIManager import APIManager
from EnvironmentCommon import GetEnvironmentCommonFactory
from soar_sdk.SiemplifyConnectors import SiemplifyConnectorExecution
from soar_sdk.SiemplifyConnectorsDataModel import AlertInfo
from soar_sdk.SiemplifyUtils import output_handler, unix_now
from TIPCommon import (
    extract_connector_param,
    read_ids,
    write_ids,
    is_overflowed,
    is_approaching_timeout,
)
from ..core.constants import (
    ALLOWED_STATUS_VALUES,
    ALLOWED_PRIORITY_VALUES,
    SOC_INSIGHTS_CONNECTOR_NAME,
)
from ..core.utils import validate_enum

# ==============================================================================
# This connector retrieves SOC Insights from Infoblox Cloud and creates alerts in
# Google SecOps SOAR. Each SOC Insight will generate an alert/case.
# ==============================================================================

connector_starting_time = unix_now()


def validate_input_params(status, priority):
    """
    Validate input parameters for the connector.

    Args:
        status (str): Filter insights by status (e.g., "Active", "Closed")
        priority (str): Filter insights by priority level

    Returns:
        tuple: Validated parameters
    """

    # Validate status using validate_enum with case-insensitive matching
    if status:
        status_title_case = status.title()
        status = validate_enum(status_title_case, ALLOWED_STATUS_VALUES, "Status")

    # Validate priority using validate_enum with case-insensitive matching
    if priority:
        priority_upper = priority.upper()
        priority = validate_enum(priority_upper, ALLOWED_PRIORITY_VALUES, "Priority")

    return status, priority


@output_handler
def main(is_test_run):
    siemplify = SiemplifyConnectorExecution()
    siemplify.script_name = SOC_INSIGHTS_CONNECTOR_NAME

    siemplify.LOGGER.info("==================== Main - Param Init ====================")

    # Configuration Parameters
    api_root = extract_connector_param(
        siemplify, param_name="API Root", input_type=str, is_mandatory=True, print_value=True
    )
    api_key = extract_connector_param(
        siemplify,
        param_name="API Key",
        input_type=str,
        is_mandatory=True,
        print_value=False,
        remove_whitespaces=False,
    )
    verify_ssl = extract_connector_param(
        siemplify,
        param_name="Verify SSL",
        default_value=True,
        input_type=bool,
        is_mandatory=True,
        print_value=True,
    )

    # Filter Parameters
    status = extract_connector_param(
        siemplify, param_name="Status", input_type=str, is_mandatory=False, print_value=True
    )
    threat_type = extract_connector_param(
        siemplify, param_name="Threat Type", input_type=str, is_mandatory=False, print_value=True
    )
    priority = extract_connector_param(
        siemplify, param_name="Priority", input_type=str, is_mandatory=False, print_value=True
    )

    # Environment Parameters
    environment_field_name = extract_connector_param(
        siemplify,
        param_name="Environment Field Name",
        default_value="Default Environment",
        input_type=str,
        print_value=True,
    )
    environment_regex_pattern = extract_connector_param(
        siemplify, param_name="Environment Regex Pattern", input_type=str, print_value=True
    )

    python_process_timeout = extract_connector_param(
        siemplify,
        param_name="PythonProcessTimeout",
        input_type=int,
        is_mandatory=True,
        print_value=True,
    )
    device_product_field = extract_connector_param(
        siemplify, "DeviceProductField", is_mandatory=True
    )

    siemplify.LOGGER.info("------------------- Main - Started -------------------")
    try:

        status, priority = validate_input_params(status, priority)

        # Read existing insight IDs for deduplication
        siemplify.LOGGER.info("Reading existing insight IDs...")
        existing_ids = read_ids(siemplify)

        # Instantiate API manager
        manager = APIManager(api_root, api_key, verify_ssl=verify_ssl, siemplify=siemplify)

        # Fetch SOC Insights
        insights = manager.get_soc_insights(
            existing_ids=existing_ids, status=status, threat_type=threat_type, priority=priority
        )

        if is_test_run:
            insights = insights[:1]

        siemplify.LOGGER.info(f"Found {len(insights)} SOC Insights.")

        alerts = []

        # Process each insight
        for soc_insight in insights:
            siemplify.LOGGER.info(f"Started processing insight {soc_insight.insight_id}")
            try:
                # Check for timeout
                if is_approaching_timeout(connector_starting_time, python_process_timeout):
                    siemplify.LOGGER.info("Timeout is approaching. Connector will gracefully exit")
                    break

                # Create environment manager
                environment_common = GetEnvironmentCommonFactory.create_environment_manager(
                    siemplify, environment_field_name, environment_regex_pattern
                )

                # Convert insight to AlertInfo using the datamodel method
                alert_info = soc_insight.get_alert_info(
                    AlertInfo(), environment_common, device_product_field
                )

                # Update existing ids
                existing_ids.append(alert_info.ticket_id)

                # Check for case overflow
                if is_overflowed(siemplify, alert_info, is_test_run):
                    siemplify.LOGGER.info(
                        f"{str(alert_info.rule_generator)}-{str(alert_info.ticket_id)}"
                        f"-{str(alert_info.environment)}"
                        f"-{str(alert_info.device_product)}"
                        " found as overflow alert. Skipping."
                    )
                    # If is overflowed we should skip
                    continue

                # Add to alerts list
                alerts.append(alert_info)

                siemplify.LOGGER.info(f"Alert {soc_insight.insight_id} was created.")

            except Exception as e:
                siemplify.LOGGER.error(
                    f"Failed to process insight {soc_insight.insight_id}. "
                    "Any further insights will not be processed"
                )
                siemplify.LOGGER.exception(e)
                if is_test_run:
                    raise
                break

        # Write all IDs for deduplication
        if not is_test_run:
            write_ids(siemplify, existing_ids)

    except Exception as e:
        siemplify.LOGGER.error(f"Got exception on main handler. Error: {e}")
        siemplify.LOGGER.exception(e)

        if is_test_run:
            raise

    siemplify.LOGGER.info(f"Created total of {len(alerts)} alerts")
    siemplify.LOGGER.info("------------------- Main - Finished -------------------")
    siemplify.return_package(alerts)


if __name__ == "__main__":
    # Connectors are run in iterations. The interval is configurable from the ConnectorsScreen UI.
    is_test_run = not (len(sys.argv) < 2 or sys.argv[1] == "True")
    main(is_test_run)
