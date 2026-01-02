from __future__ import annotations

import sys
from datetime import datetime

from EnvironmentCommon import GetEnvironmentCommonFactory
from soar_sdk.SiemplifyConnectors import SiemplifyConnectorExecution
from soar_sdk.SiemplifyConnectorsDataModel import AlertInfo
from soar_sdk.SiemplifyUtils import output_handler, unix_now
from TIPCommon import (
    UNIX_FORMAT,
    extract_connector_param,
    get_last_success_time,
    is_approaching_timeout,
    is_overflowed,
    read_ids,
    save_timestamp,
    write_ids,
)

from ..core.constants import (
    CONNECTOR_NAME,
    DEFAULT_ENTITY_TYPE,
    DEFAULT_TIME_FRAME,
    DETECTION_CATEGORIES,
    MAX_IDS,
)
from ..core.UtilsManager import validate_integer, validate_limit_param
from ..core.VectraQUXExceptions import VectraQUXException
from ..core.VectraQUXManager import VectraQUXManager

# ==============================================================================
# This is a Connector Template + mock generator. This file objective is to demonstrate
#  how to build a connector, and exmplain the objective of each field.
# All the data generated here, is MOCK data. Enjoy.
# ==============================================================================


connector_starting_time = unix_now()


def validate_input_params(
    entity_type,
    hours_backwards,
    min_threat_score,
    min_certainty_score,
    detection_category,
    limit,
):
    entity_type = entity_type.lower()
    if entity_type not in {"account", "host"}:
        raise VectraQUXException("Entity type should be one of the ['Account', 'Host']")

    if hours_backwards:
        hours_backwards = validate_integer(
            hours_backwards,
            zero_allowed=True,
            field_name="Max Hours Backwards",
        )

    if min_threat_score:
        min_threat_score = validate_integer(
            min_threat_score,
            zero_allowed=True,
            field_name="Threat Score GTE",
        )

    if min_certainty_score:
        min_certainty_score = validate_integer(
            min_certainty_score,
            zero_allowed=True,
            field_name="Certainty Score GTE",
        )

    if detection_category and detection_category.strip():
        detection_category = detection_category.strip()
        if detection_category.lower() not in DETECTION_CATEGORIES:
            raise VectraQUXException(
                f"Detection Category should be one of the {DETECTION_CATEGORIES}",
            )

    limit = validate_integer(
        validate_limit_param(limit),
        zero_allowed=True,
        field_name="Limit",
    )

    return (
        entity_type,
        hours_backwards,
        min_threat_score,
        min_certainty_score,
        detection_category,
        limit,
    )


