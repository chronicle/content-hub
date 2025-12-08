from __future__ import annotations

from EnvironmentCommon import GetEnvironmentCommonFactory as EnvCommon
from soar_sdk.SiemplifyConnectors import SiemplifyConnectorExecution
from soar_sdk.SiemplifyConnectorsDataModel import AlertInfo
from soar_sdk.SiemplifyUtils import convert_unixtime_to_datetime, output_handler, unix_now
from TIPCommon.consts import UNIX_FORMAT
from TIPCommon.extraction import extract_connector_param
from TIPCommon.filters import pass_whitelist_filter
from TIPCommon.smp_io import read_content, read_ids, write_content, write_ids
from TIPCommon.smp_time import (
    get_last_success_time,
    is_approaching_timeout,
    siemplify_save_timestamp,
)
from TIPCommon.utils import is_overflowed
from TIPCommon.validation import ParameterValidator

from ..core import constants
from ..core.DarktraceManager import DarktraceManager
from ..core.UtilsManager import extract_connector_param_wrapper, hours_to_milliseconds

connector_current_time = unix_now()


@output_handler
def main() -> None:
    siemplify = SiemplifyConnectorExecution()
    siemplify.script_name = constants.AI_CONNECTOR_NAME
    param_validator = ParameterValidator(siemplify)
    processed_alerts = []

    if siemplify.is_test_run:
        siemplify.LOGGER.info(
            '***** This is an "IDE Play Button""Run Connector once" test run ******'
        )

    siemplify.LOGGER.info("--------------- Main - Param Init ---------------")

    api_root = extract_connector_param(
        siemplify, param_name="API Root", is_mandatory=True, print_value=True
    )
    api_token = extract_connector_param(
        siemplify, param_name="API Token", is_mandatory=True, print_value=True
    )
    api_private_token = extract_connector_param(
        siemplify,
        param_name="API Private Token",
        is_mandatory=True,
        remove_whitespaces=False,
        print_value=False,
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
    whitelist_as_a_blacklist = extract_connector_param(
        siemplify,
        param_name="Use dynamic list as a blocklist",
        is_mandatory=True,
        input_type=bool,
        print_value=True,
    )
    device_product_field = extract_connector_param(
        siemplify, param_name="DeviceProductField", is_mandatory=True
    )

    try:
        min_score = extract_connector_param_wrapper(
            siemplify,
            param_name="Lowest AI Incident Score To Fetch",
            input_type=int,
            print_value=True,
            default_value=constants.AI_DEFAULT_MIN_SCORE,
            is_mandatory=True,
        )
        hours_backwards = extract_connector_param_wrapper(
            siemplify,
            param_name="Max Hours Backwards",
            input_type=int,
            default_value=constants.AI_DEFAULT_TIME_FRAME,
            print_value=True,
        )
        fetch_limit = extract_connector_param_wrapper(
            siemplify,
            param_name="Max AI Incidents To Fetch",
            input_type=int,
            default_value=constants.AI_DEFAULT_LIMIT,
            print_value=True,
        )

        siemplify.LOGGER.info("--------------- Main - Started ---------------")

        lowest_severity = param_validator.validate_range(
            param_name="Lowest AI Incident Score To Fetch",
            value=min_score,
            min_limit=constants.AI_SCORE_MIN_VALUE,
            max_limit=constants.AI_SCORE_MAX_VALUE,
        )

        fetch_limit = param_validator.validate_range(
            param_name="Max AI Incidents To Fetch",
            value=fetch_limit,
            min_limit=constants.AI_INCIDENTS_MIN_VALUE,
            max_limit=constants.AI_INCIDENTS_MAX_VALUE,
        )

        hours_backwards = param_validator.validate_positive(
            param_name="Max Hours Backwards", value=hours_backwards
        )
        existing_ids = read_ids(siemplify)
        siemplify.LOGGER.info(f"Successfully loaded {len(existing_ids)} existing ids")

        manager = DarktraceManager(
            api_root=api_root,
            api_token=api_token,
            api_private_token=api_private_token,
            verify_ssl=verify_ssl,
            siemplify_logger=siemplify.LOGGER,
        )

        start_time = read_content(
            siemplify=siemplify,
            file_name=constants.AI_CONNECTOR_NAME,
            db_key="repeat_time",
        )
        if not start_time or start_time == constants.REPEAT_TIME_DEFAULT_VALUE:
            start_time = get_last_success_time(
                siemplify=siemplify,
                offset_with_metric={"hours": hours_backwards},
                time_format=UNIX_FORMAT,
            )
        else:
            siemplify.LOGGER.info(
                "Using previous last success time: "
                f"{convert_unixtime_to_datetime(start_time)}"
                ", to get un-fetched alerts from that time period"
            )
        end_time = start_time + hours_to_milliseconds(constants.SPLIT_INTERVAL)
        padding_validate = connector_current_time - hours_to_milliseconds(
            constants.PADDING_INTERVAL
        )

        if end_time > connector_current_time:
            end_time = connector_current_time

        if end_time == connector_current_time and start_time > padding_validate:
            start_time = end_time - hours_to_milliseconds(constants.PADDING_INTERVAL)

        processed_alerts_counter = 0
        fetched_alerts = manager.get_ai_alerts(
            existing_ids=existing_ids,
            start_timestamp=start_time,
            end_timestamp=end_time,
            score=lowest_severity,
            siemplify=siemplify,
        )

        fetched_alerts = sorted(fetched_alerts, key=lambda device: device.time)

        fetched_alerts_ids = {alert.id for alert in fetched_alerts}

        siemplify.LOGGER.info(f"Fetched {len(fetched_alerts)} alerts")

        if siemplify.is_test_run:
            siemplify.LOGGER.info("This is a TEST run. Only 1 alert will be processed.")
            fetched_alerts = fetched_alerts[:1]

        for alert in fetched_alerts:
            try:
                if alert.id in existing_ids:
                    continue

                if is_approaching_timeout(script_timeout, connector_current_time):
                    siemplify.LOGGER.info("Timeout is approaching. Connector will gracefully exit")
                    break

                if len(processed_alerts) >= fetch_limit:
                    # Provide slicing for the alerts amount.
                    siemplify.LOGGER.info(
                        "Reached max number of alerts cycle. "
                        "No more alerts will be processed in this cycle."
                    )
                    break

                siemplify.LOGGER.info(f"Started processing alert {alert.id} - {alert.name}")
                if not pass_whitelist_filter(siemplify, whitelist_as_a_blacklist, alert, "name"):
                    continue

                processed_alerts_counter += 1
                existing_ids.append(alert.id)
                environment_common = EnvCommon.create_environment_manager(
                    siemplify=siemplify,
                    environment_field_name=environment_field_name,
                    environment_regex_pattern=environment_regex_pattern,
                )
                alert_info = alert.get_alert_info(
                    AlertInfo(), environment_common, device_product_field
                )

                if is_overflowed(siemplify, alert_info, siemplify.is_test_run):
                    siemplify.LOGGER.info(
                        f"{alert_info.rule_generator}-{alert_info.ticket_id}"
                        f"-{alert_info.environment}"
                        f"-{alert_info.device_product} found as "
                        "overflow alert. Skipping..."
                    )
                    continue

                processed_alerts.append(alert_info)
                siemplify.LOGGER.info(f"Alert {alert.id} was created.")

            except Exception as e:
                siemplify.LOGGER.error(f"Failed to process alert {alert.id}")
                siemplify.LOGGER.exception(e)

                if siemplify.is_test_run:
                    raise

            siemplify.LOGGER.info(f"Finished processing alert {alert.id}")

        if not siemplify.is_test_run:
            siemplify.LOGGER.info("Saving existing ids.")
            if processed_alerts_counter:
                write_ids(siemplify, ids=existing_ids, stored_ids_limit=constants.AI_MAX_LIMIT)
            if fetched_alerts_ids.issubset(existing_ids):
                siemplify_save_timestamp(siemplify, new_timestamp=end_time)
                write_content(
                    siemplify=siemplify,
                    content_to_write=constants.REPEAT_TIME_DEFAULT_VALUE,
                    file_name=constants.DARKTRACE_AI_FILE_NAME,
                    db_key=constants.REPEAT_TIME_DB_KEY,
                )
            else:
                write_content(
                    siemplify=siemplify,
                    content_to_write=start_time,
                    file_name=constants.DARKTRACE_AI_FILE_NAME,
                    db_key=constants.REPEAT_TIME_DB_KEY,
                )

        siemplify.LOGGER.info(
            f"Alerts processed: {len(processed_alerts)} out of {processed_alerts_counter}"
        )
    except Exception as e:
        siemplify.LOGGER.error(f"Got exception on main handler. Error: {e}")
        siemplify.LOGGER.exception(e)

        if siemplify.is_test_run:
            raise

    siemplify.LOGGER.info(f"Created total of {len(processed_alerts)} cases")
    siemplify.LOGGER.info("--------------- Main - Finished ---------------")
    siemplify.return_package(processed_alerts)


if __name__ == "__main__":
    main()
