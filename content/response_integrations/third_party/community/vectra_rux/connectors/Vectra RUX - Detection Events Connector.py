from __future__ import annotations

import sys

from EnvironmentCommon import GetEnvironmentCommonFactory
from soar_sdk.SiemplifyConnectors import SiemplifyConnectorExecution
from soar_sdk.SiemplifyConnectorsDataModel import AlertInfo
from soar_sdk.SiemplifyUtils import output_handler, unix_now

from TIPCommon.consts import UNIX_FORMAT
from TIPCommon.extraction import extract_connector_param
from TIPCommon.smp_io import read_ids, write_ids
from TIPCommon.smp_time import (
    get_last_success_time,
    is_approaching_timeout,
    save_timestamp,
)
from TIPCommon.utils import is_overflowed

from ..core.constants import (
    DEFAULT_DETECTION_EVENTS_ENTITY_TYPES,
    DEFAULT_TIME_FRAME,
    DETECTIONS_CONNECTOR_NAME,
    MAX_DETECTION_EVENTS_HOURS_BACKWARDS,
    MAX_IDS,
)
from ..core.UtilsManager import validate_integer, validate_limit_param
from ..core.VectraRUXExceptions import VectraRUXException
from ..core.VectraRUXManager import VectraRUXManager

connector_starting_time = unix_now()


def validate_input_params(entity_type, hours_backwards, limit):
    entity_types = [single_type.strip().lower() for single_type in entity_type.split(",") if single_type.strip()]
    if not entity_types or any(single_type not in {"account", "host"} for single_type in entity_types):
        raise VectraRUXException("Entity type should be one of the ['Account', 'Host']")
    entity_type = ",".join(entity_types)

    if hours_backwards:
        hours_backwards = validate_integer(
            hours_backwards,
            zero_allowed=True,
            field_name="Max Hours Backwards",
        )
        if hours_backwards > MAX_DETECTION_EVENTS_HOURS_BACKWARDS:
            raise VectraRUXException(
                f"'Max Hours Backwards' must not exceed {MAX_DETECTION_EVENTS_HOURS_BACKWARDS} hours (5 days).",
            )
    limit = validate_integer(
        validate_limit_param(limit),
        zero_allowed=True,
        field_name="Limit",
    )

    return entity_type, hours_backwards, limit


@output_handler
def main(is_test_run):
    processed_alerts = []
    siemplify = SiemplifyConnectorExecution()
    siemplify.script_name = DETECTIONS_CONNECTOR_NAME

    siemplify.LOGGER.info("==================== Main - Param Init ====================")

    api_root = extract_connector_param(
        siemplify,
        param_name="API Root",
        input_type=str,
        is_mandatory=True,
        print_value=True,
    ).strip()
    client_id = extract_connector_param(
        siemplify,
        param_name="Client ID",
        input_type=str,
        is_mandatory=True,
        print_value=False,
    ).strip()
    client_secret = extract_connector_param(
        siemplify,
        param_name="Client Secret",
        input_type=str,
        print_value=False,
        is_mandatory=True,
    ).strip()
    environment_field_name = extract_connector_param(
        siemplify,
        param_name="Environment Field Name",
        default_value="",
        input_type=str,
        print_value=True,
    ).strip()

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
    ).strip() or str(DEFAULT_TIME_FRAME)
    entity_type = extract_connector_param(
        siemplify,
        param_name="Entity Type",
        input_type=str,
        default_value=DEFAULT_DETECTION_EVENTS_ENTITY_TYPES,
        is_mandatory=True,
        print_value=True,
    )
    unresolved_priority = extract_connector_param(
        siemplify,
        param_name="Unresolved Priority",
        input_type=bool,
        is_mandatory=False,
        print_value=True,
    )
    include_triaged = extract_connector_param(
        siemplify,
        param_name="Include Triaged",
        input_type=bool,
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
        entity_type, hours_backwards, limit = validate_input_params(
            entity_type,
            hours_backwards,
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

        vectra_manager = VectraRUXManager(
            api_root,
            client_id=client_id,
            client_secret=client_secret,
            siemplify=siemplify,
        )

        # connector_state: resume from the checkpoint persisted by the previous iteration.
        # Absent on the first run, in which case `start_time` (Max Hours Backwards) is used.
        stored_checkpoint = vectra_manager.get_detection_events_checkpoint()
        siemplify.LOGGER.info(f"Using stored checkpoint - {stored_checkpoint}")

        detection_events, new_checkpoint = vectra_manager.list_detection_events_by_filters(
            existing_ids=set(existing_ids),
            entity_type=entity_type,
            start_time=start_time,
            limit=limit,
            unresolved_priority=unresolved_priority,
            include_triaged=include_triaged,
            checkpoint=stored_checkpoint,
        )

        siemplify.LOGGER.info(f"Found {len(detection_events)} detection events.")

        environment_common = GetEnvironmentCommonFactory.create_environment_manager(
            siemplify,
            environment_field_name,
            environment_regex_pattern,
        )

        # Tracks whether every fetched event was attempted. The checkpoint returned by
        # list_detection_events_by_filters already marks the end of this whole batch, so
        # persisting it after an early break would skip whatever wasn't reached -
        # those events would never be fetched again. Only advance the checkpoint when
        # the batch is fully processed; otherwise the next iteration resumes from the
        # previous checkpoint and re-fetches the same batch (already-processed events
        # are filtered out again via existing_ids).
        batch_fully_processed = True

        for event in detection_events:
            siemplify.LOGGER.info(
                f"Started processing detection event {event.event_id} "
                f"(detection {event.detection_id})",
            )
            try:
                if is_approaching_timeout(
                    connector_starting_time,
                    python_process_timeout,
                ):
                    siemplify.LOGGER.info(
                        "Timeout is approaching. Connector will gracefully exit",
                    )
                    batch_fully_processed = False
                    break

                alert_info = event.get_alert_info(
                    AlertInfo(),
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
                    f"Failed to process detection event {event.event_id}. "
                    "Any further detection events will not be processed",
                )
                siemplify.LOGGER.exception(e)

                if is_test_run:
                    raise

                batch_fully_processed = False
                break

            siemplify.LOGGER.info(
                f"Finished processing detection event {event.event_id}",
            )

            if is_test_run:
                break

        if not is_test_run:
            save_timestamp(
                siemplify=siemplify,
                alerts=processed_alerts,
                timestamp_key="end_time",
            )
            write_ids(siemplify, existing_ids, stored_ids_limit=MAX_IDS)
            if not batch_fully_processed:
                siemplify.LOGGER.info(
                    "Batch was not fully processed (timeout or error). Skipping "
                    "checkpoint update so the next iteration resumes from the previous "
                    "checkpoint and re-fetches the remaining events.",
                )
            else:
                vectra_manager.save_detection_events_checkpoint(new_checkpoint)
                siemplify.LOGGER.info(
                    f"Saved checkpoint - {new_checkpoint} for the next iteration.",
                )

    except Exception as err:
        siemplify.LOGGER.error(f"Got exception on main handler. Error: {err}")
        siemplify.LOGGER.exception(err)

        if is_test_run:
            raise

    siemplify.LOGGER.info(f"Created total of {len(processed_alerts)} alerts")
    siemplify.LOGGER.info("------------------- Main - Finished -------------------")
    siemplify.return_package(processed_alerts)


if __name__ == "__main__":
    # Connectors are run in iterations. The interval is configurable from the ConnectorsScreen UI.
    is_test_run = not (len(sys.argv) < 2 or sys.argv[1] == "True")
    main(is_test_run)
