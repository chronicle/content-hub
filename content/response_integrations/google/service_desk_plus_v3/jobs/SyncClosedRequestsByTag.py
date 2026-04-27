from __future__ import annotations
from soar_sdk.SiemplifyJob import SiemplifyJob
from soar_sdk.SiemplifyUtils import output_handler, convert_datetime_to_unix_time, unix_now

from TIPCommon.extraction import extract_action_param
from TIPCommon.rest.soar_api import get_full_case_details
from TIPCommon.types import SingleJson

from ..core.constants import (
    INTEGRATION_NAME,
    SYNC_CLOSURE_SCRIPT_NAME,
    SERVICE_DESK_PLUS_TAG,
    REQUESTS_TAG,
    TAG_SEPARATOR,
    CANCELLED_STATUS,
    CLOSED_STATUS,
    RESOLVED_STATUS,
    REASON,
    ROOT_CAUSE,
    COMMENT,
    CASE_STATUS_CLOSED,
    CASE_STATUS_OPEN,
    DEFAULT_HOURS_BACKWARDS,
    MIN_HOURS_BACKWARDS,
)
from ..core.ServiceDeskPlusManagerV3 import ServiceDeskPlusManagerV3
from ..core.ServiceDeskPlusV3Exceptions import (
    NoteNotFoundException,
    ServiceDeskPlusV3Exception,
)
from ..core.utils import get_last_success_time


