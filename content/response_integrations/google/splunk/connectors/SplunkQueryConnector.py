# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from __future__ import annotations
import sys
import uuid
from itertools import chain

from EnvironmentCommon import GetEnvironmentCommonFactory
from soar_sdk.SiemplifyConnectors import SiemplifyConnectorExecution
from soar_sdk.SiemplifyConnectorsDataModel import AlertInfo
from soar_sdk.SiemplifyUtils import output_handler, unix_now
from ..core.SplunkManager import SplunkManager
from TIPCommon.extraction import extract_connector_param
from TIPCommon.smp_io import read_ids, write_ids
from TIPCommon.utils import is_overflowed
from ..core.UtilsManager import (
    clean_duplicated_keys,
    get_last_success_time_for_queries,
    get_query_identifier,
    is_approaching_timeout,
    save_query_timestamp,
)
from ..core.constants import DEFAULT_DEVICE_VENDOR, QUERY_CONNECTOR_SCRIPT_NAME


connector_starting_time = unix_now()


def get_alert_info(
    events,
    device_product_field_name,
    rule_generator_field_name,
    query,
    alert_name_field_name,
    environment_common,
):
    alert_info = AlertInfo()

    event_json = list(map(clean_duplicated_keys, [event.to_flat() for event in events]))
    alert_info.start_time = events[0].timestamp
    alert_info.end_time = events[-1].timestamp
    alert_info.rule_generator = event_json[0].get(rule_generator_field_name, query)
    alert_info.device_product = event_json[0].get(
        device_product_field_name, "Splunk Query"
    )
    alert_info.name = event_json[0].get(alert_name_field_name, f"Query: {query}")
    alert_info.events = event_json

    alert_info.environment = environment_common.get_environment(events[0].to_flat())
    alert_info.device_vendor = DEFAULT_DEVICE_VENDOR
    alert_info.ticket_id = f"{alert_info.start_time}_{str(uuid.uuid4())}"
    alert_info.display_id = alert_info.identifier = alert_info.ticket_id
    alert_info.extensions = {"query": query}

    return alert_info


def split_events_to_lists(events_list, aggregate_events_query):
    """
    Split event list to events lists list.
    :param events_list: {list} List of dicts.
    :param aggregate_events_query: {}
    :return:
    """
    if aggregate_events_query:
        return [events_list] if events_list else []

    return [[event] for event in events_list]


