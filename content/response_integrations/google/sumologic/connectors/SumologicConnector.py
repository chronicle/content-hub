# ==============================================================================
# title           :SumologicConnector.py
# description     :This Module contain Sumologic Connector logic.
# author          :avital@siemplify.co
# date            :05-11-18
# python_version  :2.7
# API DOCS: https://help.sumologic.com/@api/deki/pages/5856/pdf/APIs.pdf?stylesheet=default,
# https://help.sumologic.com/Beta/APIs/APIs
# ==============================================================================

from __future__ import annotations
import sys
import time
from typing import List

from TIPCommon import extract_connector_param

from soar_sdk.SiemplifyConnectors import SiemplifyConnectorExecution
from soar_sdk.SiemplifyUtils import output_handler, unix_now
from ..core.SumoLogicManager import SumoLogicManager
from ..core.consts import (
    SEARCH_JOB_AWAIT_INTERVAL_SECONDS,
    DEFAULT_MAX_ALERTS,
    QUERY,
    CONNECTOR_NAME,
    DEFAULT_DAYS_BACKWARDS,
)
from ..core.datamodels import SearchMessage
from ..core.utils import (
    load_csv_to_list,
    read_ids,
    is_approaching_timeout,
    write_ids,
    get_last_success_time,
    is_overflowed,
    get_environment_common,
)


class SumologicQueryConnector:
    """
    Sumologic Connector
    """

    def __init__(
        self,
        connector_scope,
        logger,
        sumologic_manager,
        alert_name_field,
        timestamp_field_name,
        device_product_field_name,
        environment_field_name,
    ):
        self.connector_scope = connector_scope
        self.logger = logger
        self.sumologic_manager = sumologic_manager
        self.alert_name_field = alert_name_field
        self.timestamp_field_name = timestamp_field_name
        self.device_product_field_name = device_product_field_name
        self.environment_field_name = environment_field_name

    def create_case(self, alert, environment_field_name, environment_regex_pattern):
        """
        Create AlertInfo
        :param alert: {dict} The alert
        :param environment_field_name: {str} The environment field name
        :param environment_regex_pattern: {str} The environment regex pattern
        :return: {AlertInfo} The created case info
        """
        environment_common = get_environment_common(
            self.connector_scope, environment_field_name, environment_regex_pattern
        )
        return alert.get_alert_info(
            self.timestamp_field_name,
            self.device_product_field_name,
            self.alert_name_field,
            environment_common,
        )

    def get_alerts(
        self,
        limit: int,
        since: int,
        to: int,
        existing_ids: List[str],
        indexes: List[str] = [],
        queries: List[str] = [],
    ) -> List[SearchMessage]:
        """
        Get alerts from indexes or queries. Queries if provided have higher priority over indexes
        :param indexes: {[str]} The indexes to fetch alerts from
        :param queries: {[str]} List of queries run
        :param limit: {int} Max alerts to fetch
        :param since: {int} Time to fetch from in milliseconds
        :param to: {int} Time to fetch until in milliseconds
        :param existing_ids: {[str]} Already seen alert ids
        :return: {list} List of found alerts
        """
        alerts = []
        queryables = queries + [QUERY.format(index) for index in indexes]

        for query in queryables:
            try:
                self.logger.info(f"Fetching alerts for query {query}")
                job_id = self.sumologic_manager.search(query, since, to)
                self.logger.info(f"Search ID: {job_id}")

                job_info = self.sumologic_manager.get_job_info(job_id)
                while not job_info.completed:
                    self.logger.info(f"Search {job_id} is not complete.")
                    if job_info.failed:
                        raise Exception(
                            f"Search for index {query} has failed: {self.sumologic_manager.get_job_status(job_id)}"
                        )
                    time.sleep(SEARCH_JOB_AWAIT_INTERVAL_SECONDS)
                    job_info = self.sumologic_manager.get_job_info(job_id)

                self.logger.info(f"Search {job_id} completed. Collecting results.")
                self.logger.info(
                    f"Total messages for result is {job_info.message_count}"
                )
                results = self.sumologic_manager.get_oldest_search_results(
                    job_id=job_id,
                    message_count=job_info.message_count,
                    existing_ids=existing_ids,
                    limit=limit,
                )
                self.logger.info(f"Found {len(results)} alerts for query")
                alerts.extend(results)

                self.sumologic_manager.delete_job(job_id)
                self.logger.info(f"Deleted search job {job_id}")

                if len(alerts) >= limit:
                    # Reached limit - stop fetching
                    break

            except Exception as e:
                self.logger.error(f"Unable to get results for query: {query}")
                self.logger.exception(e)

        return alerts[:limit]


