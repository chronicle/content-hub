from __future__ import annotations
import sys
from EnvironmentCommon import GetEnvironmentCommonFactory
from soar_sdk.SiemplifyConnectors import SiemplifyConnectorExecution
from soar_sdk.SiemplifyConnectorsDataModel import AlertInfo
from soar_sdk.SiemplifyUtils import output_handler
from TIPCommon import (
    extract_connector_param,
    convert_comma_separated_to_list,
    get_last_success_time,
    siemplify_save_timestamp,
    is_approaching_timeout,
    write_ids,
    write_content,
    read_ids,
    read_content,
    unix_now,
    pass_whitelist_filter,
    is_overflowed,
)

from ..core.VaronisDataSecurityPlatformConstants import (
    STORED_IDS_LIMIT,
    VENDOR_NAME,
    PRODUCT_NAME,
    ALERT_SEQ_ID_WITH_TIME,
    LAST_DAYS,
)
from ..core.VaronisDataSecurityPlatformDatamodels import Alert

from ..core.VaronisDataSecurityPlatformManager import VaronisDataSecurityPlatformManager
from ..core.VaronisDataSecurityPlatformUtils import transform_template_string


class Params:
    def __init__(self):
        self._params = {}

    def __get__(self, ins, owner):
        return self._params.get(ins)

    def __set__(self, ins, value):
        self._params[ins] = value

    def as_dict(self):
        return self._params


