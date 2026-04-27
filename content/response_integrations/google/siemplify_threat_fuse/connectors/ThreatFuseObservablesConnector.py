from __future__ import annotations
import sys
import uuid
from typing import List

from EnvironmentCommon import EnvironmentHandle
from soar_sdk.SiemplifyConnectors import SiemplifyConnectorExecution
from soar_sdk.SiemplifyConnectorsDataModel import AlertInfo
from soar_sdk.SiemplifyUtils import output_handler, unix_now
from TIPCommon import extract_connector_param
from ..core import consts
from ..core import datamodels
from ..core.ThreatFuseManager import ThreatFuseManager
from ..core.exceptions import ThreatFuseValidationException
from ..core.utils import (
    get_last_success_time,
    is_overflowed,
    save_timestamp,
    get_environment_common,
    read_ids,
    write_ids,
    is_approaching_timeout,
    load_csv_to_list,
    load_valid_csv_to_list,
    convert_datetime_to_string,
)

CONNECTOR_NAME = f"{consts.INTEGRATION_NAME} - Observables Connector"


def calculate_priority(observables_group: List[datamodels.Indicator]):
    """
    Calculate alert's siemplify priority based on highest observables in the alert.
    :param observables_group: {[datamodels.Indicator]} list of observables
    :return: Highest priority among the observables
    """
    return max([observable.siemplify_severity for observable in observables_group])


def create_alert_info(
    environment_common: EnvironmentHandle,
    is_source_feed_grouped: bool,
    source_grouping_identifier: str,
    observables_group: List[datamodels.Indicator],
):
    """
    Create Alert from observables group. Alert's id is the oldest observable id. Start time of the alert is the
    oldest 'modified_ts' time of an observable in group and End time is latest 'modified_ts' timestamp
    of the observable in group. All observables in observables group are events of the alert.
    :param environment_common: {EnvironmentHandle}
    :param is_source_feed_grouped: {bool} True if observables in group are grouped by feed id, otherwise False
    :param source_grouping_identifier: {str} AlertInfo().source_grouping_identifier parameter
    :param observables_group: {[datamodels.Indicator]} list of observables data models
    :param device_product: {str} device product name
    :return: {AlertInfo} an Alert with all observables as events
    """
    sorted_observables = sorted(
        observables_group, key=lambda observable: observable.modified_ts_ms
    )

    alert_info = AlertInfo()
    alert_info.ticket_id = sorted_observables[0].id
    alert_info.display_id = str(uuid.uuid4())

    alert_info.name = (
        f"New {len(observables_group)} Observables"
        if is_source_feed_grouped
        else consts.ALERT_NAME_WITHOUT_SOURCE_GROUPING
    )
    alert_info.device_vendor = consts.VENDOR
    alert_info.device_product = consts.PRODUCT

    alert_info.priority = calculate_priority(observables_group)
    alert_info.rule_generator = consts.RULE_GENERATOR

    alert_info.start_time = sorted_observables[
        0
    ].modified_ts_ms  # oldest observable's time
    alert_info.end_time = sorted_observables[
        -1
    ].modified_ts_ms  # latest observable's  time

    alert_info.events = [observable.as_event() for observable in observables_group]
    alert_info.environment = environment_common.get_environment(alert_info.events[0])
    alert_info.source_grouping_identifier = source_grouping_identifier

    return alert_info


