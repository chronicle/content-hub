from __future__ import annotations
import sys
import uuid

from datetime import timedelta, datetime

from soar_sdk.SiemplifyConnectors import CaseInfo, SiemplifyConnectorExecution
from soar_sdk.SiemplifyUtils import output_handler, utc_now

from EnvironmentCommon import GetEnvironmentCommonFactory

from TIPCommon.extraction import extract_connector_param
from TIPCommon.smp_io import read_ids, write_ids
from TIPCommon.smp_time import validate_timestamp
from TIPCommon.transformation import dict_to_flat
from TIPCommon.utils import is_overflowed

from ..core.constants import DEVICE_PRODUCT, VENDOR
from ..core.datamodels import Alert
from ..core.utils import GraphSecurityManagerConfig, init_graph_security_manager


CONNECTOR_NAME = "Microsoft Graph Alerts"

EVENT_STATES = [
    "fileStates",
    "hostStates",
    "malwareStates",
    "networkConnections",
    "registryKeyStates",
    "triggers",
    "userStates",
    "vulnerabilityStates",
    "cloudAppStates",
    "processes",
]

STATUSES = "unknown, newAlert, inProgress, resolved"
SEVERITIES = "high, medium, low, informational, unknown"
SCRIPT_TIMEOUT_SECONDS = 30
MAX_ALERTS = 50
OFFSET_TIME_HOURS = 120
ALERT_NAME = "UNABLE TO GET ALERT NAME"
ALERT_RULE_GENERATOR = "UNABLE TO GET ALERT RULE GENERATOR"
MAP_FILE = "map.json"


def create_alert_info(
    siemplify: SiemplifyConnectorExecution,
    environment_common: GetEnvironmentCommonFactory,
    alert: Alert,
    use_v2_api: bool=False
) -> CaseInfo:
    """
    Create alert info.

    Args:
        siemplify (SiemplifyConnectorExecution): The main Siemplify object.
        environment_common (GetEnvironmentCommonFactory): Variable use depending on
        environment.
        alert (Alert): Data of an alert used to extract necessary information.
        use_v2_api(bool): use_v2_api(bool): If true, alerts V2 API is used.

    Returns:
        CaseInfo: Alert info, for the case.
    """
    alert_info = CaseInfo()

    if alert.id:
        alert_id = alert.id
    else:
        alert_id = str(uuid.uuid4())
        siemplify.LOGGER.info(
            f"Alert ID does not found, use generated uuid {alert_id} instead"
        )

    alert_info.display_id = alert_id
    alert_info.ticket_id = alert_id
    alert_info.name = alert.title or ALERT_NAME
    alert_info.device_vendor = alert.vendor if not use_v2_api else VENDOR
    alert_info.device_product =  alert.provider if alert.provider else DEVICE_PRODUCT
    alert_info.priority = alert.siemplify_severity
    alert_info.rule_generator = alert.category or ALERT_RULE_GENERATOR
    alert_info.start_time = alert.created_datetime_ms
    alert_info.end_time = alert.last_modified_datetime_ms
    alert_info.extensions.update(alert.as_extension())

    alert_info.events = [alert.as_event()] if not use_v2_api else alert.as_event_v2()

    # Use nested State objects as Events
    for state in EVENT_STATES:
        for event in alert.raw_data.get(state, []):
            try:
                flattened_event = dict_to_flat(event)
                if flattened_event.get("userPrincipalName"):
                    flattened_event[
                        f"userPrincipalName_{flattened_event['emailRole']}"
                    ] = flattened_event["userPrincipalName"]
                flattened_event["event_class"] = state
                flattened_event["alert_id"] = alert_id
                flattened_event["timestamp"] = alert_info.start_time
                if flattened_event.get("createdDateTime"):
                    flattened_event["iso_timestamp"] = flattened_event.get(
                        "createdDateTime"
                    )
                elif flattened_event.get("timestamp"):
                    _dt = datetime.fromtimestamp(
                        int(flattened_event.get("timestamp")) / 1000
                    )
                    flattened_event["iso_timestamp"] = _dt.strftime(
                        "%Y-%m-%dT%H:%M:%SZ"
                    )
                alert_info.events.append(flattened_event)
            except TypeError as e:
                siemplify.LOGGER.error(f"Failed to build event {event}")
                siemplify.LOGGER.exception(e)

    if not alert_info.events:
        siemplify.LOGGER.info(f"No events found for Alert {alert_id}")

    alert_info.environment = environment_common.get_environment(alert.raw_data)
    siemplify.LOGGER.info(
        f"-------------- Finished processing Alert {alert_id}", alert_id=alert_id
    )

    return alert_info


