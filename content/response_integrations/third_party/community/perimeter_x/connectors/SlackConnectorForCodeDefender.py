from __future__ import annotations

import sys

from soar_sdk.SiemplifyConnectors import SiemplifyConnectorExecution
from soar_sdk.SiemplifyConnectorsDataModel import AlertInfo
from soar_sdk.SiemplifyUtils import output_handler

from ..core.PerimeterXManager import PerimeterXManager

CONNECTOR_NAME = "PerimeterX Code Defender Connector"
VENDOR = "PerimeterX"
PRODUCT = "Code Defender"


class BasePXCodeDefenderConnector:
    """Base class for PerimeterX Slack Code Defender Connector containing most common functionality"""

    def __init__(self, config=None, is_test=False, connector_name=None):
        """Common constructor for PerimeterX Slack Code Defender Connector"""
        self.connector_scope = SiemplifyConnectorExecution()
        self.connector_scope.script_name = connector_name
        self.logger = self.connector_scope.LOGGER
        self.environment_name = self.connector_scope.context.connector_info.environment

        self.is_test = is_test
        if self.is_test:
            self.logger.info(
                '***** This is an "IDE Play Button"\\"Run Connector once" test run ******',
            )

        self._load_connector_configuration(config)
        self._initialize_managers()

    def _get_connector_param(
        self,
        param_name,
        config,
        default_value=None,
        is_mandatory=False,
        print_value=False,
        input_type=str,
    ):
        return self.connector_scope.extract_connector_param(
            param_name=param_name,
            input_type=input_type,
            default_value=default_value,
            is_mandatory=is_mandatory,
            print_value=print_value,
        )

    def _load_connector_configuration(self, config):
        """Loads all connector configurations from Siemplify"""
        self.logger.info("==================== Main - Param Init ====================")

        conf = self.connector_scope.parameters if not config else config
        self.param_slack_channel = self._get_connector_param(
            param_name="Slack Channel",
            config=conf,
            is_mandatory=True,
        )
        self.param_slack_api_key = self._get_connector_param(
            param_name="Slack API Key",
            config=conf,
            is_mandatory=True,
        )

        self.last_run_time = self._get_last_calculated_run_time()

    def _initialize_managers(self):
        """Abstract method to initialize all required managers"""
        raise NotImplementedError

    def run(self):
        """Main method of Connector execution. It uses template pattern."""
        self.logger.info("------------------- Main - Started -------------------")

        self.logger.info(f"Last execution time: {self.last_run_time:.6f}")

        alerts = []  # The main output of each connector run

        if is_test_run:
            self.logger.info(
                '***** This is an "IDE Play Button"\\"Run Connector once" test run ******',
            )

        self.logger.info("==================== Main - Param Init ====================")
        self.logger.info("------------------- Main - Started -------------------")

        # Let's fetch the alerts
        my_alerts = self.px_manager.get_cd_alerts(self.px_manager.get_connector_type())

        # First check to make sure we got some alerts
        if not my_alerts:
            self.logger.info("No Alerts to Process - Generic Error")
            self.connector_scope.return_package(alerts)
            return

        if len(my_alerts) < 1:
            self.logger.info("No Alerts to Process - Zero Alerts")
            self.connector_scope.return_package(alerts)
            return

        self.logger.info(my_alerts)

        # Walk through the alerts
        for my_alert in my_alerts:
            try:
                alert_details = self._fetch_alert(my_alert)

                if alert_details:
                    alerts.append(alert_details)
                    self.logger.info(
                        "Added Alert {} to package results".format(
                            round(float(my_alert["ts"]) * 100000),
                        ),
                    )

            except Exception as e:
                self.logger.error(
                    "Failed to process alert {}".format(
                        round(float(my_alert["ts"]) * 100000),
                    ),
                    my_alert=round(float(my_alert["ts"]) * 100000),
                )
                self.logger.exception(e)

        self._save_last_run_timestamp(alerts, self.last_run_time, self.is_test)

        self.logger.info("------------------- Main - Finished -------------------")
        self.connector_scope.return_package(alerts)

    def _fetch_alert(self, alert):
        raise NotImplementedError

    def _get_last_calculated_run_time(self):
        """Allows to fetch last run time for connector.
        It's important to work from last successful timestamp to effectively process events.
        """
        last_run_time = self.connector_scope.fetch_timestamp(datetime_format=False)

        self.logger.info(
            f"Received last run time. Last run time is: {last_run_time}",
        )

        if last_run_time > 0:
            last_run_time = round(float(last_run_time / 10000), 6)
        else:
            last_run_time = 0

        self.logger.info(
            f"Calculated last run time. Last run time is: {last_run_time:.6f}",
        )

        return last_run_time

    def _save_last_run_timestamp(self, all_alerts, previous_timestamp, is_test=False):
        # type: (list, arrow.datetime, bool) -> None
        """Calculates current run timestamp and saves it
        :param all_alerts: {list} List of cases, which have been created during this run
        :param previous_timestamp: {arrow.datetime} Timestamp, which has been used as
        a starting point for the current round retrieval
        :param is_test: {bool} Allows to handle special cases, when running Test
        in Connector configuration
        """
        # Get last successful execution time.
        if all_alerts and len(all_alerts) > 0:
            # Sort the cases by the end time of each case.
            all_alerts = sorted(all_alerts, key=lambda event: event.slack_time)
            # Last execution time is set to the newest message time
            new_last_run_time = all_alerts[-1].slack_time
            self.logger.info(
                f"New Run Time From alerts: {new_last_run_time:.6f}",
            )
        else:
            # previous_timestamp is datetime object. Convert it to milliseconds timestamp.
            self.logger.info(
                f"New Run Time From previous_timestamp: {previous_timestamp:.6f}",
            )
            new_last_run_time = previous_timestamp

        if not self.is_test:
            # update last execution time
            self.connector_scope.save_timestamp(new_timestamp=new_last_run_time)
            self.logger.info(f"Saved last run timestamp: {new_last_run_time}")


