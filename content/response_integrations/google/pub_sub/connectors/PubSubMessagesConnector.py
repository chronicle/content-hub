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

from soar_sdk.SiemplifyUtils import output_handler
from soar_sdk.SiemplifyConnectorsDataModel import AlertInfo

from TIPCommon.adapters.pubsub.data_models import Subscription
from TIPCommon.base.connector import Connector
from TIPCommon.exceptions import (
    BadGatewayError,
    ConnectorSetupError,
    DeadlineExceededError,
    ResourceExhaustedError,
    UnavailableError,
)
from TIPCommon.smp_io import read_ids, write_ids
from ..core import PubSubConstants as Constants
from ..core import PubSubDatamodels as Datamodels
from ..core.PubSubExceptions import PubSubException
from ..core.PubSubAuthManager import AuthManager, build_auth_manager_params
from ..core.PubSubManager import ApiManager


class PubSubMessagesConnector(Connector):

    def __init__(self) -> None:
        super().__init__(Constants.PUB_SUB_CONNECTOR_SCRIPT_NAME)

        self.manager: ApiManager | None = None
        self.subscription: Subscription | None = None
        self.ack_ids = []

    def validate_params(self) -> None:
        """Validate connector parameters."""
        self.params.max_messages_to_fetch = (
            self.param_validator.validate_positive(
                "Max Messages To Fetch",
                self.params.max_messages_to_fetch,
            )
        )
        self.params.severity_mapping_json = self.param_validator.validate_json(
            "Severity Mapping JSON",
            self.params.severity_mapping_json
        )
        if "Default" not in self.params.severity_mapping_json:
            raise PubSubException(
                "Invalid parameter \"Severity Mapping JSON\". \"Default\" "
                "value must be specified."
            )

    def init_managers(self) -> None:
        """Initialize connector api clients."""
        auth_manager_params = build_auth_manager_params(self.siemplify)
        auth_manager = AuthManager(auth_manager_params, self.logger)
        self.manager = ApiManager(
            auth_manager.prepare_client(),
            logger=self.logger
        )
        self.subscription = self.manager.get_subscription(
            subscription_name=self.params.subscription_id,
            ack_deadline=self.params.python_process_timeout
        )

    def get_alerts(self) -> list[Datamodels.PubSubMessage]:
        """Fetch new notifications from Pub/Sub topic."""
        alert_config = Datamodels.AlertConfig(
            unique_id_field=self.params.unique_id_field,
            timestamp_field=self.params.timestamp_field,
            timestamp_format=self.params.timestamp_format,
            case_name_template=self.params.case_name_template,
            alert_name_template=self.params.alert_name_template,
            rule_generator_template=self.params.rule_generator_template,
            severity_mapping_json=self.params.severity_mapping_json,
        )
        return self.manager.pull_messages(
            alert_config=alert_config,
            subscription=self.subscription,
            max_alerts_to_fetch=self.params.max_messages_to_fetch
        )

    def read_context_data(self) -> None:
        self.logger.info("Reading already existing alerts ids...")
        self.context.existing_ids = set(read_ids(self.siemplify))

    def write_context_data(
            self,
            _: list[Datamodels.PubSubMessage]
    ) -> None:
        """Write connector context data."""
        self.logger.info("Saving existing ids.")
        write_ids(
            self.siemplify,
            list(self.context.existing_ids),
        )

    def store_alert_in_cache(self, alert: Datamodels.PubSubMessage) -> None:
        self.context.existing_ids.add(alert.alert_id)
        self.ack_ids.append(alert.message.ack_id)

    def is_overflow_alert(self, alert_info: AlertInfo) -> bool:
        return (
            not self.params.disable_overflow
            and super().is_overflow_alert(alert_info)
        )

    def create_alert_info(
            self,
            alert: Datamodels.PubSubMessage,
    ) -> AlertInfo:
        """Create SOAR alert info from Pub/Sub notification."""
        alert_info = AlertInfo()
        flat_message = alert.flat()

        alert_info.environment = self.env_common.get_environment(flat_message)
        alert_info.ticket_id = alert.alert_id
        alert_info.display_id = (
            Constants.CONNECTOR_DISPLAY_ID_TEMPLATE
            .format(
                alert_id=alert.alert_id,
                connector_identifier=self.siemplify.context.connector_info.identifier
            )
        )
        alert_info.device_vendor = Constants.VENDOR
        alert_info.device_product = Constants.PRODUCT
        alert_info.name = (
            alert.alert_name
            or Constants.ALERT_NAME.format(
                connector_name=self.siemplify.context.connector_info.display_name,
            )
        )
        alert_info.rule_generator = (
            alert.rule_generator or
            Constants.RULE_GENERATOR.format(
                connector_name=self.siemplify.context.connector_info.display_name,
            )
        )
        alert_info.priority = alert.get_severity()
        alert_info.source_grouping_identifier = self.subscription.name
        alert_info.end_time, alert_info.start_time = alert.timestamp, alert.timestamp

        flat_message["custom_case_name"] = alert.case_name
        alert_info.events = [flat_message]
        return alert_info

    def finalize(self) -> None:
        """Finalize connector"s run."""
        if not self.is_test_run and self.manager is not None:
            self.logger.info(
                f"Acknowledging {len(self.ack_ids)} posture findings messages "
                f"from pubsub"
            )
            self.manager.ack_pubsub_findings(
                self.subscription.name,
                self.ack_ids
            )

    @output_handler
    def start(self) -> None:
        """
        Executes the connector logic.

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
            f"---------------- Starting connector {self.script_name} "
            "execution ----------------"
        )
        if self.is_test_run:
            self.logger.info(
                "****** This is an \"IDE Play Button\"\\\"Run Connector once\" "
                "test run ******"
            )

        self.logger.info(
            "------------------- Main - Param Init -------------------"
        )
        self.extract_params()
        self.logger.info(
            "------------------- Main - Started -------------------"
        )
        processed_alerts = []

        try:
            try:
                self.validate_params_wrapper()
                self.read_context_wrapper()
                self.logger.info("Initializing managers...")
                self.init_managers()

            # pylint: disable=try-except-raise
            except (
                BadGatewayError,
                DeadlineExceededError,
                ResourceExhaustedError,
                UnavailableError,
            ):
                raise
            except Exception as e:
                raise ConnectorSetupError(e) from e

            self.logger.info(
                "Fetching data from manager and starting case ingestion..."
            )
            fetched_alerts = self.get_alerts()
            self.logger.info(
                f"Fetched {len(fetched_alerts)} alerts from the manager"
            )

            filtered_alerts = self.filter_alerts(fetched_alerts)
            self.logger.info(
                f"Successfully filtered alerts. "
                f"Filtered alerts count: {len(filtered_alerts)}"
            )

            self.logger.info("Starting to process alerts...")
            processed_alerts, all_alerts = self.process_alerts(filtered_alerts)
            if not self.is_test_run:
                self.write_context_wrapper(all_alerts)

        except (
            BadGatewayError,
            DeadlineExceededError,
            ResourceExhaustedError,
            UnavailableError,
        ) as e:
            self.logger.error(
                f"Pub/Sub services are temporarily unavailable, "
                f"received error: {e}. The connector will gracefully exit "
                f"and retry on next iteration."
            )

        # pylint: disable=broad-exception-caught
        except Exception as e:
            self.logger.error(f"{self.error_msg}")
            self.logger.error(f"Error: {e}")
            self.logger.exception(e)

            if self.is_test_run:
                raise

        try:
            self.finalize()

        # pylint: disable=broad-exception-caught
        except Exception as e:
            self.logger.error(f"{self.error_msg}")
            self.logger.error(f"Error: {e}")
            self.logger.exception(e)

            if self.is_test_run:
                raise

        self.logger.info(
            "------------------- Main - Finished -------------------"
        )
        self.logger.info(
            f"Sending {len(processed_alerts)} alerts back to SOAR platform. This "
            "package can contain both new alerts and updates to existing ones."
        )
        self.siemplify.return_package(processed_alerts)
        self.logger.info(
            f"---------------- Finished connector {self.script_name} "
            f"execution ----------------"
        )


def main() -> None:
    connector = PubSubMessagesConnector()
    connector.start()


if __name__ == "__main__":
    main()