@output_handler
def main(is_test_run):
    alerts = []
    all_alerts = []
    siemplify = SiemplifyConnectorExecution()  # Siemplify main SDK wrapper
    siemplify.script_name = CONNECTOR_NAME

    siemplify.LOGGER.info("==================== Main - Param Init ====================")

    environment_field_name = extract_connector_param(
        siemplify,
        "Environment Field Name",
        default_value="",
        input_type=str,
        is_mandatory=False,
        print_value=True,
    )

    environment_regex_pattern = extract_connector_param(
        siemplify,
        "Environment Regex Pattern",
        default_value=".*",
        input_type=str,
        is_mandatory=False,
        print_value=True,
    )

    client_id = extract_connector_param(
        siemplify,
        "Client ID",
        default_value="",
        input_type=str,
        is_mandatory=True,
        print_value=False,
    )

    secret_id = extract_connector_param(
        siemplify,
        "Client Secret",
        default_value="",
        input_type=str,
        is_mandatory=False,
        print_value=False,
    )

    certificate_path = extract_connector_param(
        siemplify,
        "Certificate Path",
        default_value="",
        input_type=str,
        is_mandatory=False,
        print_value=False,
    )

    certificate_password = extract_connector_param(
        siemplify,
        "Certificate Password",
        default_value="",
        input_type=str,
        is_mandatory=False,
        print_value=False,
    )

    azure_active_directory_id = extract_connector_param(
        siemplify,
        "Azure Active Directory ID",
        default_value="",
        input_type=str,
        is_mandatory=True,
        print_value=True,
    )
    use_v2_api = extract_connector_param(
        siemplify,
        param_name="Use V2 API",
        default_value=False,
        input_type=bool,
        print_value=True,
    )

    verify_ssl = extract_connector_param(
        siemplify,
        param_name="Verify SSL",
        default_value=False,
        input_type=bool,
        is_mandatory=True,
    )

    offset_time_hours = extract_connector_param(
        siemplify,
        "Offset Time In Hours",
        default_value=OFFSET_TIME_HOURS,
        input_type=int,
        is_mandatory=True,
        print_value=True,
    )

    fetch_alerts_only_from = extract_connector_param(
        siemplify,
        "Fetch Alerts only from",
        default_value="",
        input_type=str,
        is_mandatory=False,
        print_value=True,
    )

    alert_statuses_to_fetch = extract_connector_param(
        siemplify,
        "Alert Statuses to fetch",
        default_value=STATUSES,
        input_type=str,
        is_mandatory=True,
        print_value=True,
    )

    alert_severities_to_fetch = extract_connector_param(
        siemplify,
        "Alert Severities to fetch",
        default_value=SEVERITIES,
        input_type=str,
        is_mandatory=True,
        print_value=True,
    )

    max_alerts_per_cycle = extract_connector_param(
        siemplify,
        "Max Alerts Per Cycle",
        default_value=MAX_ALERTS,
        input_type=int,
        is_mandatory=True,
        print_value=True,
    )

    provider_list = (
        [provider.strip() for provider in fetch_alerts_only_from.split(",")]
        if fetch_alerts_only_from
        else []
    )
    severity_list = (
        [severity.strip() for severity in alert_severities_to_fetch.split(",")]
        if alert_severities_to_fetch
        else []
    )
    status_list = (
        [
            status.strip().replace("newAlert", "new") if use_v2_api else status.strip()
            for status in alert_statuses_to_fetch.split(",")
        ]
        if alert_statuses_to_fetch
        else []
    )

    last_run_time = siemplify.fetch_timestamp(datetime_format=True)
    environment_common = GetEnvironmentCommonFactory.create_environment_manager(
        siemplify, environment_field_name, environment_regex_pattern
    )

    # Read already existing alerts ids
    siemplify.LOGGER.info("Reading already existing alerts ids...")
    existing_ids = read_ids(siemplify)

    # Ignore stored timestamp when running tests
    if is_test_run:
        siemplify.LOGGER.info("This is a test run. Ignoring stored timestamps")
        last_calculated_run_time = validate_timestamp(
            utc_now() - timedelta(hours=offset_time_hours), offset_time_hours
        )
    else:
        last_calculated_run_time = validate_timestamp(last_run_time, offset_time_hours)

    config = GraphSecurityManagerConfig(
        client_id=client_id,
        secret_id=secret_id,
        certificate_path=certificate_path,
        certificate_password=certificate_password,
        tenant=azure_active_directory_id,
        verify_ssl=verify_ssl,
        chronicle_soar=siemplify,
    )
    try:
        mtm = init_graph_security_manager(
            config=config,
            use_v2_api=use_v2_api,
        )
    except Exception as e:
        siemplify.LOGGER.error(
            "Could not authenticate against Microsoft Graph Security. Check Credentials"
        )
        siemplify.LOGGER.exception(e)
        raise

    siemplify.LOGGER.info("------------------- Main - Started -------------------")

    if is_test_run:
        siemplify.LOGGER.info("This is a TEST run. Only 1 alert will be processed.")
        max_alerts_per_cycle = 1
    else:
        siemplify.LOGGER.info(f"Slicing alerts to {max_alerts_per_cycle}")

    fetched_alerts = mtm.list_alerts(
        provider_list,
        severity_list,
        status_list,
        last_calculated_run_time,
        max_alerts_per_cycle,
        existing_ids=existing_ids,
    )

    siemplify.LOGGER.info(f"Found {len(fetched_alerts)} alerts")

    for alert in fetched_alerts:
        try:
            # Update existing alerts
            existing_ids.append(alert.id)

            alert_info = create_alert_info(
                siemplify=siemplify,
                environment_common=environment_common,
                alert=alert,
                use_v2_api=use_v2_api,
            )

            overflowed = is_overflowed(siemplify, alert_info, is_test_run)
            if overflowed and not is_test_run:
                siemplify.LOGGER.info("Alert {alert.id} is overflow. Skipping")
                continue

            siemplify.LOGGER.info(
                f"Alert: '{alert.id}' Created in Graph at {alert.created_datetime}"
            )

            if not overflowed:
                alerts.append(alert_info)

            all_alerts.append(alert_info)

        except Exception as e:  # pylint: disable=broad-exception-caught
            siemplify.LOGGER.error(
                f"Could not add alert '{alert.title}' ({alert.id}) to Siemplify.\
                Skipping."
            )
            siemplify.LOGGER.exception(f"Exception raised: {e}")

            if is_test_run:
                raise

    if not is_test_run:
        if all_alerts:
            all_alerts = sorted(all_alerts, key=lambda alert: alert.start_time)
            # The timestamps are in milliseconds
            # So increase the last found timestamp by 1 millisecond
            # to proceed to the next millisecond
            siemplify.save_timestamp(new_timestamp=all_alerts[-1].start_time + 1)

        write_ids(siemplify, existing_ids)

    siemplify.LOGGER.info(f"Alerts Processed: {len(alerts)} of {len(all_alerts)}")
    siemplify.LOGGER.info(f"Created total of {len(alerts)} alerts")

    siemplify.LOGGER.info("------------------- Main - Finished -------------------")
    siemplify.return_package(alerts)


if __name__ == "__main__":
    # Connectors are run in iterations. The interval is
    # configurable from the ConnectorsScreen UI.
    is_test_run_flag = not (len(sys.argv) < 2 or sys.argv[1] == "True")
    main(is_test_run_flag)