class PXCodeDefenderConnector(BasePXCodeDefenderConnector):
    """Class wrapping logic of PXCodeDefenderConnector."""

    VENDOR_RISK_MAP = {
        "Informative": -1,
        "Low": 40,
        "Medium": 60,
        "High": 80,
        "Critical": 100,
    }

    def __init__(self, config=None, is_test=False):
        # type: (dict, bool) -> None
        """Default constructor for the PXCodeDefenderConnector
        :param is_test: Runs collection in a limited manner in test purposes
        """
        super(PXCodeDefenderConnector, self).__init__(
            config=config,
            is_test=is_test,
            connector_name=CONNECTOR_NAME,
        )

    def _initialize_managers(self):
        # type: () -> None
        """Initializes PerimeterXManager"""
        self.logger.info("Connecting to PerimeterX manager")
        self.px_manager = PerimeterXManager(
            slack_channel=self.param_slack_channel,
            slack_api_key=self.param_slack_api_key,
            connector_type="slack",
            offset_in_ms=self.last_run_time,
        )

    def _fetch_alert(self, alert):
        """Returns an alert, which is an aggregation of basic events. (ie: Arcsight's correlation, QRadar's Offense)"""
        self.logger.info(
            "-------------- Started processing Alert {}".format(
                round(float(alert["ts"]) * 100000),
            ),
            alert_id=round(float(alert["ts"]) * 100000),
        )

        alert_info = AlertInfo()

        # ----------------------------- Alert Fields initilization START -----------------------------
        # ... Replace this DUMMY VALUES !!! ...

        # Each alert_info has a unique key composed of alert_info.name+alert_info.display_id. This key is used to validate data is digested only once by the Siemplify System - to avoid duplicates.
        # If an alert_info has a uniqe_key that has already been digested, it will be ignored.
        # The uniqueness must be persistent, even after server restart\ refetching of the same alert, multiple runs of the same API queries, etc.
        alert_info.display_id = round(float(alert["ts"]) * 1000000)
        alert_info.ticket_id = round(
            float(alert["ts"]) * 1000000,
        )  # In default, ticket_id = display_id. But, if for some reason the external alert id, is different then the composite's key display_id, you can save the original external alert id in this "ticket_id" field.
        alert_info.name = "Code Defender " + alert["severity"] + " Alert"
        alert_info.rule_generator = alert[
            "title"
        ]  # Describes the name of the siem's rule, that caused the aggregation of the alert.
        alert_info.start_time = round(
            float(alert["ts"]) * 1000,
        )  # Times should be saved in UnixTime. You may use SiemplifyUtils.convert_datetime_to_unix_time, or SiemplifyUtils.convert_string_to_datetime
        alert_info.end_time = round(
            float(alert["ts"]) * 1000,
        )  # Take the current time from Slack but we need to +1 ms since slack timestamps are finer and we could end up in a loop
        alert_info.slack_time = round(float(alert["ts"]) * 1000000)
        alert_info.priority = self.VENDOR_RISK_MAP[
            alert["severity"]
        ]  # Informative = -1,Low = 40,Medium = 60,High = 80,Critical = 100.
        alert_info.device_vendor = VENDOR  # This field, may be fetched from the Original Alert. If you build this alert manualy, Describe the source vendor of the data. (ie: Microsoft, Mcafee)
        alert_info.device_product = PRODUCT  # This field, may be fetched from the Original Alert. If you build this alert manualy, Describe the source product of the data. (ie: ActiveDirectory, AntiVirus)
        # ----------------------------- Alert Fields initilization END -----------------------------

        self.logger.info(
            "---------- Events fetching started for alert  {}".format(
                round(float(alert["ts"]) * 100000),
            ),
        )

        # Gather the Event Details
        event = {}
        event["StartTime"] = round(float(alert["ts"]) * 1000)
        event["EndTime"] = round(float(alert["ts"]) * 1000)
        event["category"] = alert["text"]
        event["name"] = alert["title"]
        event["scriptName"] = alert["script"]
        event["hostDomain"] = alert["domain"]
        event["portalDeepLink"] = alert["deepLink"]
        event["fullURL"] = alert["script"][2:-2]
        event["details"] = alert["fullText"]
        alert_info.events.append(event)

        self.logger.info(
            "-------------- Finished processing Alert {}".format(
                round(float(alert["ts"]) * 100000),
            ),
            alert_id=round(float(alert["ts"]) * 100000),
        )
        return alert_info


@output_handler
def main(is_test=False):
    px_cd_connector = PXCodeDefenderConnector(is_test=is_test)
    px_cd_connector.run()


if __name__ == "__main__":
    # Connectors are run in iterations. The interval is configurable from the ConnectorsScreen UI.
    is_test_run = not (len(sys.argv) < 2 or sys.argv[1] == "True")
    main(is_test_run)