@output_handler
def main(is_test_run=False):
    """
    :param is_test_run: run test flow of real flow (timestamp updating is the differencee)
    :return: -
    """
    siemplify = SiemplifyConnectorExecution()
    siemplify.script_name = QUERY_CONNECTOR_SCRIPT_NAME
    cases, processed_events = [], []

    if is_test_run:
        siemplify.LOGGER.info(
            '***** This is an "IDE Play Button"\\"Run Connector once" test run ******'
        )

    try:
        server_address = extract_connector_param(siemplify, param_name="Api Root")
        username = extract_connector_param(siemplify, param_name="Username")
        password = extract_connector_param(siemplify, param_name="Password")
        api_token = extract_connector_param(siemplify, param_name="API Token")
        verify_ssl = extract_connector_param(
            siemplify, param_name="Verify SSL", default_value=False, input_type=bool
        )
        ca_certificate = extract_connector_param(
            siemplify, param_name="CA Certificate File", print_value=False
        )

        environment_field_name = extract_connector_param(
            siemplify, param_name="Environment Field Name"
        )
        environment_regex_pattern = extract_connector_param(
            siemplify, param_name="Environment Regex Pattern"
        )
        device_product_field_name = extract_connector_param(
            siemplify, param_name="DeviceProductField", is_mandatory=True
        )
        rule_generator_field_name = extract_connector_param(
            siemplify, param_name="Rule Generator Field", is_mandatory=True
        )
        alert_name_field_name = extract_connector_param(
            siemplify, param_name="Alert Name Field Name", is_mandatory=True
        )
        event_limit = extract_connector_param(
            siemplify,
            param_name="Events Count Limit Per Query",
            input_type=int,
            default_value=100,
        )
        event_limit = 1 if is_test_run else event_limit
        max_days_backwards = extract_connector_param(
            siemplify, param_name="Max Days Backwards", input_type=int, default_value=1
        )
        aggregate_events_query = extract_connector_param(
            siemplify,
            param_name="Aggregate Events Query",
            default_value=False,
            is_mandatory=True,
            input_type=bool,
        )
        python_process_timeout = extract_connector_param(
            siemplify,
            param_name="PythonProcessTimeout",
            input_type=int,
            is_mandatory=True,
            print_value=True,
        )
        queries_whitelist = siemplify.whitelist

        splunk_manager = SplunkManager(
            server_address=server_address,
            username=username,
            password=password,
            api_token=api_token,
            ca_certificate=ca_certificate,
            verify_ssl=verify_ssl,
            siemplify_logger=siemplify.LOGGER,
        )

        siemplify.LOGGER.info("Reading already existing alerts ids...")
        existing_ids = read_ids(siemplify)
        siemplify.LOGGER.info(f"Loaded {len(existing_ids)} existing ids")
        query_timestamp = get_last_success_time_for_queries(
            siemplify,
            queries=queries_whitelist,
            offset_with_metric={"days": max_days_backwards},
        )
        query_events = {}
        force_save_timestamp = {}
        environment_common = GetEnvironmentCommonFactory.create_environment_manager(
            siemplify, environment_field_name, environment_regex_pattern
        )

        for query in queries_whitelist:
            query_identifier = get_query_identifier(query)
            try:
                if is_approaching_timeout(
                    python_process_timeout, connector_starting_time
                ):
                    siemplify.LOGGER.info(
                        "Timeout is approaching. Connector will gracefully exit"
                    )
                    break

                siemplify.LOGGER.info(f'\nQuerying Splunk for "{query}"')
                query_events[query_identifier] = []

                earliest_time = query_timestamp.get(query_identifier)
                latest_time = min(earliest_time + 86400000, unix_now())
                events = splunk_manager.get_events_by_query(
                    query,
                    earliest_time=earliest_time / 1000,
                    latest_time=latest_time / 1000,
                    revers_limit=max(event_limit, 100),
                )

                siemplify.LOGGER.info(
                    f"Found {len(events)} events for query "
                    f'"{query}" with time range '
                    f"{str(earliest_time)} - {str(latest_time)}"
                )
                # exclude existing event ids
                events = list(
                    filter(lambda event: event.event_id not in existing_ids, events)
                )
                siemplify.LOGGER.info(
                    "Events count after removing "
                    f"already processed events: {len(events)}"
                )
                # Apply user limit
                events = events[:event_limit]
                if not events:
                    force_save_timestamp[query_identifier] = latest_time

                # split events into lists.Depends on aggregation.

                for event_list in split_events_to_lists(events, aggregate_events_query):
                    try:
                        alert_info = get_alert_info(
                            events=event_list,
                            query=query,
                            device_product_field_name=device_product_field_name,
                            rule_generator_field_name=rule_generator_field_name,
                            alert_name_field_name=alert_name_field_name,
                            environment_common=environment_common,
                        )
                        siemplify.LOGGER.info(
                            "\nProcessed events timestamps are "
                            f'{", ".join([str(event.timestamp) for event in event_list])} '
                            "with timestamp"
                        )

                        query_events[query_identifier].extend(event_list)
                        # Check if overflowed.
                        if is_overflowed(siemplify, alert_info, is_test_run):
                            siemplify.LOGGER.info(
                                "{alert_name}-"
                                "{alert_identifier}-"
                                "{environment}-{product} found as overflow alert. "
                                "Skipping. ".format(
                                    alert_name=alert_info.rule_generator,
                                    alert_identifier=alert_info.ticket_id,
                                    environment=alert_info.environment,
                                    product=alert_info.device_product,
                                )
                            )
                            # If is overflowed we should skip
                            continue

                        processed_events.append(alert_info)
                        siemplify.LOGGER.info(
                            "\nCase with display id "
                            f'"{alert_info.display_id}" was created.'
                        )

                    except Exception as err:
                        error_massage = (
                            f"\nError occurred creating case package, Error: {err}"
                        )
                        siemplify.LOGGER.error(error_massage)
                        siemplify.LOGGER.exception(err)
                        if is_test_run:
                            raise

            except Exception as err:
                error_massage = (
                    f'\nError occurred running query "{query}", Error: {err}'
                )
                siemplify.LOGGER.error(error_massage)
                siemplify.LOGGER.exception(err)
                if is_test_run:
                    raise

        if is_test_run:
            siemplify.LOGGER.info(
                f'Maximum event limit({event_limit}) for each query reached! "test run"'
            )
            siemplify.LOGGER.info(
                " ------------ Finish Splunk Query Connector Test ------------ "
            )
        else:
            save_query_timestamp(
                siemplify,
                query_alerts=query_events,
                force_save_timestamp=force_save_timestamp,
            )
            write_ids(
                siemplify,
                existing_ids
                + [
                    event.event_id
                    for event in chain.from_iterable(query_events.values())
                ],
            )
            siemplify.LOGGER.info(
                " ------------ Connector Finished Iteration ------------ "
            )

        siemplify.LOGGER.info(f"{len(processed_events)} cases created.")
        siemplify.return_package(processed_events)

    except Exception as err:
        error_message = f"Got exception on main handler. Error: {err}"
        siemplify.LOGGER.error(error_message)
        siemplify.LOGGER.exception(err)
        if is_test_run:
            raise
        siemplify.LOGGER.info("\n")


if __name__ == "__main__":
    is_test = not (len(sys.argv) < 2 or sys.argv[1] == "True")
    main(is_test)
