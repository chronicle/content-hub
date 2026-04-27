from __future__ import annotations
import sys

from soar_sdk.SiemplifyConnectors import SiemplifyConnectorExecution
from soar_sdk.SiemplifyUtils import output_handler, unix_now

from EnvironmentCommon import GetEnvironmentCommonFactory
from TIPCommon.consts import TIMEOUT_THRESHOLD
from TIPCommon.extraction import extract_connector_param
from TIPCommon.filters import pass_whitelist_filter
from TIPCommon.smp_io import read_ids_by_timestamp, write_ids_with_timestamp
from TIPCommon.smp_time import get_last_success_time, is_approaching_timeout
from TIPCommon.utils import is_overflowed

from ..core.AzureSecurityCenterManager import AzureSecurityCenterManager
from ..core.consts import (
    CONNECTOR_NAME,
    DEFAULT_MAX_ALERTS_TO_FETCH,
    DEFAULT_MAX_HOURS_BACKWARDS,
    DEFAULT_LOWEST_SEVERITY_TO_FETCH,
    DEFAULT_CONNECTOR_SCRIPT_EXECUTION_TIME,
    SEVERITIES_MAP,
    TIME_FORMAT,
    MAX_EVENTS_PER_ALERT,
    HOURS_LIMIT_IN_IDS_FILE,
)
from ..core.exceptions import AzureSecurityCenterValidationException
from ..core import utils


