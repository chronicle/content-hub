from __future__ import annotations
import sys

from EnvironmentCommon import GetEnvironmentCommonFactory
from soar_sdk.SiemplifyConnectors import SiemplifyConnectorExecution
from soar_sdk.SiemplifyUtils import output_handler, unix_now
from ..core.McAfeeManager import McafeeEpoManager
from TIPCommon import (
    extract_connector_param,
    is_approaching_timeout,
    get_last_success_time,
    save_timestamp,
    is_overflowed,
    write_ids,
    read_ids,
    UNIX_FORMAT,
)
from ..core.constants import THREATS_CONNECTOR_SCRIPT_NAME
from ..core.exceptions import McAfeeEpoNotFoundException
from ..core.utils import get_whitelist, SeverityLevelMappingEnum, dotted_field_to_underscored

connector_starting_time = unix_now()

# CONSTANTS
THREATS_TO_FETCH_DEFAULT_LIMIT = 100
THREATS_TO_PROCESS_DEFAULT_LIMIT = 10

DEFAULT_TIME_FRAME = 1
CONNECTOR_DATA_TABLE_NAME = "EPOEvents"
CONNECTOR_JOIN_TABLE_NAME = "EPExtendedEvent"
CONNECTOR_FIELDS_TO_RETURN = [
    "EPOEvents.ServerID",
    "EPOEvents.ReceivedUTC",
    "EPOEvents.DetectedUTC",
    "EPOEvents.EventTimeLocal",
    "EPOEvents.AgentGUID",
    "EPOEvents.Analyzer",
    "EPOEvents.AnalyzerName",
    "EPOEvents.AnalyzerVersion",
    "EPOEvents.AnalyzerHostName",
    "EPOEvents.AnalyzerIPV4",
    "EPOEvents.AnalyzerIPV6",
    "EPOEvents.AnalyzerMAC",
    "EPOEvents.AnalyzerDATVersion",
    "EPOEvents.AnalyzerEngineVersion",
    "EPOEvents.SourceHostName",
    "EPOEvents.SourceIPV4",
    "EPOEvents.SourceIPV6",
    "EPOEvents.SourceMAC",
    "EPOEvents.SourceUserName",
    "EPOEvents.SourceProcessName",
    "EPOEvents.SourceURL",
    "EPOEvents.TargetHostName",
    "EPOEvents.TargetIPV4",
    "EPOEvents.TargetIPV6",
    "EPOEvents.TargetMAC",
    "EPOEvents.TargetUserName",
    "EPOEvents.TargetPort",
    "EPOEvents.TargetProtocol",
    "EPOEvents.TargetProcessName",
    "EPOEvents.TargetFileName",
    "EPOEvents.ThreatCategory",
    "EPOEvents.ThreatEventID",
    "EPOEvents.ThreatSeverity",
    "EPOEvents.ThreatName",
    "EPOEvents.ThreatType",
    "EPOEvents.ThreatActionTaken",
    "EPOEvents.ThreatHandled",
    "EPOEvents.AnalyzerDetectionMethod",
]