@output_handler
def main(is_test_run):
    processed_alerts = []
    siemplify = SiemplifyConnectorExecution()
    siemplify.script_name = CONNECTOR_NAME

    siemplify.LOGGER.info("==================== Main - Param Init ====================")

    api_root = extract_connector_param(
        siemplify,
        param_name="API Root",
        input_type=str,
        is_mandatory=True,
        print_value=True,
    )
    api_token = extract_connector_param(
        siemplify,
        param_name="API Token",
        input_type=str,
        is_mandatory=True,
        print_value=False,
        remove_whitespaces=False,
    )
    verify_ssl = extract_connector_param(
        siemplify,
        param_name="Verify SSL",
        default_value=True,
        input_type=bool,
        is_mandatory=True,
        print_value=True,
    )

    environment_field_name = extract_connector_param(
        siemplify,
        param_name="Environment Field Name",
        default_value="",
        input_type=str,
        print_value=True,
    )
    environment_regex_pattern = extract_connector_param(
        siemplify,
        param_name="Environment Regex Pattern",
        input_type=str,
        print_value=True,
    )
    hours_backwards = extract_connector_param(
        siemplify,
        param_name="Max Hours Backwards",
        input_type=str,
        default_value=DEFAULT_TIME_FRAME,
        print_value=True,
    )
    entity_type = extract_connector_param(
        siemplify,
        param_name="Entity Type",
        input_type=str,
        default_value=DEFAULT_ENTITY_TYPE,
        is_mandatory=True,
        print_value=True,
    )
    min_threat_score = extract_connector_param(
        siemplify,
        param_name="Threat Score GTE",
        input_type=str,
        is_mandatory=False,
        print_value=True,
    )
    min_certainty_score = extract_connector_param(
        siemplify,
        param_name="Certainty Score GTE",
        input_type=str,
        is_mandatory=False,
        print_value=True,
    )
    detection_category = extract_connector_param(
        siemplify,
        param_name="Detection Category",
        input_type=str,
        is_mandatory=False,
        print_value=True,
    )
    detection_type = extract_connector_param(
        siemplify,
        param_name="Detection Type",
        input_type=str,
        is_mandatory=False,
        print_value=True,
    )
    specific_tag = extract_connector_param(
        siemplify,
        param_name="Specific Tag",
        input_type=str,
        is_mandatory=False,
        print_value=True,
    )
    partial_tag = extract_connector_param(
        siemplify,
        param_name="Partial Tag",
        input_type=str,
        is_mandatory=False,
        print_value=True,
    )
    user_query = extract_connector_param(
        siemplify,
        param_name="Query",
        input_type=str,
        is_mandatory=False,
        print_value=True,
    )
    limit = extract_connector_param(
        siemplify,
        param_name="Limit",
        input_type=str,
        is_mandatory=False,
        print_value=True,
    )
    python_process_timeout = extract_connector_param(
        siemplify,
        param_name="PythonProcessTimeout",
        input_type=int,
        is_mandatory=True,
        print_value=True,
    )
    device_product_field = extract_connector_param(
        siemplify,
        "DeviceProductField",
        is_mandatory=True,
    )

    try:
        siemplify.LOGGER.info("------------------- Main - Started -------------------")

        # Validate input parameters
        (
            entity_type,
            hours_backwards,
            min_threat_score,
            min_certainty_score,
            detection_category,
            limit,
        ) = validate_input_params(
            entity_type,
            hours_backwards,
            min_threat_score,
            min_certainty_score,
            detection_category,
            limit,
        )

        # Read existing alerts ids
        siemplify.LOGGER.info("Reading existing alerts ids...")
        existing_ids = read_ids(siemplify)

        if is_test_run:
            siemplify.LOGGER.info("This is a TEST run. Only 1 alert will be processed.")
            limit = 100

        start_time = get_last_success_time(
            siemplify=siemplify,
            offset_with_metric={"hours": hours_backwards},
            time_format=UNIX_FORMAT,
        )

        vectra_manager = VectraQUXManager(
            api_root,
            api_token,
            verify_ssl=verify_ssl,
            siemplify=siemplify,
        )

        filtered_alerts = vectra_manager.list_entities_by_filters(
            existing_ids=set(existing_ids),
            entity_type=entity_type,
            start_time=start_time,
            limit=limit,
            min_threat_score=min_threat_score,
            min_certainty_score=min_certainty_score,
            detection_category=detection_category,
            detection_type=detection_type,
            specific_tag=specific_tag,
            partial_tag=partial_tag,
            user_query=user_query,
        )

        siemplify.LOGGER.info(f"Found {len(filtered_alerts)} entities.")

        # Sorting the records based on the timestamp field
        filtered_alerts = sorted(
            filtered_alerts,
            key=lambda x: datetime.strptime(x.last_timestamp, "%Y-%m-%dT%H:%M:%SZ"),
        )

        for alert in filtered_alerts:
            siemplify.LOGGER.info(f"Started processing entity {alert.id}")
            try:
                if is_approaching_timeout(
                    connector_starting_time,
                    python_process_timeout,
                ):
                    siemplify.LOGGER.info(
                        "Timeout is approaching. Connector will gracefully exit",
                    )
                    break

                detections = vectra_manager.list_entity_detections(
                    alert.id,
                    entity_type,
                    limit=0,
                )

                if not detections:
                    siemplify.LOGGER.info(
                        f"No detection found. Skipping entity {alert.id}",
                    )
                    continue

                environment_common = (
                    GetEnvironmentCommonFactory.create_environment_manager(
                        siemplify,
                        environment_field_name,
                        environment_regex_pattern,
                    )
                )

                alert_info = alert.get_alert_info(
                    AlertInfo(),
                    detections,
                    entity_type,
                    environment_common,
                    device_product_field,
                )

                # Update existing alerts
                existing_ids.append(alert_info.ticket_id)

                if is_overflowed(siemplify, alert_info, is_test_run):
                    siemplify.LOGGER.info(
                        f"{alert_info.rule_generator!s}-{alert_info.ticket_id!s}"
                        f"-{alert_info.environment!s}"
                        f"-{alert_info.device_product!s}"
                        " found as overflow alert. Skipping.",
                    )
                    # If is overflowed we should skip
                    continue

                processed_alerts.append(alert_info)
                siemplify.LOGGER.info(f"Alert {alert_info.ticket_id} was created.")

            except Exception as e:
                siemplify.LOGGER.error(
                    f"Failed to process entity {alert.id}. "
                    f"Any further entities will not be processed.",
                )
                siemplify.LOGGER.exception(e)

                if is_test_run:
                    raise

                break

            siemplify.LOGGER.info(f"Finished processing entity {alert.id}")

            if is_test_run:
                break

        if not is_test_run:
            save_timestamp(
                siemplify=siemplify,
                alerts=processed_alerts,
                timestamp_key="end_time",
            )
            write_ids(siemplify, existing_ids, stored_ids_limit=MAX_IDS)

    except Exception as err:
        siemplify.LOGGER.error(f"Got exception on main handler. Error: {err}")
        siemplify.LOGGER.exception(err)

        if is_test_run:
            raise

    siemplify.LOGGER.info(f"Created total of {len(processed_alerts)} cases")
    siemplify.LOGGER.info("------------------- Main - Finished -------------------")
    siemplify.return_package(processed_alerts)


if __name__ == "__main__":
    # Connectors are run in iterations. The interval is configurable from the ConnectorsScreen UI.
    is_test_run = not (len(sys.argv) < 2 or sys.argv[1] == "True")
    main(is_test_run)
