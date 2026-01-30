from __future__ import annotations
import sys

from greynoise.exceptions import RateLimitError, RequestFailure
from soar_sdk.SiemplifyConnectors import SiemplifyConnectorExecution
from soar_sdk.SiemplifyConnectorsDataModel import AlertInfo
from soar_sdk.SiemplifyUtils import output_handler, unix_now
from TIPCommon.smp_io import read_ids, write_ids
from TIPCommon.smp_time import is_approaching_timeout
from TIPCommon.utils import is_overflowed
from TIPCommon.extraction import extract_connector_param
from EnvironmentCommon import GetEnvironmentCommonFactory
from ..core.api_manager import APIManager
from ..core.constants import (
    GNQL_CONNECTOR_NAME,
    GNQL_PAGE_SIZE,
    MAX_CONNECTOR_RESULTS,
    TEST_MODE_MAX_RESULTS,
)
from ..core.utils import validate_integer_param

# ==============================================================================
# This connector retrieves threat intelligence data from GreyNoise using GNQL
# queries and creates alerts in Google SecOps SOAR. Each matching IP from the
# query will generate an alert/case.
# ==============================================================================

connector_starting_time = unix_now()


@output_handler
def main(is_test_run):
    siemplify = SiemplifyConnectorExecution()
    siemplify.script_name = GNQL_CONNECTOR_NAME

    if is_test_run:
        siemplify.LOGGER.info(
            '***** This is an "IDE Play Button Run Connector once" test run ******'
        )

    siemplify.LOGGER.info("==================== Main - Param Init ====================")

    # Configuration Parameters
    api_key = extract_connector_param(
        siemplify,
        param_name="GN API Key",
        input_type=str,
        is_mandatory=True,
        print_value=False,
    )

    # Query Parameters
    query = extract_connector_param(
        siemplify,
        param_name="Query",
        input_type=str,
        is_mandatory=False,
        print_value=True,
    )

    max_results = extract_connector_param(
        siemplify,
        param_name="Max Results",
        default_value=MAX_CONNECTOR_RESULTS,
        input_type=int,
        is_mandatory=False,
        print_value=True,
    )

    # Environment Parameters
    environment_field_name = extract_connector_param(
        siemplify,
        param_name="Environment Field Name",
        default_value="",
        input_type=str,
        print_value=True,
    )
    environment_regex_pattern = extract_connector_param(
        siemplify,
        param_name="Environment Regex Pattern",
        input_type=str,
        print_value=True,
    )

    # Timeout Parameters
    python_process_timeout = extract_connector_param(
        siemplify,
        param_name="PythonProcessTimeout",
        input_type=int,
        is_mandatory=True,
        print_value=False,
    )

    device_product_field = extract_connector_param(
        siemplify,
        param_name="DeviceProductField",
        is_mandatory=False,
        print_value=True,
    )

    siemplify.LOGGER.info("------------------- Main - Started -------------------")

    # Initialize alerts list
    alerts = []

    try:
        # Read existing event IDs for deduplication
        siemplify.LOGGER.info("Reading existing event IDs...")
        existing_ids = read_ids(siemplify)

        if is_test_run:
            siemplify.LOGGER.info(
                f"This is a TEST run. Only {TEST_MODE_MAX_RESULTS} alerts will be processed."
            )
            max_results = TEST_MODE_MAX_RESULTS
        # Set default query if not provided
        if not query or not query.strip():
            query = "last_seen:1d"
            siemplify.LOGGER.info(f"No query provided, using default: {query}")

        # Instantiate API manager
        manager = APIManager(api_key, siemplify=siemplify)

        # Fetch GNQL events
        gnql_events = manager.get_gnql_events(
            query=query,
            page_size=GNQL_PAGE_SIZE,
            existing_ids=existing_ids,
            connector_start_time=connector_starting_time,
            timeout=python_process_timeout,
            max_results=max_results,
        )

        siemplify.LOGGER.info(f"Found {len(gnql_events)} new GNQL events to process.")

        # Process each event
        for gnql_event in gnql_events:
            siemplify.LOGGER.info(f"Started processing GNQL event: {gnql_event.event_id}")
            try:
                # Check for timeout
                if is_approaching_timeout(connector_starting_time, python_process_timeout):
                    siemplify.LOGGER.info("Timeout is approaching. Connector will gracefully exit")
                    break

                # Create environment manager
                environment_common = GetEnvironmentCommonFactory.create_environment_manager(
                    siemplify,
                    environment_field_name,
                    environment_regex_pattern,
                )

                # Convert event to AlertInfo using the datamodel method
                alert_info = gnql_event.get_alert_info(
                    AlertInfo(), environment_common, device_product_field
                )

                # Update existing IDs
                existing_ids.append(alert_info.ticket_id)

                if is_overflowed(siemplify, alert_info, is_test_run):
                    siemplify.LOGGER.info(
                        f"{str(alert_info.rule_generator)}-"
                        f"{str(alert_info.ticket_id)}-"
                        f"{str(alert_info.environment)}-"
                        f"{str(alert_info.device_product)}"
                        " found as overflow alert. Skipping."
                    )
                    continue

                # Add to alerts list
                alerts.append(alert_info)
                siemplify.LOGGER.info(f"Added alert {alert_info.ticket_id} to package results")

            except Exception as e:
                siemplify.LOGGER.error(f"Failed to process GNQL event. Error: {str(e)}")
                siemplify.LOGGER.exception(e)

                if is_test_run:
                    raise
                break

        # Save data for the next run if not in test mode
        if not is_test_run and alerts:
            write_ids(siemplify, existing_ids)

        siemplify.LOGGER.info(f"Created total of {len(alerts)} alerts")
        siemplify.LOGGER.info("------------------- Main - Finished -------------------")
        siemplify.return_package(alerts)

    except RateLimitError as e:
        siemplify.LOGGER.error("Daily rate limit reached, please check API Key.")
        siemplify.LOGGER.exception(e)
        if is_test_run:
            raise

    except RequestFailure as e:
        if "401" in str(e):
            siemplify.LOGGER.error("Unable to auth, please check API Key.")
        else:
            siemplify.LOGGER.error(f"Request failed: {e}")
        siemplify.LOGGER.exception(e)
        if is_test_run:
            raise

    except Exception as e:
        siemplify.LOGGER.error(f"Got exception on main handler. Error: {e}")
        siemplify.LOGGER.exception(e)
        if is_test_run:
            raise


if __name__ == "__main__":
    # Connectors are run in iterations. The interval is configurable
    # from the ConnectorsScreen UI.
    is_test_run = not (len(sys.argv) < 2 or sys.argv[1] == "True")
    main(is_test_run)