@output_handler
def main(is_test_run):
    connector_starting_time = unix_now()
    processed_alerts = []
    processed_observables = []
    siemplify = SiemplifyConnectorExecution()  # Siemplify main SDK wrapper
    siemplify.script_name = CONNECTOR_NAME

    if is_test_run:
        siemplify.LOGGER.info(
            '***** This is an "IDE Play Button"\\"Run Connector once" test run ******'
        )

    siemplify.LOGGER.info("------------------- Main - Param Init -------------------")

    # Siemplify Threatfuse credential parameters
    api_root = extract_connector_param(
        siemplify, param_name="API Root", is_mandatory=True
    )
    api_key = extract_connector_param(
        siemplify, param_name="API Key", is_mandatory=True
    )
    email_address = extract_connector_param(
        siemplify, param_name="Email Address", is_mandatory=True
    )

    # Connector parameters
    python_process_timeout = extract_connector_param(
        siemplify,
        param_name="PythonProcessTimeout",
        is_mandatory=False,
        input_type=int,
        default_value=consts.DEFAULT_SCRIPT_TIMEOUT,
    )

    verify_ssl = extract_connector_param(
        siemplify, param_name="Verify SSL", default_value=False, input_type=bool
    )

    product_field_name = extract_connector_param(
        siemplify,
        param_name="DeviceProductField",
        default_value=consts.PRODUCT,
        print_value=True,
    )

    environment_field_name = extract_connector_param(
        siemplify,
        param_name="Environment Field Name",
        default_value="",
        print_value=True,
    )
    environment_regex_pattern = extract_connector_param(
        siemplify,
        param_name="Environment Regex Pattern",
        default_value="",
        print_value=True,
    )

    source_feed_ids = extract_connector_param(
        siemplify,
        param_name="Source Feed Filter",
        is_mandatory=False,
        default_value=None,
    )
    observable_types = extract_connector_param(
        siemplify,
        param_name="Observable Type Filter",
        is_mandatory=False,
        default_value=consts.DEFAULT_OBSERVABLE_TYPE_FILTER,
        print_value=True,
    )
    observable_statuses = extract_connector_param(
        siemplify,
        param_name="Observable Status Filter",
        is_mandatory=False,
        default_value=consts.DEFAULT_OBSERVABLE_STATUS,
        print_value=True,
    )
    threat_types = extract_connector_param(
        siemplify,
        param_name="Threat Type Filter",
        is_mandatory=False,
        default_value=None,
        print_value=True,
    )
    trusted_circle_filter = extract_connector_param(
        siemplify,
        param_name="Trusted Circle Filter",
        is_mandatory=False,
        default_value=None,
    )
    tags = extract_connector_param(
        siemplify,
        param_name="Tag Name Filter",
        print_value=True,
        is_mandatory=False,
        default_value=None,
    )

    source_feed_grouping = extract_connector_param(
        siemplify,
        param_name="Source Feed Grouping",
        is_mandatory=False,
        input_type=bool,
        print_value=True,
        default_value=False,
    )

    max_observables_per_alert = extract_connector_param(
        siemplify,
        param_name="Max Observables Per Alert",
        input_type=int,
        is_mandatory=False,
        default_value=consts.MAX_OBSERVABLES_PER_ALERT,
        print_value=True,
    )

    days_backwards = extract_connector_param(
        siemplify,
        param_name="Fetch Max Days Backwards",
        input_type=int,
        is_mandatory=False,
        default_value=consts.DEFAULT_MAX_DAYS_BACKWARDS,
        print_value=True,
    )

    lowest_confidence_to_fetch = extract_connector_param(
        siemplify,
        param_name="Lowest Confidence To Fetch",
        input_type=int,
        is_mandatory=True,
        default_value=consts.DEFAULT_LOWEST_CONFIDENCE_TO_FETCH,
        print_value=True,
    )

    min_severity = extract_connector_param(
        siemplify,
        param_name="Lowest Severity To Fetch",
        is_mandatory=True,
        print_value=True,
        default_value=consts.DEFAULT_LOWEST_SEVERITY_TO_FETCH,
    )

    if min_severity not in consts.SEVERITIES_MAP:
        # Severity value is invalid
        raise Exception(
            f"Severity {min_severity} is invalid. Valid values are: {list(consts.SEVERITIES.values())}"
        )

    if max_observables_per_alert > consts.MAX_OBSERVABLES_PER_ALERT:
        siemplify.LOGGER.info(
            f"'Max Observables Per Alert' parameter is higher than allowed max {consts.MAX_OBSERVABLES_PER_ALERT}. Using max value."
        )
        max_observables_per_alert = consts.MAX_OBSERVABLES_PER_ALERT

    if max_observables_per_alert < 0:
        raise ThreatFuseValidationException(
            "Max Observables Per Alert parameter must be a positive number."
        )

    # validate filters values
    observable_types = (
        load_valid_csv_to_list(
            observable_types, "Observable Type Filter", consts.OBSERVABLE_TYPES
        )
        if observable_types
        else []
    )
    observable_statuses = (
        load_valid_csv_to_list(
            observable_statuses, "Observable Status Filter", consts.OBSERVABLE_STATUSES
        )
        if observable_statuses
        else []
    )
    source_feed_ids = (
        load_csv_to_list(source_feed_ids, "Source Feed Filter")
        if source_feed_ids
        else []
    )
    tags = load_csv_to_list(tags, "Tag Name Filter") if tags else []
    trusted_circle_filter = (
        load_csv_to_list(trusted_circle_filter, "Trusted Circle Filter")
        if trusted_circle_filter
        else []
    )
    threat_types = (
        load_valid_csv_to_list(
            threat_types,
            "Threat Type Filter",
            list(consts.THREAT_TYPE_MAPPINGS.values()),
        )
        if threat_types
        else []
    )

    lowest_confidence_to_fetch = (
        consts.MIN_CONFIDENCE
        if lowest_confidence_to_fetch < consts.MIN_CONFIDENCE
        else lowest_confidence_to_fetch
    )
    lowest_confidence_to_fetch = (
        consts.MAX_CONFIDENCE
        if lowest_confidence_to_fetch > consts.MAX_CONFIDENCE
        else lowest_confidence_to_fetch
    )

    severities = consts.SEVERITIES_MAP[min_severity]

    whitelist_as_a_blacklist = extract_connector_param(
        siemplify,
        "Use whitelist as a blacklist",
        is_mandatory=True,
        default_value=False,
        input_type=bool,
        print_value=True,
    )
    whitelist_filter_type = (
        consts.BLACKLIST_FILTER if whitelist_as_a_blacklist else consts.WHITELIST_FILTER
    )

    whitelist = siemplify.whitelist

    try:
        siemplify.LOGGER.info("------------------- Main - Started -------------------")

        manager = ThreatFuseManager(
            api_root=api_root,
            api_key=api_key,
            email_address=email_address,
            verify_ssl=verify_ssl,
        )

        siemplify.LOGGER.info(f"Connecting to {consts.INTEGRATION_NAME}")
        manager.test_connectivity()  # validate credentials / connectivity
        siemplify.LOGGER.info(f"Successfully connected to {consts.INTEGRATION_NAME}")

        # Read already existing alerts ids
        siemplify.LOGGER.info("Loading existing ids from IDS file.")
        existing_ids = read_ids(siemplify, ids_file_name=consts.IDS_FILE)
        siemplify.LOGGER.info(f"Found {len(existing_ids)} existing ids in ids.json")

        last_success_time = get_last_success_time(
            siemplify=siemplify, offset_with_metric={"days": days_backwards}
        )

        siemplify.LOGGER.info(
            f"Fetching observables since {last_success_time.isoformat()}"
        )

        # Fetch all available observables older than last timestamp of successfully processed alert
        # Observables will be filtered by connector parameters
        fetched_observables = manager.get_filtered_indicators(
            confidence=lowest_confidence_to_fetch,
            severities=severities,
            feed_ids=source_feed_ids,
            tags=tags,
            observable_types=observable_types,
            observable_statuses=observable_statuses,
            threat_types=threat_types,
            trusted_circle_ids=trusted_circle_filter,
            last_timestamp=convert_datetime_to_string(last_success_time),
        )

        filtered_observables = []
        ignored_observables = []  # observables that didn't pass whitelist filter

        new_observables = [
            observable
            for observable in fetched_observables
            if observable.uuid not in existing_ids
        ]

        for observable in new_observables:  # Filter whitelist observables
            if not pass_whitelist_filter(
                siemplify, observable, whitelist, whitelist_filter_type
            ):
                # Save ID to whitelist to prevent processing it in the future
                ignored_observables.append(observable)
            else:
                filtered_observables.append(observable)

        siemplify.LOGGER.info(
            f"Found new {len(filtered_observables)} observables out of total of {len(filtered_observables) + len(ignored_observables)} observables."
        )

        # Group observables by feed_id if <source_feed_grouping> is True
        # Each group will be no more than <max_observables_per_alert> in size
        grouped_observables = manager.parser.map_observables_to_feed_group(
            observables=filtered_observables,
            max_observables_per_group=max_observables_per_alert,
            source_feed_grouping=source_feed_grouping,
        )

        if is_test_run:
            siemplify.LOGGER.info(
                "This is a TEST run. Only 3 alerts will be processed."
            )
            grouped_observables = grouped_observables[:3]

        # Process observables by groups. Each observables group represented as events in a single siemplify alert
        for group in grouped_observables:
            try:
                if is_approaching_timeout(
                    python_process_timeout,
                    connector_starting_time,
                    consts.TIMEOUT_THRESHOLD,
                ):
                    siemplify.LOGGER.info(
                        "Timeout is approaching. Connector will gracefully exit"
                    )
                    break

                if len(group) == 0:  # skip empty groups
                    continue

                existing_ids.extend([observable.uuid for observable in group])
                processed_observables.extend(group)

                siemplify.LOGGER.info(
                    f"Creating AlertInfo for alert group {group[0].id}"
                )
                alert_info = create_alert_info(
                    environment_common=get_environment_common(
                        siemplify, environment_field_name, environment_regex_pattern
                    ),
                    is_source_feed_grouped=source_feed_grouping,
                    source_grouping_identifier=str(connector_starting_time),
                    observables_group=group,
                )
                siemplify.LOGGER.info(
                    f"Finished creating AlertInfo for alert group {group[0].id}"
                )

                siemplify.LOGGER.info(
                    f"Alert ID: {alert_info.ticket_id}, First Observable Time: {alert_info.start_time}, Last Observable Time: {alert_info.end_time}, Severity: {alert_info.priority}, Num of observables in Alert: {len(alert_info.events)}"
                )

                if is_overflowed(siemplify, alert_info, is_test_run):
                    siemplify.LOGGER.info(
                        f"{alert_info.rule_generator}-{alert_info.ticket_id}-{alert_info.environment}-{alert_info.device_product} found as overflow alert. Skipping."
                    )
                    # If is overflowed we should skip
                    continue

                processed_alerts.append(alert_info)
                siemplify.LOGGER.info(f"Alert {alert_info.ticket_id} was created.")

            except Exception as e:
                siemplify.LOGGER.error(f"Failed to process alert {group[0].id}")
                siemplify.LOGGER.exception(e)

                if is_test_run:
                    raise

        if not is_test_run:
            siemplify.LOGGER.info("Saving existing ids.")
            write_ids(
                siemplify,
                ids=existing_ids,
                ids_file_name=consts.IDS_FILE,
                limit_ids_in_ids_file=consts.MAX_IDS_IN_IDS_FILE,
            )
            # Save timestamp based on the processed findings (processed = alert info created, regardless of overflow
            # status) and the ignored findings (= alerts that didn't pass whitelist/blacklist). New timestamp
            # should be the latest among all of those
            save_timestamp(
                siemplify=siemplify,
                alerts=processed_observables + ignored_observables,
                timestamp_key="modified_ts_ms",
            )

    except Exception as err:
        siemplify.LOGGER.error(f"Got exception on main handler. Error: {err}")
        siemplify.LOGGER.exception(err)
        if is_test_run:
            raise

    siemplify.LOGGER.info(f"Created total of {len(processed_alerts)} alerts")
    siemplify.LOGGER.info("------------------- Main - Finished -------------------")
    siemplify.return_package(processed_alerts)


def pass_whitelist_filter(siemplify, event, whitelist, whitelist_filter_type):
    # whitelist filter for observable events
    if whitelist:
        if (
            whitelist_filter_type == consts.BLACKLIST_FILTER
            and event.source
            and event.source in whitelist
        ):
            siemplify.LOGGER.info(
                f"Alert {event.uuid} with rule: {event.source} did not pass blacklist filter."
            )
            return False

        if (
            whitelist_filter_type == consts.WHITELIST_FILTER
            and event.source
            and event.source not in whitelist
        ):
            siemplify.LOGGER.info(
                f"Alert {event.uuid} with rule: {event.source} did not pass whitelist filter."
            )
            return False

    return True


if __name__ == "__main__":
    # Connectors are run in iterations. The interval is configurable from the ConnectorsScreen UI.
    is_test = not (len(sys.argv) < 2 or sys.argv[1] == "True")
    main(is_test)
