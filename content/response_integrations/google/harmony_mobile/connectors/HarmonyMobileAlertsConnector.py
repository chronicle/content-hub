from __future__ import annotations
from soar_sdk.SiemplifyUtils import output_handler, unix_now
from soar_sdk.SiemplifyConnectors import SiemplifyConnectorExecution
from TIPCommon import extract_connector_param
from ..core.constants import (
    CONNECTOR_NAME,
    DEFAULT_TIME_FRAME,
    DEFAULT_LIMIT,
    RISK_MAP,
    PARAMETERS_DEFAULT_DELIMITER,
)
from ..core.UtilsManager import (
    read_ids,
    write_ids,
    get_last_success_time,
    is_approaching_timeout,
    get_environment_common,
    is_overflowed,
    save_timestamp,
    pass_whitelist_filter,
    UNIX_FORMAT,
)
from ..core.HarmonyMobileManager import HarmonyMobileManager
from soar_sdk.SiemplifyConnectorsDataModel import AlertInfo
import sys


connector_starting_time = unix_now()


@output_handler
def main(is_test_run):
    siemplify = SiemplifyConnectorExecution()
    siemplify.script_name = CONNECTOR_NAME
    processed_alerts = []

    if is_test_run:
        siemplify.LOGGER.info(
            '***** This is an "IDE Play Button"\\"Run Connector once" test run ******'
        )

    siemplify.LOGGER.info("------------------- Main - Param Init -------------------")

    api_root = extract_connector_param(
        siemplify, param_name="API Root", is_mandatory=True, print_value=True
    )
    client_id = extract_connector_param(
        siemplify, param_name="Client ID", is_mandatory=True, print_value=True
    )
    client_secret = extract_connector_param(
        siemplify, param_name="Client Secret", is_mandatory=True
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
    min_risk = extract_connector_param(
        siemplify, param_name="Lowest Risk To Fetch", print_value=True
    )
    hours_backwards = extract_connector_param(
        siemplify,
        param_name="Max Hours Backwards",
        input_type=int,
        default_value=DEFAULT_TIME_FRAME,
        print_value=True,
    )
    fetch_limit = extract_connector_param(
        siemplify,
        param_name="Max Alerts To Fetch",
        input_type=int,
        default_value=DEFAULT_LIMIT,
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

    try:
        siemplify.LOGGER.info("------------------- Main - Started -------------------")

        if min_risk:
            min_risk = min_risk.lower()

            if min_risk not in list(RISK_MAP.values()):
                risk_items = [item.capitalize() for item in list(RISK_MAP.values())]
                raise ValueError(

                    f"Invalid value provided for 'Lowest Risk To Fetch' parameter."
                    f"Possible values are: "
                    f"{PARAMETERS_DEFAULT_DELIMITER.join(risk_items)}."
                )

        if fetch_limit < 0:
            siemplify.LOGGER.info(
                f'"Max Alerts To Fetch" must be non-negative. The default value '
                f"{DEFAULT_LIMIT} will be used"
            )
            fetch_limit = DEFAULT_LIMIT

        if hours_backwards < 0:
            siemplify.LOGGER.info(
                f'"Max Hours Backwards" must be non-negative. The default value '
                f"{DEFAULT_TIME_FRAME} will be used"
            )
            hours_backwards = DEFAULT_TIME_FRAME

        # Read already existing alerts ids
        existing_ids = read_ids(siemplify)
        siemplify.LOGGER.info(f"Successfully loaded {len(existing_ids)} existing ids")

        manager = HarmonyMobileManager(
            api_root=api_root,
            client_id=client_id,
            client_secret=client_secret,
            verify_ssl=verify_ssl,
            siemplify_logger=siemplify.LOGGER,
        )

        fetched_alerts = []
        filtered_alerts = manager.get_alerts(
            existing_ids=existing_ids,
            limit=fetch_limit,
            start_timestamp=get_last_success_time(
                siemplify=siemplify,
                offset_with_metric={"hours": hours_backwards},
                time_format=UNIX_FORMAT,
            ),
            risk=min_risk,
        )

        siemplify.LOGGER.info(f"Fetched {len(filtered_alerts)} alerts")

        if is_test_run:
            siemplify.LOGGER.info("This is a TEST run. Only 1 alert will be processed.")
            filtered_alerts = filtered_alerts[:1]

        for alert in filtered_alerts:
            try:
                if is_approaching_timeout(script_timeout, connector_starting_time):
                    siemplify.LOGGER.info(
                        "Timeout is approaching. Connector will gracefully exit"
                    )
                    break

                if len(processed_alerts) >= fetch_limit:
                    # Provide slicing for the alerts amount.
                    siemplify.LOGGER.info(
                        "Reached max number of alerts cycle. No more alerts will be processed in this cycle."
                    )
                    break

                siemplify.LOGGER.info(f"Started processing alert {alert.id}")

                if not pass_filters(
                    siemplify, whitelist_as_a_blacklist, alert, "threat_factors"
                ):
                    # Update existing alerts
                    existing_ids.append(alert.id)
                    fetched_alerts.append(alert)
                    continue

                alert.set_events()

                # Update existing alerts
                existing_ids.append(alert.id)
                fetched_alerts.append(alert)

                alert_info = alert.get_alert_info(
                    AlertInfo(),
                    get_environment_common(
                        siemplify, environment_field_name, environment_regex_pattern
                    ),
                    device_product_field,
                )

                if is_overflowed(siemplify, alert_info, is_test_run):
                    siemplify.LOGGER.info(
                        f"{alert_info.rule_generator}-{alert_info.ticket_id}"
                        f"-{alert_info.environment}"
                        f"-{alert_info.device_product} found as overflow alert."
                        f" Skipping..."
                    )
                    # If is overflowed we should skip
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
            save_timestamp(
                siemplify=siemplify, alerts=fetched_alerts, timestamp_key="timestamp"
            )

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


def pass_filters(siemplify, whitelist_as_a_blacklist, alert, model_key):
    # All alert filters should be checked here
    if not pass_whitelist_filter(siemplify, whitelist_as_a_blacklist, alert, model_key):
        return False

    return True


if __name__ == "__main__":
    # Connectors are run in iterations. The interval is configurable from the ConnectorsScreen UI.
    is_test = not (len(sys.argv) < 2 or sys.argv[1] == "True")
    main(is_test)