@output_handler
def main():
    siemplify = SiemplifyJob()
    siemplify.script_name = SYNC_CLOSURE_SCRIPT_NAME
    siemplify.LOGGER.info("--------------- JOB STARTED ---------------")

    api_root = extract_action_param(
        siemplify=siemplify, param_name="Api Root", is_mandatory=True, print_value=True
    )
    api_key = extract_action_param(
        siemplify=siemplify, param_name="Api Key", is_mandatory=True, print_value=False
    )
    hours_backwards = extract_action_param(
        siemplify=siemplify,
        param_name="Max Hours Backwards",
        input_type=int,
        print_value=True,
        default_value=DEFAULT_HOURS_BACKWARDS,
    )
    verify_ssl = extract_action_param(
        siemplify=siemplify,
        param_name="Verify SSL",
        default_value=True,
        input_type=bool,
        print_value=True,
    )

    try:
        fetch_time = get_last_success_time(
            siemplify, offset_with_metric={"hours": hours_backwards}, print_value=False
        )
        fetch_time_ms = convert_datetime_to_unix_time(fetch_time)
        siemplify.LOGGER.info(
            f"Last fetch time. Date time:{fetch_time}. Unix:{fetch_time_ms}"
        )
        new_timestamp = unix_now()

        if hours_backwards < MIN_HOURS_BACKWARDS:
            raise Exception(
                '"Max Hours Backwards" parameter must be greater or equal to '
                f"{MIN_HOURS_BACKWARDS}"
            )

        servicedesk_manager = ServiceDeskPlusManagerV3(
            api_root=api_root, api_key=api_key, verify_ssl=verify_ssl
        )

        cases_id = siemplify.get_cases_by_filter(
            tags=[SERVICE_DESK_PLUS_TAG],
            statuses=[CASE_STATUS_CLOSED],
            start_time_unix_time_in_ms=fetch_time_ms,
        )

        closed_cases = []
        open_cases = []

        for case_id in cases_id:
            case = get_full_case_details(siemplify, case_id)
            closed_cases.append(case)

        siemplify.LOGGER.info(
            f"Found {len(closed_cases)} closed cases with tag "
            f"{SERVICE_DESK_PLUS_TAG} since last fetch time."
        )

        siemplify.LOGGER.info("--- Start Closing Requests in ServiceDeskPlus ---")

        for case in closed_cases:
            case_tags = [
                item.get("displayName", item.get("tag"))
                for item in case.get("tags", [])
                if REQUESTS_TAG in item.get("displayName", item.get("tag"))
            ]
            request_ids = [tag.split(TAG_SEPARATOR)[1].strip() for tag in case_tags]
            request_id = next(
                (id for id in request_ids if is_valid_request_id(siemplify, id)), None
            )
            if request_id:
                try:
                    servicedesk_manager.update_request_status(request_id, CLOSED_STATUS)
                    siemplify.LOGGER.info(
                        f"ServiceDeskPlus request - {request_id} status was updated"
                        f" to {CLOSED_STATUS}"
                    )
                except NoteNotFoundException:
                    siemplify.LOGGER.error(
                        f"Job wasn't able to close the Request with ID {request_id}. "
                        f"Reason: Request wasn't found in {INTEGRATION_NAME}."
                    )
                except Exception as e:
                    siemplify.LOGGER.error(
                        "Failed to close the request "
                        f"{request_id} in {INTEGRATION_NAME}."
                    )
                    siemplify.LOGGER.exception(e)

        siemplify.LOGGER.info(
            "--- Finished synchronizing closed cases from Siemplify "
            "to ServiceDeskPlus requests ---"
        )

        cases_id = siemplify.get_cases_by_filter(
            tags=[SERVICE_DESK_PLUS_TAG], statuses=[CASE_STATUS_OPEN]
        )
        for case_id in cases_id:
            case = get_full_case_details(siemplify, case_id)
            open_cases.append(case)

        siemplify.LOGGER.info(
            f"Found {len(open_cases)} open cases with tag {SERVICE_DESK_PLUS_TAG}."
        )

        siemplify.LOGGER.info("--- Start Closing Alerts in Siemplify ---")

        for case in open_cases:
            case_tags = [
                item.get("displayName", item.get("tag"))
                for item in case.get("tags", [])
                if REQUESTS_TAG in item.get("displayName", item.get("tag"))
            ]
            request_ids = [tag.split(TAG_SEPARATOR)[1].strip() for tag in case_tags]
            request_id = next(
                (id for id in request_ids if is_valid_request_id(siemplify, id)), None
            )
            if request_id:
                try:
                    request = servicedesk_manager.get_request(request_id)
                    if request:
                        if request.status in [
                            CLOSED_STATUS,
                            CANCELLED_STATUS,
                            RESOLVED_STATUS,
                        ]:
                            close_alerts_for_case(
                                siemplify=siemplify,
                                case=case,
                                request_status=request.status,
                            )
                except NoteNotFoundException:
                    siemplify.LOGGER.error(
                        "Job wasn't able to get details for the Request with "
                        f"ID {request_id}. Reason: Request wasn't "
                        f"found in {INTEGRATION_NAME}."
                    )
                except Exception as e:
                    siemplify.LOGGER.error(
                        f"Failed to get details for the request {request_id} "
                        f"from {INTEGRATION_NAME}."
                    )
                    siemplify.LOGGER.exception(e)

        siemplify.save_timestamp(new_timestamp=new_timestamp)
        siemplify.LOGGER.info(
            " --- Finish synchronize closed requests from ServiceDeskPlus to Siemplify cases --- "
        )
        siemplify.LOGGER.info("--------------- JOB FINISHED ---------------")

    except Exception as error:
        siemplify.LOGGER.error(f"Got exception on main handler. Error: {error}")
        siemplify.LOGGER.exception(error)
        raise


def close_alerts_for_case(
    siemplify: SiemplifyJob,
    case: SingleJson,
    request_status: str,
) -> None:
    """Close alerts for case.

    Args:
        siemplify(SiemplifyJob): The SiemplifyJob object.
        case(SingleJson): The case object.
        request_status(str): The status of the request.
    """
    case_id = case.get("id")
    for item in case.get("tags", case.get("alerts", [])):
        alert_id = item.get("alert", item.get("identifier", ""))
        if alert_id:
            try:
                siemplify.close_alert(
                    root_cause=ROOT_CAUSE,
                    reason=REASON,
                    comment=COMMENT.format(status=request_status),
                    case_id=case_id,
                    alert_id=alert_id,
                )
                siemplify.LOGGER.info(f"Alert {alert_id} was closed")

            except ServiceDeskPlusV3Exception as error:
                siemplify.LOGGER.error(
                    f"Failed to close alert {alert_id} of " f"case {case_id}"
                )
                siemplify.LOGGER.exception(error)


def is_valid_request_id(siemplify, request_id):
    try:
        request_id = int(request_id)
    except Exception:
        siemplify.LOGGER.error(f"Request id: {request_id} is in invalid format.")
        return False

    if request_id < 1:
        siemplify.LOGGER.error(f"Request id should be a positive number.")
        return False
    return True


if __name__ == "__main__":
    main()