@output_handler
def main_handler(is_test_run):
    connector_scope = SiemplifyConnectorExecution()
    connector_scope.script_name = CONNECTOR_NAME
    connector_starting_time = unix_now()

    fetched_alerts = []
    processed_alerts = []

    if is_test_run:
        connector_scope.LOGGER.info(
            '***** This is an "IDE Play Button"\\"Run Connector once" test run ******'
        )

    try:
        connector_scope.LOGGER.info(
            "------------------- Main - Param Init -------------------"
        )

        # Integration Configuration
        api_root = extract_connector_param(
            connector_scope, param_name="Api Root", is_mandatory=True, print_value=True
        )
        access_id = extract_connector_param(
            connector_scope, param_name="Access ID", is_mandatory=True, print_value=True
        )
        access_key = extract_connector_param(
            connector_scope,
            param_name="Access Key",
            is_mandatory=True,
            print_value=False,
        )
        verify_ssl = extract_connector_param(
            connector_scope,
            param_name="Verify SSL",
            default_value=False,
            input_type=bool,
            print_value=True,
            is_mandatory=True,
        )

        # Connector Params
        environment_field_name = extract_connector_param(
            connector_scope, param_name="Environment Field", print_value=True
        )
        environment_regex_pattern = extract_connector_param(
            connector_scope, param_name="Environment Regex Pattern", print_value=True
        )
        alerts_count_limit = extract_connector_param(
            connector_scope,
            param_name="Alerts Count Limit",
            print_value=True,
            is_mandatory=True,
            input_type=int,
            default_value=DEFAULT_MAX_ALERTS,
        )
        max_days_backwards = extract_connector_param(
            connector_scope,
            param_name="Max Days Backwards",
            input_type=int,
            default_value=DEFAULT_DAYS_BACKWARDS,
            is_mandatory=True,
            print_value=True,
        )
        device_product_field_name = extract_connector_param(
            connector_scope,
            param_name="DeviceProductField",
            is_mandatory=True,
            print_value=True,
        )
        alert_name_field = extract_connector_param(
            connector_scope,
            param_name="Alert Name Field",
            is_mandatory=True,
            print_value=True,
        )
        timestamp_field_name = extract_connector_param(
            connector_scope,
            param_name="Timestamp Field",
            is_mandatory=True,
            print_value=True,
        )
        python_process_timeout = extract_connector_param(
            connector_scope,
            param_name="PythonProcessTimeout",
            input_type=int,
            is_mandatory=True,
            print_value=True,
        )
        indexes = extract_connector_param(
            connector_scope, param_name="Indexes", is_mandatory=False, print_value=True
        )
        indexes = load_csv_to_list(indexes, "Indexes") if indexes else []
        queries = connector_scope.whitelist or []

        sumologic_manager = SumoLogicManager(
            server_address=api_root,
            access_id=access_id,
            access_key=access_key,
            verify_ssl=verify_ssl,
            logger=connector_scope.LOGGER,
        )

        sumologic_connector = SumologicQueryConnector(
            connector_scope=connector_scope,
            logger=connector_scope.LOGGER,
            sumologic_manager=sumologic_manager,
            alert_name_field=alert_name_field,
            timestamp_field_name=timestamp_field_name,
            device_product_field_name=device_product_field_name,
            environment_field_name=environment_field_name,
        )

        last_run_time = get_last_success_time(
            connector_scope, offset_with_metric={"days": max_days_backwards}
        )
        existing_ids = read_ids(connector_scope)

        connector_scope.LOGGER.info("Getting alerts")
        filtered_alerts = sumologic_connector.get_alerts(
            limit=alerts_count_limit,
            since=last_run_time,
            to=connector_starting_time,
            existing_ids=existing_ids,
            indexes=indexes,
            queries=queries,
        )
        filtered_alerts = sorted(filtered_alerts, key=lambda alert: alert.message_time)
        connector_scope.LOGGER.info(f"Found total {len(filtered_alerts)} alerts")

        if is_test_run:
            connector_scope.LOGGER.info(
                "This is a TEST run. Only 1 alert will be processed."
            )
            filtered_alerts = filtered_alerts[:1]

        for alert in filtered_alerts:
            try:
                if is_approaching_timeout(
                    python_process_timeout, connector_starting_time
                ):
                    connector_scope.LOGGER.info(
                        "Timeout is approaching. Connector will gracefully exit"
                    )
                    break

                connector_scope.LOGGER.info(
                    f"Creating case for alert {alert.message_id}"
                )

                # Update existing alerts
                existing_ids.append(alert.message_id)
                fetched_alerts.append(alert)

                # Create case package.
                case = sumologic_connector.create_case(
                    alert, environment_field_name, environment_regex_pattern
                )

                if is_overflowed(connector_scope, case, is_test_run):
                    connector_scope.LOGGER.info(
                        f"{case.rule_generator}-{case.ticket_id}-{case.environment}-{case.device_product} found as overflow alert. Skipping."
                    )
                    # If is overflowed we should skip
                    continue

                processed_alerts.append(case)
                connector_scope.LOGGER.info(
                    f'Case with display id "{case.display_id}" was created.'
                )

            except Exception as err:
                connector_scope.LOGGER.error(
                    f"Failed to process alert {alert.message_id}"
                )
                connector_scope.LOGGER.exception(err)
                if is_test_run:
                    raise

        if not is_test_run:
            if fetched_alerts:
                # Alerts are sorted - get sumo time of newest alert
                connector_scope.save_timestamp(
                    new_timestamp=fetched_alerts[-1].message_time
                )
            write_ids(connector_scope, existing_ids)
            connector_scope.LOGGER.info(
                " ------------ Connector Finished Iteration ------------ "
            )

        connector_scope.LOGGER.info(f"{len(processed_alerts)} cases created.")
        connector_scope.return_package(processed_alerts)

    except Exception as err:
        error_message = f"Got exception on main handler. Error: {err}"
        connector_scope.LOGGER.error(error_message)
        connector_scope.LOGGER.exception(err)
        if is_test_run:
            raise


if __name__ == "__main__":
    # Connectors are run in iterations. The interval is configurable from the ConnectorsScreen UI.
    is_test = not (len(sys.argv) < 2 or sys.argv[1] == "True")
    main_handler(is_test)
