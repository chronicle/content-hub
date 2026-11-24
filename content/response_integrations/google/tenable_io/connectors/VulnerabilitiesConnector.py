from __future__ import annotations
from soar_sdk.SiemplifyUtils import output_handler, unix_now
from soar_sdk.SiemplifyConnectors import SiemplifyConnectorExecution
from TIPCommon import extract_connector_param
from tenable_io.core.constants import (
    CONNECTOR_NAME,
    DEFAULT_SEVERITY,
    HOST_GROUPING,
    VULNERABILITY_GROUPING,
    NONE_GROUPING,
    POSSIBLE_STATUSES,
    POSSIBLE_GROUPINGS,
    DEFAULT_STATUS_FILTER,
    DEFAULT_TIME_FRAME,
    SEVERITIES,
    FINISHED_STATUS,
)
from tenable_io.core.UtilsManager import (
    read_ids,
    write_ids,
    is_approaching_timeout,
    get_environment_common,
    create_whitelist_filter,
    convert_comma_separated_to_list,
    convert_list_to_comma_string,
    read_pending_export,
    save_timestamp,
    get_last_success_time,
    UNIX_FORMAT,
    write_pending_export,
)
from tenable_io.core.TenableIOManager import TenableIOManager
from tenable_io.core.TenableIOExceptions import ExportNotFinishedException
from soar_sdk.SiemplifyConnectorsDataModel import AlertInfo
import sys


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
    access_key = extract_connector_param(
        siemplify, param_name="Access Key", is_mandatory=True
    )
    secret_key = extract_connector_param(
        siemplify, param_name="Secret Key", is_mandatory=True
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
        siemplify, param_name="Lowest Severity To Fetch", print_value=True
    )
    status_filter = extract_connector_param(
        siemplify,
        param_name="Status Filter",
        print_value=True,
        default_value=DEFAULT_STATUS_FILTER,
    )
    days_backwards = extract_connector_param(
        siemplify,
        param_name="Max Days Backwards",
        input_type=int,
        default_value=DEFAULT_TIME_FRAME,
        print_value=True,
    )
    whitelist_as_a_blacklist = extract_connector_param(
        siemplify,
        "Use whitelist as a blacklist",
        is_mandatory=True,
        input_type=bool,
        print_value=True,
    )
    grouping_mechanism = extract_connector_param(
        siemplify, param_name="Grouping Mechanism", is_mandatory=True, print_value=True
    )
    device_product_field = extract_connector_param(
        siemplify, "DeviceProductField", is_mandatory=True
    )

    statuses = [
        status.lower() for status in convert_comma_separated_to_list(status_filter)
    ]

    try:
        siemplify.LOGGER.info("------------------- Main - Started -------------------")

        if days_backwards < 0:
            siemplify.LOGGER.info(
                f"Max Days Backwards must be non-negative. The default value {DEFAULT_TIME_FRAME} "
                f"will be used"
            )
            days_backwards = DEFAULT_TIME_FRAME

        if (
            lowest_severity_to_fetch
            and lowest_severity_to_fetch.lower() not in SEVERITIES
        ):
            raise Exception(
                f"Invalid value given for Lowest Severity To Fetch parameter. Possible values are: "
                f"{convert_list_to_comma_string([severity.title() for severity in SEVERITIES])}. "
                f'The default value "{DEFAULT_SEVERITY}" will be used.'
            )

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
                f'Invalid values provided for "Status Filter" parameter. Possible values are: '
                f"{convert_list_to_comma_string(POSSIBLE_STATUSES)}."
            )
        elif invalid_statuses:
            statuses = [status for status in statuses if status not in invalid_statuses]
            siemplify.LOGGER.error(
                f'Following values are invalid for "Status Filter" parameter: '
                f"{convert_list_to_comma_string(invalid_statuses)}."
            )

        # Read already existing alerts ids
        existing_ids = read_ids(siemplify)
        siemplify.LOGGER.info(
            f"Successfully loaded {len(existing_ids)} existing hosts from ids file"
        )

        siemplify.LOGGER.info("Reading pending export data...")
        pending_export_data = read_pending_export(siemplify)

        manager = TenableIOManager(
            api_root=api_root,
            secret_key=secret_key,
            access_key=access_key,
            verify_ssl=verify_ssl,
            siemplify_logger=siemplify.LOGGER,
        )

        last_success_time = get_last_success_time(
            siemplify=siemplify,
            offset_with_metric={"days": days_backwards},
            time_format=UNIX_FORMAT,
        )

        plugin_families = manager.list_plugin_families() if siemplify.whitelist else []
        filtered_plugin_families = create_whitelist_filter(
            siemplify,
            whitelist_as_a_blacklist,
            plugin_families=[family.name for family in plugin_families],
        )

        export_object = {}
        filtered_alerts = []
        fetched_alerts = []

        if pending_export_data:
            export_status = pending_export_data.get("status")
            export_uuid = pending_export_data.get("uuid")
            if export_status != FINISHED_STATUS:
                export_object = manager.get_export_status(
                    siemplify=siemplify, export_uuid=export_uuid
                )
                pending_export_data = export_object
            if pending_export_data:
                chunks_available = pending_export_data.get("chunks_available")
                if chunks_available:
                    filtered_alerts = manager.get_export_chunk_data(
                        existing_ids=existing_ids,
                        export_uuid=export_uuid,
                        chunk_id=chunks_available[0],
                    )
        else:
            export_uuid = manager.initiate_export(
                statuses=statuses,
                severities=(
                    SEVERITIES[SEVERITIES.index(lowest_severity_to_fetch.lower()) :]
                    if lowest_severity_to_fetch
                    else []
                ),
                start_timestamp=last_success_time,
                plugin_families=filtered_plugin_families,
            )

            export_object = manager.get_export_status(
                siemplify=siemplify, export_uuid=export_uuid
            )
            if export_object:
                chunks_available = export_object.get("chunks_available")
                if chunks_available:
                    filtered_alerts = manager.get_export_chunk_data(
                        existing_ids=existing_ids,
                        export_uuid=export_uuid,
                        chunk_id=chunks_available[0],
                    )

        siemplify.LOGGER.info(f"Fetched {len(filtered_alerts)} vulnerabilities")

        grouped_alerts = group_vulnerabilities(
            fetched_vulnerabilities=filtered_alerts,
            grouping_mechanism=grouping_mechanism,
        )

        if is_test_run:
            siemplify.LOGGER.info("This is a TEST run. Only 1 alert will be processed.")
            grouped_alerts = grouped_alerts[:1]

        for alert_group in grouped_alerts:
            alert = alert_group[-1]
            try:
                if is_approaching_timeout(script_timeout, connector_starting_time):
                    siemplify.LOGGER.info(
                        "Timeout is approaching. Connector will gracefully exit"
                    )
                    break

                siemplify.LOGGER.info(
                    f"Started processing vulnerability {alert.id} - {alert.asset_id}"
                )

                # Update existing alerts
                for host in set([alert.asset_id for alert in alert_group]):
                    if host in existing_ids:
                        existing_ids[host] = list(
                            set(
                                existing_ids[host]
                                + [
                                    alert.id
                                    for alert in alert_group
                                    if alert.asset_id == host
                                ]
                            )
                        )
                    else:
                        existing_ids.update(
                            {
                                host: list(
                                    set(
                                        [
                                            alert.id
                                            for alert in alert_group
                                            if alert.asset_id == host
                                        ]
                                    )
                                )
                            }
                        )
                fetched_alerts.extend(alert_group)

                alert_info = alert.get_alert_info(
                    alert_info=AlertInfo(),
                    environment_common=get_environment_common(
                        siemplify, environment_field_name, environment_regex_pattern
                    ),
                    device_product_field=device_product_field,
                    grouping_mechanism=grouping_mechanism,
                    vulnerabilities_group=alert_group,
                )

                processed_alerts.append(alert_info)
                siemplify.LOGGER.info(
                    f"Alert {alert.id} - {alert.asset_id} was created."
                )

            except Exception as e:
                siemplify.LOGGER.error(
                    f"Failed to process vulnerability {alert.id} - {alert.asset_id}"
                )
                siemplify.LOGGER.exception(e)

                if is_test_run:
                    raise

            siemplify.LOGGER.info(
                f"Finished processing vulnerability {alert.id} - {alert.asset_id}"
            )

        if not is_test_run:
            siemplify.LOGGER.info("Saving existing ids.")
            write_ids(siemplify, existing_ids)
            save_timestamp(
                siemplify=siemplify, alerts=fetched_alerts, timestamp_key="last_found"
            )

        write_pending_export(siemplify, export_object)

    except ExportNotFinishedException as e:
        siemplify.LOGGER.warn(e)

    except Exception as e:
        siemplify.LOGGER.error(f"Got exception on main handler. Error: {e}")
        siemplify.LOGGER.exception(e)

        if is_test_run:
            raise

    siemplify.LOGGER.info(f"Created total of {len(processed_alerts)} cases")
    siemplify.LOGGER.info("------------------- Main - Finished -------------------")
    siemplify.return_package(processed_alerts)


def group_vulnerabilities(fetched_vulnerabilities, grouping_mechanism):
    property_key = (
        "asset_id"
        if grouping_mechanism == HOST_GROUPING
        else "id" if grouping_mechanism == VULNERABILITY_GROUPING else None
    )
    if property_key:
        vulnerability_groups = set(
            map(
                lambda vulnerability: getattr(vulnerability, property_key),
                fetched_vulnerabilities,
            )
        )
        grouped_vulnerabilities = [
            [
                vulnerability
                for vulnerability in fetched_vulnerabilities
                if getattr(vulnerability, property_key) == group
            ]
            for group in vulnerability_groups
        ]
        return grouped_vulnerabilities

    return [[vulnerability] for vulnerability in fetched_vulnerabilities]


if __name__ == "__main__":
    # Connectors are run in iterations. The interval is configurable from the ConnectorsScreen UI.
    is_test = not (len(sys.argv) < 2 or sys.argv[1] == "True")
    main(is_test)
