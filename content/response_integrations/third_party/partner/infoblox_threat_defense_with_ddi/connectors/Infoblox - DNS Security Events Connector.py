from __future__ import annotations
import sys
from datetime import datetime

from ..core.APIManager import APIManager
from EnvironmentCommon import GetEnvironmentCommonFactory
from soar_sdk.SiemplifyConnectors import SiemplifyConnectorExecution
from soar_sdk.SiemplifyConnectorsDataModel import AlertInfo
from soar_sdk.SiemplifyUtils import output_handler, unix_now
from TIPCommon import (
    extract_connector_param,
    save_timestamp,
    get_last_success_time,
    is_overflowed,
    is_approaching_timeout,
    read_ids,
    write_ids,
)
from ..core.constants import (
    ALLOWED_THREAT_LEVEL_VALUES,
    DEFAULT_DNS_EVENTS_LIMIT,
    UNIX_FORMAT,
    DEFAULT_MAX_HOURS_BACKWARD,
)
from ..core.utils import validate_enum, validate_integer_param

# ==============================================================================
# This connector retrieves DNS Security Events from Infoblox Cloud and creates
# alerts in Google SecOps SOAR. Each DNS Security Event will generate an alert/case.
#
# Note: Deduplication using stored IDs is not needed for this connector as
# events don't have any unique identifier from the API. Instead, events are
# tracked by timestamps (event_time). Incremental fetching is handled by saving the
# latest event timestamp and using it as the start time for the next polling cycle,
# which naturally prevents duplicate processing.
# ==============================================================================

connector_starting_time = unix_now()


def validate_input_params(threat_level, limit, max_hours_backwards):
    """
    Validate input parameters for the connector.

    Args:
        threat_level (str): Filter by threat severity level
        limit (str): Maximum number of results to return
        max_hours_backwards (str): Number of hours before the first connector iteration to
        retrieve alerts from for the first time

    Returns:
        tuple: Validated parameters
    """

    # Validate threat_level using validate_enum with case-insensitive matching
    if threat_level:
        threat_level_upper = threat_level.upper()
        threat_level = validate_enum(
            threat_level_upper, ALLOWED_THREAT_LEVEL_VALUES, "Threat Level"
        )

    # Validate limit if provided
    if limit:
        limit = validate_integer_param(limit, "Limit", zero_allowed=False, allow_negative=False)

    # Validate Max Hours Backwards if provided
    if max_hours_backwards:
        max_hours_backwards = validate_integer_param(
            max_hours_backwards, "Max Hours Backwards", zero_allowed=True, allow_negative=False
        )

    return threat_level, limit, max_hours_backwards


