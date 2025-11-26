from __future__ import annotations

import sys

from EnvironmentCommon import GetEnvironmentCommonFactory
from soar_sdk.SiemplifyConnectors import SiemplifyConnectorExecution
from soar_sdk.SiemplifyConnectorsDataModel import AlertInfo
from soar_sdk.SiemplifyUtils import output_handler, unix_now
from TIPCommon.extraction import extract_connector_param
from TIPCommon.filters import pass_whitelist_filter
from TIPCommon.smp_io import read_ids, write_ids
from TIPCommon.smp_time import (
    is_approaching_timeout,
    save_timestamp,
)
from TIPCommon.utils import is_overflowed
from TIPCommon.validation import ParameterValidator

from ..core import constants
from ..core.DarktraceManager import DarktraceManager
from ..core.UtilsManager import behaviour_check_value, calculate_last_success_time

connector_starting_time = unix_now()


@output_handler
def main(is_test_run):
    siemplify = SiemplifyConnectorExecution()
    siemplify.script_name = constants.CONNECTOR_NAME
    processed_alerts = []

    if is_test_run:
        siemplify.LOGGER.info(
            '***** This is an "IDE Play Button"\\"Run Connector once" test run ******'
        )

    siemplify.LOGGER.info("------------------- Main - Param Init -------------------")

    api_root = extract_connector_param(
        siemplify, param_name="API Root", is_mandatory=True, print_value=True
    )
    api_token = extract_connector_param(
        siemplify, param_name="API Token", is_mandatory=True, print_value=True
    )
    api_private_token = extract_connector_param(
        siemplify,
        param_name="API Private Token",
        remove_whitespaces=False,
        print_value=False,
        is_mandatory=True,
    )
    verify_ssl = extract_connector_param(
        siemplify,
        param_name="Verify SSL",
        is_mandatory=True,
        input_type=bool,
        print_value=True,
    )

    environment_field_name = extract_connector_param(
        siemplify, param_name="Environment Field Name", print_value=True
    )
    environment_regex_pattern = extract_connector_param(
        siemplify, param_name="Environment Regex Pattern", print_value=True
    )

    script_timeout = extract_connector_param(
        siemplify,
        param_name="PythonProcessTimeout",
        is_mandatory=True,
        input_type=int,
        print_value=True,
    )
    min_score = extract_connector_param(
        siemplify,
        param_name="Lowest Model Breach Score To Fetch",
        input_type=int,
        print_value=True,
        default_value=constants.DEFAULT_MIN_SCORE,
    )
    min_priority = extract_connector_param(
        siemplify,
        param_name="Lowest Priority To Fetch",
        input_type=int,
        print_value=True,
    )
    hours_backwards = extract_connector_param(
        siemplify,
        param_name="Max Hours Backwards",
        input_type=int,
        default_value=constants.DEFAULT_TIME_FRAME,
        print_value=True,
    )
    padding_time = extract_connector_param(
        siemplify,
        param_name="Padding Time",
        input_type=int,
        print_value=True,
    )
    fetch_limit = extract_connector_param(
        siemplify,
        param_name="Max Model Breaches To Fetch",
        input_type=int,
        default_value=constants.DEFAULT_LIMIT,
        print_value=True,
    )

    whitelist_as_a_blacklist = extract_connector_param(
        siemplify,
        "Use whitelist as a blacklist",
        is_mandatory=True,
        input_type=bool,
        print_value=True,
    )

    device_product_field = extract_connector_param(
        siemplify, "DeviceProductField", is_mandatory=True
    )
    behaviour_visibility_filter = extract_connector_param(
        siemplify, param_name="Behaviour Visibility", print_value=True
    )
    if min_priority is not None:
        validator = ParameterValidator(siemplify)
        validator.validate_range(
            param_name="Lowest Priority To Fetch",
            value=min_priority,
            min_limit=constants.MIN_PRIORITY,
            max_limit=constants.MAX_PRIORITY,
        )

    try:
        siemplify.LOGGER.info("------------------- Main - Started -------------------")

        if behaviour_visibility_filter and not behaviour_check_value(behaviour_visibility_filter):
            raise SystemExit(
                "Invalid value provided for the parameter"
                ' "Behaviour Visibility". Supported values are '
                "Critical, Suspicious, Compliance, Informational"
            )

        if fetch_limit > constants.MAX_LIMIT:
            siemplify.LOGGER.info(
                "Max Model Breaches To Fetch exceeded the "
                f"maximum limit of {constants.MAX_LIMIT}. "
                f"The default value {constants.DEFAULT_LIMIT} will be used"
            )
            fetch_limit = constants.DEFAULT_LIMIT

        existing_ids = read_ids(siemplify)
        siemplify.LOGGER.info(f"Successfully loaded {len(existing_ids)} existing ids")

        manager = DarktraceManager(
            api_root=api_root,
            api_token=api_token,
            api_private_token=api_private_token,
            verify_ssl=verify_ssl,
            siemplify_logger=siemplify.LOGGER,
        )

        fetched_alerts = []

        last_success_timestamp = calculate_last_success_time(
            siemplify, hours_backwards, padding_time
        )

        filtered_alerts = manager.get_alerts(
            existing_ids=existing_ids,
            limit=fetch_limit,
            start_timestamp=last_success_timestamp,
            score=min_score,
            siemplify=siemplify,
            min_priority=min_priority,
        )

        siemplify.LOGGER.info(f"Fetched {len(filtered_alerts)} alerts")

        if is_test_run:
            siemplify.LOGGER.info("This is a TEST run. Only 1 alert will be processed.")
            filtered_alerts = filtered_alerts[:1]

        for alert in filtered_alerts:
            try:
                if is_approaching_timeout(script_timeout, connector_starting_time):
                    siemplify.LOGGER.info("Timeout is approaching. Connector will gracefully exit")
                    break

                if len(processed_alerts) >= fetch_limit:
                    siemplify.LOGGER.info(
                        "Reached max number of alerts cycle. "
                        "No more alerts will be processed in this cycle."
                    )
                    break

                siemplify.LOGGER.info(f"Started processing alert {alert.id} - {alert.name}")

                if not pass_whitelist_filter(siemplify, whitelist_as_a_blacklist, alert, "name"):
                    existing_ids.append(alert.id)
                    fetched_alerts.append(alert)
                    continue

                alert.set_events(manager.get_model_breach_details(alert.id))

                existing_ids.append(alert.id)
                fetched_alerts.append(alert)

                environment_common = GetEnvironmentCommonFactory.create_environment_manager(
                    siemplify=siemplify,
                    environment_field_name=environment_field_name,
                    environment_regex_pattern=environment_regex_pattern,
                )
                alert_info = alert.get_alert_info(
                    AlertInfo(), environment_common, device_product_field
                )

                if is_overflowed(siemplify, alert_info, is_test_run):
                    siemplify.LOGGER.info(
                        f"{alert_info.rule_generator}-{alert_info.ticket_id}"
                        f"-{alert_info.environment}"
                        f"-{alert_info.device_product} "
                        "found as overflow alert. Skipping..."
                    )
                    continue

                if behaviour_visibility_filter and len(alert_info.events) != 0:
                    try:
                        model_category = alert_info.events[0]["model_now_category"].lower()
                    except:  # noqa: E722
                        model_category = alert_info.events[0]["model_then_category"].lower()
                    if model_category not in behaviour_visibility_filter.lower():
                        continue

                processed_alerts.append(alert_info)
                siemplify.LOGGER.info(f"Alert {alert.id} was created.")

            except Exception as e:
                siemplify.LOGGER.error(f"Failed to process alert {alert.id}")
                siemplify.LOGGER.exception(e)

                if is_test_run:
                    raise
            siemplify.LOGGER.info(f"Finished processing alert {alert.id}")

        if not is_test_run:
            siemplify.LOGGER.info("Saving existing ids.")
            write_ids(siemplify, existing_ids)
            save_timestamp(siemplify=siemplify, alerts=fetched_alerts, timestamp_key="time")

        siemplify.LOGGER.info(
            f"Alerts processed: {len(processed_alerts)} out of {len(fetched_alerts)}"
        )

    except Exception as e:
        siemplify.LOGGER.error(f"Got exception on main handler. Error: {e}")
        siemplify.LOGGER.exception(e)

        if is_test_run:
            raise

    siemplify.LOGGER.info(f"Created total of {len(processed_alerts)} cases")
    siemplify.LOGGER.info("------------------- Main - Finished -------------------")
    siemplify.return_package(processed_alerts)


if __name__ == "__main__":
    is_test = not (len(sys.argv) < 2 or sys.argv[1] == "True")
    main(is_test)
