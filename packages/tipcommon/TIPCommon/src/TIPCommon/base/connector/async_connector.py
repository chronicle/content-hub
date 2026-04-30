# Copyright 2025 Google LLC
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

import asyncio
from abc import ABC, abstractmethod
from typing import Any

import SiemplifyUtils
from SiemplifyConnectorsDataModel import AlertInfo

from ...consts import NUM_OF_MILLI_IN_SEC, TIMEOUT_THRESHOLD
from ...data_models import BaseAlert
from ...exceptions import ConnectorSetupError
from ...smp_time import save_timestamp
from ..utils import (
    async_output_handler,
    coros_to_tasks_with_limit,
    is_native,
    nativemethod,
)
from .base_connector import BaseConnector


class AsyncConnector(BaseConnector, ABC):
    """A Unified Generic infrastructure implementation for Chroniclal SOAR
    (Formerly 'Siemplify') async Connector development.

    The ``AsyncConnector`` base class provides template abstract methods to override
    in the inherited connector classes, generic properties, and general flows
    as methods that will be executed when calling the connector's `start` method.

    Note:
        THIS CLASS IS NOT SUPPORTED WITH PYTHON 2!

    Args:
        script_name (str): The name of the script that is using this connector.
        is_test_run (bool): Whether this is a test run or not.

    Attributes:
        _siemplify (SiemplifyConnectorExecution):
            The Siemplify connector execution object.
        _script_name (str): The name of the script that is using this connector.
        _connector_start_time (int): The time at which the connector started.
        _logger (str): The logger for this connector.
        _is_test_run (bool): Whether this is a test run or not.
        _params (Container): The parameters container for this connector.
        _context (Container): The context data container for this connector.
        _vars (Container): The runtime variables container used by the connector.
        _env_common (str): The environment common handle object.
        _error_msg (str):
            The error message the connector will display in case of a generic failure.

    Properties:
        siemplify (SiemplifyConnectorExecution):
            The Siemplify connector execution object.
        script_name (str): The name of the script that is using this connector.
        connector_start_time (int): The time at which the connector started.
        logger (str): The logger for this connector.
        is_test_run (bool): Whether this is a test run or not.
        params (Container): The parameters container for this connector.
        context (Container): The context data container for this connector.
        vars (Container): The runtime variables container used by the connector.
        env_common (str): The environment common handle object.
        error_msg (str):
            The error message the connector will display in case of a generic failure.

    Abstract Methods:
        - validate_params(self): Validate the parameters for this connector.
        - read_context_data(self): Read the context data for this connector.
        - write_context_data(self, filtered_alerts, unprocessed_alerts):
            Write context data for this connector.
        - init_managers(self): Initialize the managers for this connector.
        - store_alert_in_cache(self, alert): Store the alert in the cache.
        - async get_alerts(self): Get the alerts from the manager.
        - create_alert_info(self, alert): Create an alert info object.

    Additional Methods:
        ** These are methods that are called during the connector execution and affect
        the alerts processing phase, but are not mandatory to override. **

        - get_last_success_time(
                self,
                max_backwards_param_name,
                metric, padding_period_param_name,
                padding_period_metric,
                time_format,
                print_value,
                microtime
            ):
            Calculates the connector last successful timestamp.
        - max_alerts_processed(self, processed_alerts):
            Return True if reached the maximum alerts to process limit in the connector
            execution.
        - pass_filters(self, alert):
            Boolean method to check if alert passes connector filters.
        - filter_alerts(self, alerts):
            Filter alerts from manager and return list of filtered alerts.
        - process_alert(self, alert):
            Additional alert processing (like events enrichment).
        - finalize(self):
            handle all post-processing logic before ending connector's current iteration

    Examples:
            import asyncio
            import time
            from TIPCommon.base.connector import Connector
            from TIPCommon.data_models import BaseAlert
            from SiemplifyConnectorsDataModel import AlertInfo

            class FakeAlert(BaseAlert):
                def __init__(self, raw_data):
                    super().__init__(raw_data, raw_data.get('Id'))
                    start_time = raw_data.get('StartTime')
                    end_time = raw_data.get('EndTime')


            class FakeConnector(Connector):
                def validate_params(self):
                    self.params.user_email = self.param_validator.validate_email(
                        'User Email',
                        self.params.user_email
                    )

                def read_context_data(self):
                    self.context.ids = TIPCommon.read_ids(self.siemplify)

                def init_managers(self):
                    self.manager = FakeManager(self.params.user_email)

                async def get_alerts(self):
                    raw_alerts = await self.manager.get_alerts()
                    parsed_alerts = []
                    for alert in raw_alerts:
                        parsed_alerts.append(FakeAlert(alert))
                    return parsed_alerts

                async def process_alert(self, alert):
                    return await self.manager.fetch_events(alert)

                def store_alert_in_cache(self, alert):
                    self.context.ids.append(alert.alert_id)

                def create_alert_info(self, alert):
                    alert_info = AlertInfo()
                    alert_info.ticket_id = alert.alert_id
                    alert_info.display_id = alert.alert_id
                    alert_info.name = "Fake Alert"
                    alert_info.device_vendor = "Fake Device Vendor"
                    alert_info.device_product = "Fake Device Product"
                    alert_info.start_time = alert.start_time
                    alert_info.end_time = alert.end_time
                    alert_info.environment = self.env_common.get_environment(
                        TIPCommon.dict_to_flat(alert.to_json())
                    )
                    return alert_info

                def write_context_data(self, filtered_alerts, unprocessed_alerts):
                    TIPCommon.write_ids(self.siemplify, self.context.ids)

                def get_last_success_time():
                    return super().get_last_success_time(
                        max_backwards_param_name="max_days_backwards",
                        metric="days",
                        padding_period_param_name="padding_period",
                        padding_period_metric="hours"
                    )

            async def main() -> None:
                script_name = "MyFakeConnector"
                is_test = TIPCommon.is_test_run(sys.argv)
                connector = FakeConnector(script_name, is_test)
                await asyncio.ensure_future(connector.start())

            if __name__ == '__main__':
                loop = asyncio.get_event_loop()
                loop.run_until_complete(main())

    """

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.coros_limit = 20

    # Abstract Methods ######################
    @abstractmethod
    async def get_alerts(self) -> list[BaseAlert]:
        """Get alerts from the manager and return a list of alerts.

        Raises:
            ConnectorSetupError: If there is an error getting the alerts.

        """

    # Native Methods ######################
    @nativemethod
    def write_context_data(
        self, filtered_alerts: list[BaseAlert], unprocessed_alerts: list[BaseAlert]
    ) -> None:
        """Save updated context data to platform data storage (DB/LFS).

        Args:
            filtered_alerts: All alerts that were fetched during this connector run.
            unprocessed_alerts: All alerts that connector didn't process

        Examples:
            from TIPCommon import write_ids

            Class MyConnector(Connector):
                # method override
                def write_context_data(self, all_alerts):
                    write_ids(self.siemplify, self.context.ids)

        Raises:
            ConnectorSetupError: If there is an error saving the context data.

        """

    @nativemethod
    def write_context_wrapper(self, filtered_alerts, unprocessed_alerts):
        """Write context wrapper.

        This wrapper will call set_last_success_time and then write_context_data.
        """
        self.set_last_success_time(filtered_alerts, unprocessed_alerts)
        if not is_native(self.write_context_data):
            self.logger.info(f"Saving context data to {self.context._location}...")
            self.write_context_data(filtered_alerts, unprocessed_alerts)

    @nativemethod
    def set_last_success_time(
        self,
        filtered_alerts: list[BaseAlert],
        unprocessed_alerts: list[BaseAlert],
        timestamp_key: str = None,
        incrementation_value=0,
        log_timestamp=True,
        convert_timestamp_to_micro_time=False,
        convert_a_string_timestamp_to_unix=False,
    ):
        """Gets the timestamp of the most recent alert from `filtered_alerts`
        using `timestamp_key` where `filtered_alerts` is a list of all alerts
        the connector has tried or completed processing, and stores this
        timestamp in the LFS / DB. If unprocessed_alerts is not empty,
        use first alerts from this list instead.

        Args:
            filtered_alerts (list[BaseAlert]): list of all alerts the connector
                has tried or completed processing
            unprocessed_alerts (list[BaseAlert]): list of all alerts the connector
                didn't process
            timestamp_key (str, optional): timestamp attribute name for each alert.
                Defaults to None.
            incrementation_value (int, optional): The value to increment last
                timestamp by milliseconds. Defaults to 0.
            log_timestamp (bool, optional): Whether log timestamp or not.
                Defaults to True.
            convert_timestamp_to_micro_time (bool, optional): timestamp * 1000 if True.
                Defaults to False.
            convert_a_string_timestamp_to_unix (bool, optional): If the timestamp
                in the raw data is in the form of a
                string - convert it to unix before saving it. Defaults to False.

        Note:
            * If `timestamp_key` is None, last success timestamp will not be saved!
            * In order to save it, override this method and provide it with
                `timestamp_key`!

        Example::

            Class MyAlert(BaseAlert):
                def __init__(self, raw_data, alert_id):
                    super().__init__(raw_data, alert_id)
                    self.timestamp = raw_data.get('DetectionTime')

            Class MyConnector(Connector):
                # method override
                def set_last_success_time(self, alerts):
                    super().set_last_success_time(
                        alerts=alerts,
                        timestamp_key='timestamp'
                    )

        """
        if timestamp_key is not None:
            save_timestamp(
                siemplify=self.siemplify,
                alerts=(filtered_alerts if not unprocessed_alerts else unprocessed_alerts[:1]),
                timestamp_key=timestamp_key,
                incrementation_value=incrementation_value,
                log_timestamp=log_timestamp,
                convert_timestamp_to_micro_time=convert_timestamp_to_micro_time,
                convert_a_string_timestamp_to_unix=(convert_a_string_timestamp_to_unix),
            )

    @nativemethod
    async def process_alert(self, alert: BaseAlert) -> BaseAlert:
        """Extensive alert processing (like events enrichment)

        Args:
            alert: The alert to process.

        Returns:
            The processed alert.

        """
        return alert

    @nativemethod
    async def process_alerts(
        self, filtered_alerts: list[BaseAlert], timeout_threshold: float = TIMEOUT_THRESHOLD
    ) -> tuple[list[AlertInfo], list[BaseAlert]]:
        """Main alert processing loop.
        Steps for each alert object:

        1. Schedule alert processing, once completed
        1. Check if connector is approaching timeout
        2. Check max alert count for test run
        3. Check max alert count for commercial run (override)
        4. Remove alert from unprocessed_alerts list
        5. Check if alert pass filters
        6. Store alert in cache (id.json etc) (override)
        7. Create AlertInfo object
        8. Check is alert overflowed
        9. append alert to processed alerts

        Args:
            filtered_alerts (list[BaseAlert]):list of filtered BaseAlert objects
            timeout_threshold (float, optional): timeout threshold for connector
                execution. Defaults to 0.9

        Note:
            To provide other value for timeout threshold,
            you can override this method as follows::

                my_threshold = 0.9


                def process_alerts(self, filtered_alerts, timeout_threshold):
                    return super().process_alerts(filtered_alerts, my_threshold)

        Returns:
            tuple containing a list of AlertInfo objects,
            and a list of BaseAlert objects

        """
        unprocessed_alerts = filtered_alerts.copy()
        processed_alerts = []
        processed_alerts_tasks = coros_to_tasks_with_limit(
            (self.process_alert(alert) for alert in filtered_alerts), limit=self.coros_limit
        )

        processing_time = (
            SiemplifyUtils.unix_now() - self.connector_start_time
        ) / NUM_OF_MILLI_IN_SEC
        concurrent_timeout = (
            self.params.python_process_timeout - processing_time
        ) * timeout_threshold

        try:
            for processed_alerts_cor in asyncio.as_completed(
                processed_alerts_tasks,
                timeout=concurrent_timeout,
            ):
                try:
                    if self.is_test_run and processed_alerts:
                        self.logger.info("Maximum alert count (1) for test run reached!")
                        break

                    if self.max_alerts_processed(processed_alerts):
                        self.logger.info(
                            f"Maximum alert count {len(processed_alerts)} "
                            f"for connector execution reached!."
                        )
                        break

                    processed_alert = await processed_alerts_cor
                    unprocessed_alerts.remove(processed_alert)

                    if not self.pass_filters(processed_alert):
                        self.logger.info(
                            f"Alert {processed_alert.alert_id} did not pass filters. Skipping..."
                        )
                        continue

                    self.store_alert_in_cache(processed_alert)
                    self.logger.info(f"Alert {processed_alert.alert_id} processed successfully")

                    alert_info = self.create_alert_info(processed_alert)
                    self.logger.info(
                        f"Created AlertInfo object for alert {processed_alert.alert_id}"
                    )

                    if self.is_overflow_alert(alert_info):
                        self.logger.info(
                            f"{alert_info.rule_generator}-"
                            f"{alert_info.ticket_id}-"
                            f"{alert_info.environment}-"
                            f"{alert_info.device_product} "
                            "found as overflow alert. Skipping."
                        )
                        # If is overflowed we should skip
                        continue

                    processed_alerts.append(alert_info)
                    self.logger.info(f"Finished processing {processed_alert.alert_id}")

                except TimeoutError:
                    raise

                except Exception as e:
                    self.logger.error(f"Failed to process alert. Error is: {e}")
                    self.logger.exception(e)

                    if self.is_test_run:
                        raise

        except TimeoutError:
            self.logger.info("Timeout is approaching. Connector will gracefully exit")

        finally:
            for task in processed_alerts_tasks:
                if not task.done():
                    task.cancel()

        return processed_alerts, unprocessed_alerts

    @nativemethod
    async def finalize(self) -> None:
        """Method is used to handle all post-processing logic before ending
        connector's current iteration

        Examples::

            Class MyConnector(Connector)

                # method override
                def finalize(self) -> None:
                    self.manager.logout()
        """

    def return_package(
        self,
        cases: list[AlertInfo],
        output_variables: dict[str, Any] = None,
        log_items: list[str] = None,
    ) -> None:
        """Build and send a return package to Python Execution Service through stdout.

        Args:
            cases: A list of cases CaseInfo objects
            output_variables: A list of output variables.
            log_items: A list of log items.

        """
        self.siemplify.return_package(cases, output_variables or {}, log_items or [])
        SiemplifyUtils.real_stdout.flush()

    @async_output_handler
    async def start(self) -> None:
        """Executes the connector logic.

        Execution steps:

            1. Extracting connector script parameters from the SDK connector object
            2. Validate parameters values
            3. Loading the connector context data via the SDK connector object
            4. Initializing the integrations manager(s)
            5. Fetching & parsing alerts from the product via integration manager
            6. Filtering the alerts
            7. Processing the filtered alerts into siemplify alerts
            8. Saving connector context data via the SDK connector object
            9. Sending newly created siemplify alerts to the platform

        Raises:
            ConnectorSetupError: if any of the pre-processing phases fail

        """
        self.logger.info(
            f"---------------- Starting connector {self.script_name} execution ----------------"
        )
        if self.is_test_run:
            self.logger.info(
                '****** This is an "IDE Play Button"\\"Run Connector once" test run ******'
            )

        self.logger.info("------------------- Main - Param Init -------------------")
        self.extract_params()
        self.logger.info("------------------- Main - Started -------------------")
        processed_alerts = []

        try:
            try:
                self.validate_params_wrapper()
                self.read_context_wrapper()
                self.logger.info("Initializing managers...")
                self.init_managers()
            except Exception as e:
                raise ConnectorSetupError(e) from e

            self.logger.info("Fetching data from manager and starting case ingestion...")
            fetched_alerts = await self.get_alerts()
            self.logger.info(f"Fetched {len(fetched_alerts)} alerts from the manager")

            filtered_alerts = self.filter_alerts(fetched_alerts)
            if not is_native(self.filter_alerts):
                self.logger.info(
                    f"Successfully filtered alerts. Filtered alerts count: {len(filtered_alerts)}"
                )

            self.logger.info("Starting to process alerts...")
            processed_alerts, unprocessed_alerts = await self.process_alerts(filtered_alerts)
            if not self.is_test_run:
                self.write_context_wrapper(filtered_alerts, unprocessed_alerts)

        except Exception as e:
            self.logger.error(f"{self.error_msg}")
            self.logger.error(f"Error: {e}")
            self.logger.exception(e)

            if self.is_test_run:
                raise

        try:
            await self.finalize()
        except Exception as e:
            self.logger.error(f"{self.error_msg}")
            self.logger.error(f"Error: {e}")
            self.logger.exception(e)

            if self.is_test_run:
                raise

        self.logger.info("------------------- Main - Finished -------------------")
        self.logger.info(f"Sending {len(processed_alerts)} new alerts back to SOAR platform.")
        self.return_package(processed_alerts)
        self.logger.info(
            f"---------------- Finished connector {self.script_name} execution ----------------"
        )