@output_handler
def main(is_test_run):
    siemplify = SiemplifyConnectorExecution()
    siemplify.script_name = THREATS_CONNECTOR_SCRIPT_NAME

    if is_test_run:
        siemplify.LOGGER.info(
            "***** This is an 'IDE Play Button' 'Run Connector once' test run ******"
        )

    siemplify.LOGGER.info("------------------- Main - Param Init -------------------")

    api_root = extract_connector_param(
        siemplify, param_name="API Root", is_mandatory=True
    )
    username = extract_connector_param(
        siemplify, param_name="Username", is_mandatory=True
    )
    password = extract_connector_param(
        siemplify, param_name="Password", is_mandatory=True
    )
    group_name = extract_connector_param(
        siemplify, param_name="Group Name", print_value=True
    )
    verify_ssl = extract_connector_param(
        siemplify,
        param_name="Verify SSL",
        default_value=True,
        input_type=bool,
        is_mandatory=True,
    )
    ca_certificate = extract_connector_param(
        siemplify, param_name="CA Certificate File"
    )

    device_product_field_name = extract_connector_param(
        siemplify=siemplify,
        param_name="DeviceProductField",
        is_mandatory=True,
        print_value=True,
    )
    environment_field_name = extract_connector_param(
        siemplify, param_name="Environment Field Name", default_value=""
    )
    environment_regex_pattern = extract_connector_param(
        siemplify, param_name="Environment Regex Pattern"
    )
    script_timeout = extract_connector_param(
        siemplify,
        param_name="PythonProcessTimeout",
        input_type=int,
        is_mandatory=True,
        print_value=True,
    )

    hours_backwards = extract_connector_param(
        siemplify,
        param_name="Max Hours Backwards",
        input_type=int,
        default_value=DEFAULT_TIME_FRAME,
        print_value=True,
    )
    lowest_severity_to_fetch = extract_connector_param(
        siemplify, param_name="Lowest Severity To Fetch", print_value=True
    )
    events_fetch_limit = events_process_limit = extract_connector_param(
        siemplify, param_name="Max Events To Fetch", input_type=int, print_value=True
    )
    if events_fetch_limit is None:
        events_fetch_limit, events_process_limit = (
            THREATS_TO_FETCH_DEFAULT_LIMIT,
            THREATS_TO_PROCESS_DEFAULT_LIMIT,
        )
    else:
        events_fetch_limit = max(events_fetch_limit, THREATS_TO_FETCH_DEFAULT_LIMIT)

    whitelist_as_blacklist = extract_connector_param(
        siemplify,
        "Use whitelist as a blacklist",
        is_mandatory=True,
        input_type=bool,
        print_value=True,
    )

    siemplify.LOGGER.info("------------------- Main - Started -------------------")

    all_threats, processed_threats = [], []

    try:
        manager = McafeeEpoManager(
            api_root=api_root,
            username=username,
            password=password,
            group_name=group_name,
            ca_certificate=ca_certificate,
            verify_ssl=verify_ssl,
            force_check_connectivity=True,
            logger=siemplify.LOGGER,
        )

        siemplify.LOGGER.info("Reading already existing alerts ids...")
        existing_ids = read_ids(siemplify)

        start_time, end_time = int(
            get_last_success_time(
                siemplify=siemplify,
                offset_with_metric={"hours": hours_backwards},
                time_format=UNIX_FORMAT,
            )
        ), int(unix_now())

        # Get system for provided group name
        siemplify.LOGGER.info("Fetching threats...")

        severity_value = (
            lowest_severity_to_fetch
            and SeverityLevelMappingEnum.get_values(
                level_name=lowest_severity_to_fetch
            )[-1]
        )

        try:
            systems = manager.get_systems_by_self_group() or []
        except McAfeeEpoNotFoundException:
            raise McAfeeEpoNotFoundException(
                f'Group "{manager.group.group_name}" was found, but it doesn\'t contain any endpoints. Please use a '
                "different group or remove that group from configuration"
            )

        threats = manager.get_threats(
            table_name=CONNECTOR_DATA_TABLE_NAME,
            join_table=CONNECTOR_JOIN_TABLE_NAME,
            time_range=(start_time, end_time) if start_time and end_time else None,
            severity=severity_value,
            systems_ids=[system_data.agent_guid for system_data in systems],
            fields_to_return=CONNECTOR_FIELDS_TO_RETURN,
            limit=events_fetch_limit,
            analyzers_names=get_whitelist(siemplify),
            analyzers_names_as_blacklist=whitelist_as_blacklist,
            unique_threats=True,
        )

        siemplify.LOGGER.info(f"Fetched {len(threats)} threats")

        for threat in threats:
            try:
                if len(processed_threats) >= events_process_limit:
                    siemplify.LOGGER.info(
                        f"{len(processed_threats)} threats were fetched. Stopping the connector"
                    )
                    break

                if is_approaching_timeout(connector_starting_time, script_timeout):
                    siemplify.LOGGER.info(
                        "Timeout is approaching. Connector will gracefully exit"
                    )
                    break

                if is_test_run and processed_threats:
                    siemplify.LOGGER.info(
                        "Maximum threats limit(1) for test run reached!"
                    )
                    break

                siemplify.LOGGER.info(f"Started processing threat {threat.hash_id}")

                all_threats.append(threat)

                if threat.hash_id in existing_ids:
                    siemplify.LOGGER.info(
                        f"Threat {threat.hash_id} already fetched. Skipping..."
                    )
                    continue

                siemplify.LOGGER.info(f"Processing threat")

                common_environment = (
                    GetEnvironmentCommonFactory.create_environment_manager(
                        siemplify,
                        dotted_field_to_underscored(environment_field_name),
                        environment_regex_pattern,
                    )
                )
                alert_info = threat.get_alert_info(
                    common_environment, device_product_field=device_product_field_name
                )

                if is_overflowed(siemplify, alert_info, is_test_run):
                    siemplify.LOGGER.info(
                        f"{alert_info.rule_generator}-{alert_info.ticket_id}-{alert_info.environment}"
                        f"-{alert_info.device_product} found as overflow alert. Skipping..."
                    )
                    continue

                processed_threats.append(alert_info)
                siemplify.LOGGER.info(f"Threat {threat.hash_id} was created.")

            except Exception as e:
                siemplify.LOGGER.error(f"Failed to process threat {threat.hash_id}")
                siemplify.LOGGER.exception(e)
                if is_test_run:
                    raise

        if not is_test_run and all_threats:
            siemplify.LOGGER.info("Saving existing ids.")
            write_ids(
                siemplify,
                list(set(existing_ids + [threat.hash_id for threat in all_threats])),
            )
            save_timestamp(siemplify=siemplify, alerts=all_threats)

    except Exception as err:
        siemplify.LOGGER.error(f"Got exception on main handler. Error: {err}")
        siemplify.LOGGER.exception(err)
        if is_test_run:
            raise

    siemplify.LOGGER.info(f"Created total of {len(processed_threats)} cases")
    siemplify.LOGGER.info("------------------- Main - Finished -------------------")
    siemplify.return_package(processed_threats)


if __name__ == "__main__":
    is_test_run = not (len(sys.argv) < 2 or sys.argv[1] == "True")
    main(is_test_run)