class VaronisDataSecurityPlatformAlertsConnector:
    def __init__(self, is_test_run: bool = False):

        self.connector_scope = SiemplifyConnectorExecution()
        self.is_test_run = is_test_run
        self.connector_starting_time = unix_now()

        self.connector_scope.LOGGER.info(
            "----------------- Main - Param Init -----------------"
        )

        self._params = Params()
        self._load_configurations()

        self.last_success_time = None
        self.existing_ids = []
        self.processed_alerts = []
        self.alert_infos = []

    @property
    def logger(self):
        return self.connector_scope.LOGGER

    def _load_configurations(self):
        # Connector parameters.
        self._params.environment_field_name = extract_connector_param(
            self.connector_scope,
            param_name="Environment Field Name",
            is_mandatory=False,
            print_value=True,
        )
        self._params.environment_regex_pattern = extract_connector_param(
            self.connector_scope,
            param_name="Environment Regex Pattern",
            is_mandatory=False,
            print_value=True,
        )
        self._params.python_process_timeout = extract_connector_param(
            self.connector_scope,
            param_name="PythonProcessTimeout",
            is_mandatory=True,
            print_value=True,
            input_type=int,
        )

        self.environment_common = (
            GetEnvironmentCommonFactory.create_environment_manager(
                siemplify=self.connector_scope,
                environment_field_name=self._params.environment_field_name,
                environment_regex_pattern=self._params.environment_regex_pattern,
            )
        )

        # API parameters.
        self._params.api_root = extract_connector_param(
            self.connector_scope,
            param_name="API Root",
            is_mandatory=True,
            print_value=True,
        )
        self._params.username = extract_connector_param(
            self.connector_scope,
            param_name="Username",
            is_mandatory=True,
            print_value=True,
        )
        self._params.password = extract_connector_param(
            self.connector_scope,
            param_name="Password",
            is_mandatory=True,
            remove_whitespaces=False,
        )
        self._params.verify_ssl = extract_connector_param(
            self.connector_scope,
            param_name="Verify SSL",
            is_mandatory=True,
            print_value=True,
            input_type=bool,
        )

        # Data ingestion parameters.
        self._params.max_days_backwards = extract_connector_param(
            self.connector_scope,
            param_name="Max Days Backwards",
            is_mandatory=True,
            print_value=True,
            input_type=int,
        )
        self._params.max_alerts_per_cycle = extract_connector_param(
            self.connector_scope,
            param_name="Max Alerts per Cycle",
            is_mandatory=True,
            print_value=True,
            input_type=int,
        )
        self._params.max_events_per_varonis_alert = extract_connector_param(
            self.connector_scope,
            param_name="Max Events per Varonis alert",
            is_mandatory=True,
            print_value=True,
            input_type=int,
        )
        self._params.status = convert_comma_separated_to_list(
            extract_connector_param(
                self.connector_scope,
                param_name="Status",
                is_mandatory=True,
                print_value=True,
            )
        )
        self._params.severity = convert_comma_separated_to_list(
            extract_connector_param(
                self.connector_scope,
                param_name="Severity",
                is_mandatory=True,
                print_value=True,
            )
        )

        # Data processing parameters.
        self._params.disable_overflow = extract_connector_param(
            self.connector_scope,
            param_name="Disable Overflow",
            is_mandatory=True,
            print_value=True,
            input_type=bool,
        )
        self._params.use_dynamic_list_as_blocklist = extract_connector_param(
            self.connector_scope,
            param_name="Use Dynamic List as BlockList",
            is_mandatory=True,
            print_value=True,
            input_type=bool,
        )
        self._params.alert_name_template = extract_connector_param(
            self.connector_scope,
            param_name="Alert Name Template",
            is_mandatory=False,
            print_value=True,
        )
        self._params.rule_generator_template = extract_connector_param(
            self.connector_scope,
            param_name="Rule Generator Template",
            is_mandatory=False,
            print_value=True,
        )

    def validate_params(self):
        limits = [
            "max_days_backwards",
            "max_alerts_per_cycle",
            "max_events_per_varonis_alert",
        ]
        for key in limits:
            if getattr(self._params, key) <= 0:
                key_display_name = " ".join(word.title() for word in key.split("_"))
                raise ValueError(f"{key_display_name} must be a positive integer")

    def load_context(self):
        self.last_success_time = get_last_success_time(
            self.connector_scope,
            offset_with_metric={"days": self._params.max_days_backwards},
        )
        self.logger.info(
            f"Calculated last run time. Last run time is: " f"{self.last_success_time}"
        )

        self.existing_ids = read_ids(self.connector_scope)
        self.logger.info(
            f"Loaded existing IDs. Number of existing IDs is: "
            f"{len(self.existing_ids)}"
        )

    def save_context(self):
        if self.is_test_run:
            self.logger.info("Test run. Skipping context saving.")
            return

        if self.alert_infos:
            write_ids(
                self.connector_scope,
                self.existing_ids,
                stored_ids_limit=STORED_IDS_LIMIT,
            )
            self.logger.info(
                f"Saved existing IDs. Current number of existing IDs is: "
                f"{len(self.existing_ids[:STORED_IDS_LIMIT])}"
            )

        if self.processed_alerts:
            siemplify_save_timestamp(
                self.connector_scope, self.processed_alerts[-1].timestamp
            )
            self.logger.info(
                f"Saved last success time. Last success time is: "
                f"{self.processed_alerts[-1].timestamp}"
            )

    def generate_alert_info(self, alert: Alert) -> AlertInfo:
        alert_info = AlertInfo()
        alert_info.ticket_id = alert.id
        alert_info.display_id = alert.id

        alert_info.name = transform_template_string(
            self._params.alert_name_template, alert.flat_data()
        )
        alert_info.rule_generator = transform_template_string(
            self._params.rule_generator_template, alert.flat_data()
        )
        alert_info.environment = self.environment_common.get_environment(
            alert.flat_data()
        )

        alert_info.device_vendor = VENDOR_NAME
        alert_info.device_product = PRODUCT_NAME

        alert_info.priority = alert.get_severity()
        alert_info.start_time = alert.timestamp
        alert_info.end_time = alert.timestamp

        alert_info.extensions = {
            "Severity": alert.severity,
            "Category": alert.category,
            "Status": alert.status,
            "BlacklistLocation": alert.blacklist_location,
            "AbnormalLocation": alert.abnormal_location,
            "CloseReason": alert.close_reason,
        }

        return alert_info

    def attach_events_to_alert_info(
        self, manager: VaronisDataSecurityPlatformManager, alert, alert_info
    ):
        events_data = [alert.flat_data()]
        device_data = alert.raw_data.get("Device", {})
        device_node = {"Device": device_data} if device_data else None

        events = manager.get_events_by_alert_id(
            alert_id=alert.id,
            max_events_per_varonis_alert=self._params.max_events_per_varonis_alert,
        )
        self.logger.info(f"Found {len(events)} events for alert {alert.id}")

        if events:
            events_data = [
                event.flat_data(additional_data=device_node) for event in events
            ]

        alert_info.events = events_data

        return alert_info

    def fetch_alerts(self, manager: VaronisDataSecurityPlatformManager):
        db_lastdays = read_content(
            siemplify=self.connector_scope, file_name=LAST_DAYS, db_key=LAST_DAYS
        )
        db_lastalertid = read_content(
            siemplify=self.connector_scope,
            file_name=ALERT_SEQ_ID_WITH_TIME,
            db_key=ALERT_SEQ_ID_WITH_TIME,
        )
        alert_list, last_alert_id = manager.get_alerts(
            last_days=self._params.max_days_backwards,
            max_alerts_per_cycle=self._params.max_alerts_per_cycle,
            status=self._params.status,
            severity=self._params.severity,
            existing_ids=self.existing_ids,
            db_lastdays=db_lastdays,
            db_lastalertid=db_lastalertid,
        )
        write_content(
            siemplify=self.connector_scope,
            content_to_write=last_alert_id,
            file_name=ALERT_SEQ_ID_WITH_TIME,
            db_key=ALERT_SEQ_ID_WITH_TIME,
        )
        write_content(
            siemplify=self.connector_scope,
            content_to_write=self._params.max_days_backwards,
            file_name=LAST_DAYS,
            db_key=LAST_DAYS,
        )
        return alert_list

    def process_alerts(self, manager, fetched_alerts):
        for alert in fetched_alerts:
            if self.is_test_run and len(self.alert_infos) >= 1:
                self.logger.info(
                    "This is a test run. Only one alert will be processed."
                )
                break

            if is_approaching_timeout(
                self.connector_starting_time, self._params.python_process_timeout
            ):
                self.logger.info(
                    "Timeout is approaching. Connector will gracefully exit."
                )
                break

            self.logger.info(f"Processing alert {alert.id}")
            self.processed_alerts.append(alert)

            passed_whitelist = pass_whitelist_filter(
                siemplify=self.connector_scope,
                whitelist_as_a_blacklist=self._params.use_dynamic_list_as_blocklist,
                model=alert,
                model_key="name",
                whitelist=self.connector_scope.whitelist,
            )

            if not passed_whitelist:
                self.logger.info(
                    f"Alert {alert.id} with name {alert.name} did not pass whitelist. Skipping..."
                )
                continue

            alert_info = self.generate_alert_info(alert=alert)

            is_overflow = not self._params.disable_overflow and is_overflowed(
                self.connector_scope, alert_info, self.is_test_run
            )

            if is_overflow:
                self.logger.info(f"Alert {alert.id} is overflowed. Skipping...")
                continue

            alert_info = self.attach_events_to_alert_info(
                manager=manager, alert=alert, alert_info=alert_info
            )

            self.alert_infos.append(alert_info)
            self.existing_ids.append(alert.id)

    def run(self):
        """
        Main method of Connector execution. It uses template pattern.
        """

        self.logger.info("------------------- Main - Started -------------------")

        try:
            # Params validation.
            self.validate_params()

            # Extract context params.
            self.load_context()

            # Initialize API client.
            manager = VaronisDataSecurityPlatformManager(
                self._params.api_root,
                self._params.username,
                self._params.password,
                self._params.verify_ssl,
            )

            # Do the fetching
            fetched_alerts = self.fetch_alerts(manager)

            # Do the processing
            self.process_alerts(manager, fetched_alerts)

            # Save context for next run.
            self.save_context()

        except Exception as e:
            self.logger.error(f"Got exception on main handler. Error: {e}")
            self.logger.exception(e)

            if self.is_test_run:
                raise

        self.logger.info(f"Created total of {len(self.alert_infos)} cases")
        self.logger.info("------------------- Main - Finished -------------------")
        self.connector_scope.return_package(self.alert_infos)


@output_handler
def main():
    is_test_run = not (len(sys.argv) < 2 or sys.argv[1] == "True")
    connector = VaronisDataSecurityPlatformAlertsConnector(is_test_run=is_test_run)
    connector.run()


if __name__ == "__main__":
    main()