@output_handler
def main(is_test_run):
    siemplify = SiemplifyConnectorExecution()

    # Configuration Parameters
    api_root = extract_connector_param(
        siemplify, param_name="API Root", input_type=str, is_mandatory=True, print_value=True
    )
    api_key = extract_connector_param(
        siemplify, param_name="API Key", input_type=str, is_mandatory=True, print_value=False
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
    max_hours_backwards = extract_connector_param(
        siemplify,
        param_name="Max Hours Backwards",
        default_value=DEFAULT_MAX_HOURS_BACKWARD,
        input_type=str,
        is_mandatory=False,
        print_value=True,
    )
    queried_name = extract_connector_param(
        siemplify, param_name="Queried name", input_type=str, is_mandatory=False, print_value=True
    )
    policy_name = extract_connector_param(
        siemplify, param_name="Policy Name", input_type=str, is_mandatory=False, print_value=True
    )
    threat_level = extract_connector_param(
        siemplify, param_name="Threat Level", input_type=str, is_mandatory=False, print_value=True
    )
    threat_class = extract_connector_param(
        siemplify, param_name="Threat Class", input_type=str, is_mandatory=False, print_value=True
    )
    threat_family = extract_connector_param(
        siemplify, param_name="Threat Family", input_type=str, is_mandatory=False, print_value=True
    )
    threat_indicator = extract_connector_param(
        siemplify,
        param_name="Threat Indicator",
        input_type=str,
        is_mandatory=False,
        print_value=True,
    )
    policy_action = extract_connector_param(
        siemplify, param_name="Policy Action", input_type=str, is_mandatory=False, print_value=True
    )
    feed_name = extract_connector_param(
        siemplify, param_name="Feed Name", input_type=str, is_mandatory=False, print_value=True
    )
    network = extract_connector_param(
        siemplify, param_name="Network", input_type=str, is_mandatory=False, print_value=True
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

    # Pagination and Timeout Parameters
    python_process_timeout = extract_connector_param(
        siemplify,
        param_name="PythonProcessTimeout",
        input_type=int,
        is_mandatory=True,
        print_value=False,
    )
    limit = extract_connector_param(
        siemplify,
        param_name="Limit",
        default_value=DEFAULT_DNS_EVENTS_LIMIT,
        input_type=str,
        is_mandatory=False,
        print_value=True,
    )
    device_product_field = extract_connector_param(
        siemplify, param_name="DeviceProductField", is_mandatory=False, print_value=True
    )

    siemplify.LOGGER.info("------------------- Main - Started -------------------")

    # Initialize processed events lists
    alerts = []

    try:

        threat_level, limit, max_hours_backwards = validate_input_params(
            threat_level, limit, max_hours_backwards
        )

        # Read existing event IDs for deduplication
        siemplify.LOGGER.info("Reading existing event IDs...")
        existing_ids = read_ids(siemplify)

        if is_test_run:
            siemplify.LOGGER.info("This is a TEST run. Only 1 alert will be processed.")
            limit = 100

        # Prepare the timestamp parameters
        # Set end_time to current time as Unix timestamp (seconds since epoch)
        end_time = str(int(datetime.utcnow().timestamp()))

        # Calculate start_time based on last success time or max_hours_backwards
        start_time = str(
            int(
                get_last_success_time(
                    siemplify=siemplify,
                    offset_with_metric={"hours": max_hours_backwards},
                    time_format=UNIX_FORMAT,
                ).timestamp()
            )
        )

        siemplify.LOGGER.info(
            f"Time range: start_time={start_time}, end_time={end_time} (Unix timestamps)"
        )

        # Instantiate API manager
        manager = APIManager(api_root, api_key, verify_ssl=verify_ssl, siemplify=siemplify)

        # Fetch dns security events
        dns_events = manager.get_dns_security_events(
            existing_ids=existing_ids,
            t0=start_time,
            t1=end_time,
            queried_name=queried_name,
            policy_name=policy_name,
            threat_level=threat_level,
            threat_class=threat_class,
            threat_family=threat_family,
            threat_indicator=threat_indicator,
            policy_action=policy_action,
            feed_name=feed_name,
            network=network,
            limit=limit,
        )

        # Change order to ascending
        dns_events = dns_events[::-1]

        if is_test_run:
            dns_events = dns_events[:1]

        siemplify.LOGGER.info(f"Found {len(dns_events)} new DNS Security Events to process.")

        # Process each pre-filtered event
        for dns_event in dns_events:
            siemplify.LOGGER.info(
                f"Started processing DNS Security Event with composite ID: {dns_event.event_id}"
            )
            try:
                # Check for timeout
                if is_approaching_timeout(connector_starting_time, python_process_timeout):
                    siemplify.LOGGER.info("Timeout is approaching. Connector will gracefully exit")
                    break

                # Create environment manager
                environment_common = GetEnvironmentCommonFactory.create_environment_manager(
                    siemplify, environment_field_name, environment_regex_pattern
                )

                # Convert event to AlertInfo using the datamodel method
                alert_info = dns_event.get_alert_info(
                    AlertInfo(), environment_common, device_product_field
                )

                # Update existing alerts
                existing_ids.append(alert_info.ticket_id)

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

            except Exception as e:
                siemplify.LOGGER.error(f"Failed to process DNS Security Event. Error: {str(e)}")
                siemplify.LOGGER.exception(e)

                if is_test_run:
                    raise
                break

        # Save data for the next run if not in test mode
        if not is_test_run and alerts:
            write_ids(siemplify, existing_ids)
            save_timestamp(siemplify=siemplify, alerts=alerts, timestamp_key="end_time")

        siemplify.LOGGER.info(f"Created total of {len(alerts)} alerts")
        siemplify.LOGGER.info("------------------- Main - Finished -------------------")
        siemplify.return_package(alerts)

    except Exception as e:
        siemplify.LOGGER.error(f"Got exception on main handler. Error: {e}")
        siemplify.LOGGER.exception(e)

        if is_test_run:
            raise


if __name__ == "__main__":
    # Connectors are run in iterations. The interval is configurable from the ConnectorsScreen UI.
    is_test_run = not (len(sys.argv) < 2 or sys.argv[1] == "True")
    main(is_test_run)
