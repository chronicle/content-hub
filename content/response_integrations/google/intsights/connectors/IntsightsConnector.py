from __future__ import annotations
import sys

from soar_sdk.SiemplifyConnectors import CaseInfo, SiemplifyConnectorExecution
from soar_sdk.SiemplifyUtils import (
    convert_string_to_unix_time,
    convert_unixtime_to_datetime,
    dict_to_flat,
    output_handler,
)

from ..core.IntsightsManager import IntsightsManager
from ..core.consts import VENDOR, PRIORITIES, CONNECTOR_SCRIPT_NAME
from TIPCommon import (
    extract_connector_param,
    is_overflowed,
    siemplify_save_timestamp,
    siemplify_fetch_timestamp,
)
from ..core.utils import validate_timestamp


class IntsightsConnector:

    def __init__(self, siemplify, intsights_manager):
        self.siemplify = siemplify
        self.intsights_manager = intsights_manager

    def build_case_info(self, alert):
        """
        Builds CaseInfo
        :params alert: {dict} Intsights alert
        :return: {CaseInfo} The newly created case
        """
        case_info = CaseInfo()

        self.siemplify.LOGGER.info(f"Build CaseInfo for alert {alert.alert_id}.")

        case_info.start_time = (
            convert_string_to_unix_time(alert.found_date) if alert.found_date else 1
        )
        case_info.end_time = case_info.start_time
        case_info.ticket_id = alert.alert_id
        case_info.display_id = case_info.ticket_id
        case_info.name = alert.title
        case_info.rule_generator = case_info.name
        case_info.device_product = f"{alert.network_type} - {alert.alert_type}"
        case_info.device_vendor = VENDOR
        case_info.priority = PRIORITIES.get(alert.severity, -1)

        case_info.events = [dict_to_flat(alert.to_json())]
        case_info.environment = self.siemplify.context.connector_info.environment

        return case_info


@output_handler
def main(test=False):
    siemplify = SiemplifyConnectorExecution()
    siemplify.script_name = CONNECTOR_SCRIPT_NAME
    output_variables, result_params, log_items = {}, {}, []

    if test:
        siemplify.LOGGER.info(
            '***** This is an "IDE Play Button"\\"Run Connector once" test run ******'
        )

    siemplify.LOGGER.info("------------------- Main - Param Init -------------------")

    server_address = extract_connector_param(
        siemplify, param_name="Api Root", is_mandatory=True
    )
    account_id = extract_connector_param(
        siemplify, param_name="Account ID", is_mandatory=True
    )
    api_key = extract_connector_param(
        siemplify, param_name="Api Key", is_mandatory=True
    )
    verify_ssl = extract_connector_param(
        siemplify, param_name="Verify SSL", is_mandatory=True, input_type=bool
    )
    max_days_backwards = extract_connector_param(
        siemplify,
        param_name="Max Days Backwards",
        is_mandatory=True,
        print_value=True,
        input_type=int,
    )
    max_alerts_per_cycle = extract_connector_param(
        siemplify,
        param_name="Max Alerts Per Cycle",
        is_mandatory=True,
        print_value=True,
        input_type=int,
    )

    try:
        siemplify.LOGGER.info("------------------- Main - Started -------------------")

        siemplify.LOGGER.info("Connecting to Intsights")
        intsights_manager = IntsightsManager(
            server_address,
            account_id,
            api_key,
            verify_ssl=verify_ssl,
            siemplify=siemplify,
        )
        result_params["Connection"] = "Success"

        # connector_scope
        intsights_connector = IntsightsConnector(siemplify, intsights_manager)

        # get last run timestamp
        last_run_timestamp = validate_timestamp(
            float(siemplify_fetch_timestamp(siemplify)), max_days_backwards
        )
        siemplify.LOGGER.info(f"Fetching alerts from {last_run_timestamp}.")

        alerts = intsights_manager.get_alerts(
            limit=max_alerts_per_cycle, date_from=last_run_timestamp
        )
        result_params["Alarms Fetching"] = "Success"

        siemplify.LOGGER.info(f"Fetched {len(alerts)} alerts")

        success_alarms = 0
        failed_alarms = 0
        processed_alerts = []
        fetched_alerts = []

        if test:
            siemplify.LOGGER.info("This is a TEST run. Only 1 alert will be processed.")
            alerts = alerts[:1]

        for alert in alerts:
            try:
                siemplify.LOGGER.info(f"Processing alert {alert.alert_id}.")
                case = intsights_connector.build_case_info(alert)
                fetched_alerts.append(case)

                is_overflow = False

                try:
                    is_overflow = is_overflowed(
                        siemplify=siemplify, alert_info=case, is_test_run=test
                    )

                except Exception as e:
                    failed_alarms += 1
                    siemplify.LOGGER.error(
                        f"Failed to detect overflow for Alert {case.name}"
                    )
                    siemplify.LOGGER.exception(e)

                if is_overflow:
                    siemplify.LOGGER.warn(
                        "{alertname}-{alertid}-{environ}-{product} found as overflow alert, "
                        "skipping this alert.".format(
                            alertname=case.name,
                            alertid=case.ticket_id,
                            environ=case.environment,
                            product=case.device_product,
                        )
                    )
                    continue

                processed_alerts.append(case)
                success_alarms += 1
                siemplify.LOGGER.info(f"Alert {alert.alert_id} was created.")

            except Exception as e:
                failed_alarms += 1
                siemplify.LOGGER.error(f"Couldn't process alert {alert.alert_id}.")
                siemplify.LOGGER.exception(e)

                if test:
                    raise

            siemplify.LOGGER.info(f"Finished processing Alert {alert.alert_id}")

        if not failed_alarms:
            result_params["Alarm processing"] = "Success"
        else:
            result_params["Alarm processing"] = (
                f"Failed. {failed_alarms} failed cases, {success_alarms} successful cases."
            )

        if not test and fetched_alerts:
            new_timestamp = (
                sorted(fetched_alerts, key=lambda case: case.start_time)[-1].start_time
                + 1
            )
            siemplify_save_timestamp(siemplify, new_timestamp=new_timestamp)
            siemplify.LOGGER.info(
                f"New timestamp {convert_unixtime_to_datetime(new_timestamp).isoformat()} has been saved"
            )

        siemplify.LOGGER.info(f"Created total of {len(processed_alerts)} cases")
        siemplify.LOGGER.info("------------------- Main - Finished -------------------")
        siemplify.return_package(processed_alerts, output_variables, log_items)

    except Exception as err:
        siemplify.LOGGER.error(f"Failed to run Intsights Connector. Error: {err}")
        siemplify.LOGGER.exception(err)
        if test:
            raise


if __name__ == "__main__":
    if len(sys.argv) < 2 or sys.argv[1] == "True":
        print("Main execution started")
        main()
    else:
        print("Test execution started")
        main(test=True)