@output_handler
def main(is_test_run):
    connector_starting_time = unix_now()
    processed_alerts = []
    siemplify = SiemplifyConnectorExecution()  # Siemplify main SDK wrapper
    siemplify.script_name = CONNECTOR_NAME

    try:
        if is_test_run:
            siemplify.LOGGER.info(
                '***** This is an "IDE Play Button"\\"Run Connector once" test run ******'
            )

        siemplify.LOGGER.info(
            "------------------- Main - Param Init -------------------"
        )

        client_id = extract_connector_param(
            siemplify,
            param_name="Client ID",
            default_value="",
            is_mandatory=True,
            print_value=True,
        )
        client_secret = extract_connector_param(
            siemplify, param_name="Client Secret", is_mandatory=True, print_value=False
        )
        username = extract_connector_param(
            siemplify,
            param_name="Username",
            default_value="",
            is_mandatory=False,
            print_value=True,
        )
        password = extract_connector_param(
            siemplify, param_name="Password", is_mandatory=False, print_value=False
        )
        subscription_id = extract_connector_param(
            siemplify, param_name="Subscription ID", is_mandatory=True, print_value=True
        )
        tenant_id = extract_connector_param(
            siemplify, param_name="Tenant ID", is_mandatory=True, print_value=True
        )
        refresh_token = extract_connector_param(
            siemplify, param_name="Refresh Token", is_mandatory=False, print_value=False
        )
        max_alerts_to_fetch = extract_connector_param(
            siemplify,
            param_name="Max Alerts To Fetch",
            is_mandatory=False,
            input_type=int,
            print_value=True,
            default_value=DEFAULT_MAX_ALERTS_TO_FETCH,
        )
        hours_backwards = extract_connector_param(
            siemplify,
            param_name="Max Hours Backwards",
            is_mandatory=False,
            input_type=int,
            print_value=True,
            default_value=DEFAULT_MAX_HOURS_BACKWARDS,
        )
        min_severity = extract_connector_param(
            siemplify,
            param_name="Lowest Severity To Fetch",
            is_mandatory=False,
            print_value=True,
            default_value=DEFAULT_LOWEST_SEVERITY_TO_FETCH,
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
        verify_ssl = extract_connector_param(
            siemplify,
            param_name="Verify SSL",
            default_value=False,
            input_type=bool,
            is_mandatory=True,
        )
        python_process_timeout = extract_connector_param(
            siemplify,
            param_name="PythonProcessTimeout",
            input_type=int,
            is_mandatory=False,
            default_value=DEFAULT_CONNECTOR_SCRIPT_EXECUTION_TIME,
            print_value=True,
        )

        whitelist_as_a_blacklist = extract_connector_param(
            siemplify,
            "Use whitelist as a blacklist",
            default_value=False,
            is_mandatory=True,
            input_type=bool,
            print_value=True,
        )

        whitelist = siemplify.whitelist

        siemplify.LOGGER.info("------------------- Main - Started -------------------")

        if min_severity not in SEVERITIES_MAP:
            # Severity value is invalid
            raise AzureSecurityCenterValidationException(
                "Severity {} is invalid. Valid values are: Low, Medium, High"
            )

        if max_alerts_to_fetch <= 0:
            raise AzureSecurityCenterValidationException(
                "Max Alerts To Fetch {} parameter cannot be non-positive."
            )

        severities = SEVERITIES_MAP[min_severity]

        manager = AzureSecurityCenterManager(
            client_id=client_id,
            client_secret=client_secret,
            username=username,
            password=password,
            subscription_id=subscription_id,
            verify_ssl=verify_ssl,
            tenant_id=tenant_id,
            siemplify=siemplify,
            refresh_token=refresh_token,
        )

        # Read already existing alerts ids
        siemplify.LOGGER.info("Loading existing ids from IDS file.")
        existing_ids = read_ids_by_timestamp(
            siemplify,
            offset_in_hours=HOURS_LIMIT_IN_IDS_FILE,
            default_value_to_return={},
        )
        siemplify.LOGGER.info(f"Found {len(existing_ids)} existing ids in ids.json")

        last_success_time = get_last_success_time(
            siemplify=siemplify, offset_with_metric={"hours": hours_backwards}
        )

        siemplify.LOGGER.info(
            f"Fetching Alerts since {utils.datetime_to_string(last_success_time, time_format=TIME_FORMAT)}"
        )

        fetched_alerts = []  # list of fetched alerts
        # Pull filtered alert ids from Microsoft Graph
        filtered_alerts = manager.get_alert_ids(
            start_time=utils.datetime_to_string(
                last_success_time, time_format=TIME_FORMAT
            ),
            existing_ids=existing_ids,
            categories=whitelist,
            whitelist_as_blacklist=whitelist_as_a_blacklist,
            severities=severities,
            limit=max_alerts_to_fetch,
        )

        filtered_alerts = sorted(
            filtered_alerts, key=lambda filtered_alert: filtered_alert.create_time_ms
        )

        siemplify.LOGGER.info(
            f"Found {len(filtered_alerts)} new alerts since {last_success_time.isoformat()}."
        )

        if is_test_run:
            siemplify.LOGGER.info("This is a TEST run. Only 1 alert will be processed.")
            filtered_alerts = filtered_alerts[:1]

        for alert in filtered_alerts:
            try:
                if len(processed_alerts) >= max_alerts_to_fetch:
                    # Provide slicing for the alarms amount.
                    siemplify.LOGGER.info(
                        "Reached max number of alerts cycle. No more alerts will be processed in this cycle."
                    )
                    break

                if is_approaching_timeout(
                    connector_starting_time=connector_starting_time,
                    python_process_timeout=python_process_timeout,
                    timeout_threshold=TIMEOUT_THRESHOLD,
                ):
                    siemplify.LOGGER.info(
                        "Timeout is approaching. Connector will gracefully exit."
                    )
                    break

                siemplify.LOGGER.info(f"Started processing alert {alert.id}")

                # Filter whitelisted alerts
                if not pass_whitelist_filter(
                    siemplify=siemplify,
                    whitelist_as_a_blacklist=whitelist_as_a_blacklist,
                    whitelist=whitelist,
                    model=alert,
                    model_key="category",
                ):
                    siemplify.LOGGER.info(
                        f"Alert {alert.id} did not pass whitelist filter. Skipping..."
                    )
                    continue

                detailed_alert = manager.get_alert_details(
                    alert_id=alert.id, location=alert.location
                )

                environment_common = (
                    GetEnvironmentCommonFactory.create_environment_manager(
                        siemplify=siemplify,
                        environment_field_name=environment_field_name,
                        environment_regex_pattern=environment_regex_pattern,
                    )
                )

                alert_infos = (
                    []
                )  # list of created AlertInfo objects out of filtered alert
                # Process incident alerts
                if detailed_alert.is_incident:

                    siemplify.LOGGER.info(
                        f"Alert {detailed_alert.alert_id} is an incident. Fetching all related events."
                    )
                    events = []  # incident alert events

                    # get details about all the system alert ids of each entity item
                    for entity_incident in detailed_alert.entities_obj:
                        siemplify.LOGGER.info(
                            f"Incident {entity_incident.display_name} has {len(entity_incident.system_alert_ids)} system alert ids"
                        )
                        # Get details about system alert ids of incident entity
                        for entity_alert_id in entity_incident.system_alert_ids:
                            try:
                                siemplify.LOGGER.info(
                                    f"Getting alert details for incident entity system alert id {entity_alert_id}"
                                )
                                entity_alert_details = manager.get_alert_details(
                                    alert_id=entity_alert_id,
                                    location=entity_incident.location,
                                )
                                siemplify.LOGGER.info(
                                    f"Successfully got details for incident entity {entity_alert_id} in location {entity_incident.location}"
                                )

                                events.extend(
                                    detailed_alert.to_events(
                                        entity_incident, entity_alert_details
                                    )
                                )

                            except Exception as e:
                                siemplify.LOGGER.error(
                                    f"Failed to fetch and process events for Incident entity alert {entity_alert_id}"
                                )
                                siemplify.LOGGER.exception(e)

                    # Slice events if exceeding max events per alert
                    sliced_events = utils.slice_list_to_max_sublists(
                        events, MAX_EVENTS_PER_ALERT
                    )
                    siemplify.LOGGER.info(
                        f"Created total of {len(events)} events for incident alert {detailed_alert.alert_id}"
                    )

                else:
                    # Non-Incident alert will have event for each alert entity with the same data
                    # Slice events if exceeding max events per alert
                    sliced_events = utils.slice_list_to_max_sublists(
                        detailed_alert.to_events(), MAX_EVENTS_PER_ALERT
                    )

                # Create AlertInfos for the alert
                for events_chunk in sliced_events:
                    alert_infos.append(
                        detailed_alert.as_alert_info(
                            environment_common, events=events_chunk
                        )
                    )

                # Add alert to processed findings (regardless of overflow status) to mark it as processed
                existing_ids.update({alert.id: unix_now()})
                fetched_alerts.append(alert)

                for alert_info in alert_infos:
                    if is_overflowed(
                        siemplify=siemplify,
                        alert_info=alert_info,
                        is_test_run=is_test_run,
                    ):
                        siemplify.LOGGER.info(
                            f"{alert_info.rule_generator}-{alert_info.ticket_id}-{alert_info.environment}-{alert_info.device_product} found as overflow alert. Skipping."
                        )
                        # If is overflowed we should skip
                        continue
                    processed_alerts.append(alert_info)

                siemplify.LOGGER.info(f"Alert {alert.id} was created.")
                siemplify.LOGGER.info(
                    f"Alert {alert.create_time} ({alert.create_time_ms} timestamp)"
                )
            except Exception as e:
                siemplify.LOGGER.error(f"Failed to process alert {alert.id}")
                siemplify.LOGGER.exception(e)

                if is_test_run:
                    raise

            siemplify.LOGGER.info(f"Finished processing alert {alert.id}")

        if not is_test_run:
            if fetched_alerts:
                siemplify.LOGGER.info("Saving existing ids.")
                write_ids_with_timestamp(siemplify=siemplify, ids=existing_ids)
                siemplify.save_timestamp(
                    new_timestamp=fetched_alerts[-1].create_time_ms
                )
            else:
                siemplify.LOGGER.info("No fetched alerts.")

        siemplify.LOGGER.info(f"Created total of {len(processed_alerts)} cases")
        siemplify.LOGGER.info("------------------- Main - Finished -------------------")
        siemplify.return_package(processed_alerts)

    except Exception as err:
        siemplify.LOGGER.error(f"Got exception on main handler. Error: {err}")
        siemplify.LOGGER.exception(err)
        if is_test_run:
            raise


if __name__ == "__main__":
    # Connectors are run in iterations. The interval is configurable from the ConnectorsScreen UI.
    is_test = not (len(sys.argv) < 2 or sys.argv[1] == "True")
    main(is_test)
