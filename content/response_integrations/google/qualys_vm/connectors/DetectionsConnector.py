from __future__ import annotations
import sys

from soar_sdk.SiemplifyUtils import output_handler, unix_now
from soar_sdk.SiemplifyConnectors import SiemplifyConnectorExecution
from soar_sdk.SiemplifyConnectorsDataModel import AlertInfo

from TIPCommon import (
    extract_connector_param,
    is_approaching_timeout,
    read_ids,
    is_overflowed,
    pass_whitelist_filter,
    convert_comma_separated_to_list,
    convert_list_to_comma_string,
)
from EnvironmentCommon import GetEnvironmentCommonFactory

from ..core.constants import (
    CONNECTOR_NAME,
    DEFAULT_SEVERITY,
    HOST_GROUPING,
    DETECTION_GROUPING,
    NONE_GROUPING,
    POSSIBLE_STATUSES,
    POSSIBLE_GROUPINGS,
    DEFAULT_STATUS_FILTER,
    STORED_IDS_LIMIT,
)
from ..core.UtilsManager import pass_severity_filter, write_ids
from ..core.QualysVMManager import QualysVMManager


connector_starting_time = unix_now()


@output_handler
def main(is_test_run):
    siemplify = SiemplifyConnectorExecution()
    siemplify.script_name = CONNECTOR_NAME
    processed_alerts = []

    if is_test_run:
        siemplify.LOGGER.info(
            '***** This is an "IDE Play Button"\\"Run Connector once" test run ******'
        )

    siemplify.LOGGER.info("------------------- Main - Param Init -------------------")

    api_root = extract_connector_param(
        siemplify, param_name="API Root", is_mandatory=True, print_value=True
    )
    username = extract_connector_param(
        siemplify, param_name="Username", is_mandatory=True, print_value=True
    )
    password = extract_connector_param(
        siemplify, param_name="Password", is_mandatory=True
    )
    verify_ssl = extract_connector_param(
        siemplify,
        param_name="Verify SSL",
        is_mandatory=True,
        input_type=bool,
        print_value=True,
    )

    environment_field_name = extract_connector_param(
        siemplify, param_name="Environment Field Name", print_value=True
    )
    environment_regex_pattern = extract_connector_param(
        siemplify, param_name="Environment Regex Pattern", print_value=True
    )

    script_timeout = extract_connector_param(
        siemplify,
        param_name="PythonProcessTimeout",
        is_mandatory=True,
        input_type=int,
        print_value=True,
    )
    lowest_severity_to_fetch = extract_connector_param(
        siemplify,
        param_name="Lowest Severity To Fetch",
        input_type=int,
        print_value=True,
        default_value=DEFAULT_SEVERITY,
    )
    status_filter = extract_connector_param(
        siemplify,
        param_name="Status Filter",
        print_value=True,
        default_value=DEFAULT_STATUS_FILTER,
    )
    ingest_ignored = extract_connector_param(
        siemplify,
        param_name="Ingest Ignored Detections",
        is_mandatory=True,
        input_type=bool,
        print_value=True,
    )
    ingest_disabled = extract_connector_param(
        siemplify,
        param_name="Ingest Disabled Detections",
        is_mandatory=True,
        input_type=bool,
        print_value=True,
    )
    whitelist_as_a_blacklist = extract_connector_param(
        siemplify,
        param_name="Use whitelist as a blacklist",
        is_mandatory=True,
        input_type=bool,
        print_value=True,
    )
    grouping_mechanism = extract_connector_param(
        siemplify, param_name="Grouping Mechanism", print_value=True
    )
    device_product_field = extract_connector_param(
        siemplify, "DeviceProductField", is_mandatory=True
    )
    x_request_with_header = extract_connector_param(
        siemplify,
        param_name="X-Requested-With Header",
        print_value=True,
        default_value="Google SecOps SOAR",
    )
    statuses = [
        status.title() for status in convert_comma_separated_to_list(status_filter)
    ]

    try:
        siemplify.LOGGER.info("------------------- Main - Started -------------------")

        if lowest_severity_to_fetch > 5 or lowest_severity_to_fetch < 1:
            siemplify.LOGGER.error(
                "Lowest Severity To Fetch must be between 1 and 5. "
                "The default value {} will be used".format(DEFAULT_SEVERITY)
            )
            lowest_severity_to_fetch = DEFAULT_SEVERITY

        if grouping_mechanism not in POSSIBLE_GROUPINGS:
            siemplify.LOGGER.error(
                f"Invalid value given for Grouping Mechanism. {NONE_GROUPING} will be used"
            )
            grouping_mechanism = NONE_GROUPING

        invalid_statuses = [
            status for status in statuses if status not in POSSIBLE_STATUSES
        ]

        if len(invalid_statuses) == len(statuses):
            raise Exception(
                'Invalid values provided for "Status Filter" parameter. '
                "Possible values are: {}.".format(
                    convert_list_to_comma_string(POSSIBLE_STATUSES)
                )
            )
        elif invalid_statuses:
            statuses = [status for status in statuses if status not in invalid_statuses]
            siemplify.LOGGER.error(
                'Following values are invalid for "Status Filter" '
                "parameter: {}.".format(convert_list_to_comma_string(invalid_statuses))
            )

        # Read already existing alerts ids
        existing_ids = read_ids(siemplify, default_value_to_return={})
        siemplify.LOGGER.info(
            f"Successfully loaded {len(existing_ids)} existing hosts from ids file"
        )

        manager = QualysVMManager(
            server_address=api_root,
            username=username,
            password=password,
            use_ssl=verify_ssl,
            siemplify_logger=siemplify.LOGGER,
            x_request_with_header=x_request_with_header,
        )

        filtered_alerts = manager.get_vulnerabilities(
            existing_ids=existing_ids,
            include_ignored=ingest_ignored,
            include_disabled=ingest_disabled,
            status_filter=convert_list_to_comma_string([status for status in statuses]),
        )

        siemplify.LOGGER.info(f"Fetched {len(filtered_alerts)} detections")

        grouped_alerts = group_detections(
            fetched_detections=filtered_alerts, grouping_mechanism=grouping_mechanism
        )

        if is_test_run:
            siemplify.LOGGER.info("This is a TEST run. Only 1 alert will be processed.")
            grouped_alerts = grouped_alerts[:1]

        for alert_group in grouped_alerts:
            alert = alert_group[0]
            try:
                if is_approaching_timeout(
                    python_process_timeout=script_timeout,
                    connector_starting_time=connector_starting_time,
                ):
                    siemplify.LOGGER.info(
                        "Timeout is approaching. Connector will gracefully exit"
                    )
                    break

                siemplify.LOGGER.info(
                    f"Started processing detection {alert.id} - {alert.dns_name} - {alert.host_id}"
                )
                group_to_process = []
                for detection in alert_group:
                    if pass_filters(
                        siemplify,
                        whitelist_as_a_blacklist,
                        detection,
                        "detection_type",
                        lowest_severity_to_fetch,
                    ):
                        group_to_process.append(detection)

                if not group_to_process:
                    siemplify.LOGGER.info(
                        f"Detection {alert.id} - {alert.dns_name} - {alert.host_id} did not pass filtering."
                    )
                    continue

                # Update existing alerts
                for host in set([alert.host_id for alert in alert_group]):
                    entries = [
                        alert.entry
                        for alert in group_to_process
                        if alert.host_id == host
                    ]
                    if host in existing_ids:
                        existing_ids[host] = list(set(existing_ids[host] + entries))
                    else:
                        existing_ids.update({host: list(set(entries))})

                common_env = GetEnvironmentCommonFactory.create_environment_manager(
                    siemplify=siemplify,
                    environment_field_name=environment_field_name,
                    environment_regex_pattern=environment_regex_pattern,
                )
                alert_info = alert.get_alert_info(
                    alert_info=AlertInfo(),
                    environment_common=common_env,
                    device_product_field=device_product_field,
                    grouping_mechanism=grouping_mechanism,
                    execution_time=connector_starting_time,
                    detections_group=group_to_process,
                )

                if is_overflowed(siemplify, alert_info, is_test_run):
                    siemplify.LOGGER.info(
                        "{alert_name}-{alert_identifier}-{environment}-{product} "
                        "found as overflow alert. Skipping...".format(
                            alert_name=alert_info.rule_generator,
                            alert_identifier=alert_info.ticket_id,
                            environment=alert_info.environment,
                            product=alert_info.device_product,
                        )
                    )
                    # If is overflowed we should skip
                    continue

                processed_alerts.append(alert_info)
                siemplify.LOGGER.info(
                    f"Alert {alert.id} - {alert.dns_name} - {alert.host_id} was created."
                )

            except Exception as e:
                siemplify.LOGGER.error(
                    f"Failed to process detection {alert.id} - {alert.dns_name} - {alert.host_id}"
                )
                siemplify.LOGGER.exception(e)

                if is_test_run:
                    raise

            siemplify.LOGGER.info(
                f"Finished processing detection {alert.id} - {alert.dns_name} - {alert.host_id}"
            )

        if not is_test_run:
            siemplify.LOGGER.info("Saving existing ids.")
            write_ids(siemplify, existing_ids, stored_ids_limit=STORED_IDS_LIMIT)

    except Exception as e:
        siemplify.LOGGER.error(f"Got exception on main handler. Error: {e}")
        siemplify.LOGGER.exception(e)

        if is_test_run:
            raise

    siemplify.LOGGER.info(f"Created total of {len(processed_alerts)} cases")
    siemplify.LOGGER.info("------------------- Main - Finished -------------------")
    siemplify.return_package(processed_alerts)


def pass_filters(
    siemplify, whitelist_as_a_blacklist, alert, model_key, lowest_severity_to_fetch
):
    # All alert filters should be checked here
    if not pass_whitelist_filter(siemplify, whitelist_as_a_blacklist, alert, model_key):
        return False

    if not pass_severity_filter(siemplify, alert, lowest_severity_to_fetch):
        return False

    return True


def group_detections(fetched_detections, grouping_mechanism):
    property_key = (
        "ip_address"
        if grouping_mechanism == HOST_GROUPING
        else "id"
        if grouping_mechanism == DETECTION_GROUPING
        else None
    )
    if property_key:
        detection_groups = set(
            map(lambda detection: getattr(detection, property_key), fetched_detections)
        )
        grouped_detections = [
            [
                detection
                for detection in fetched_detections
                if getattr(detection, property_key) == group
            ]
            for group in detection_groups
        ]
        return grouped_detections

    return [[detection] for detection in fetched_detections]


if __name__ == "__main__":
    # Connectors are run in iterations. The interval is configurable from the ConnectorsScreen UI.
    is_test = not (len(sys.argv) < 2 or sys.argv[1] == "True")
    main(is_test)
