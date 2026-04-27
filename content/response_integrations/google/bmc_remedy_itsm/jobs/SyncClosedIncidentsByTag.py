from __future__ import annotations
from soar_sdk.SiemplifyDataModel import (
    CaseFilterOperatorEnum,
    CaseFilterSortByEnum,
    CaseFilterSortOrderEnum,
    CaseFilterStatusEnum,
)
from soar_sdk.SiemplifyJob import SiemplifyJob
from soar_sdk.SiemplifyUtils import output_handler, unix_now

from TIPCommon.extraction import extract_action_param
from TIPCommon.rest.soar_api import get_full_case_details
from TIPCommon.types import SingleJson

from ..core.BMCRemedyITSMExceptions import (
    BMCRemedyITSMNotFoundException,
    BMCRemedyITSMJobException,
)
from ..core.BMCRemedyITSMManager import BMCRemedyITSMManager
from ..core.constants import (
    INTEGRATION_NAME,
    SYNC_CLOSURE_SCRIPT_NAME,
    BMC_REMEDY_ITSM_TAG,
    INCIDENTS_TAG,
    TAG_SEPARATOR,
    CANCELLED_STATUS,
    CLOSED_STATUS,
    RESOLVED_STATUS,
    REASON,
    ROOT_CAUSE,
    COMMENT,
    CASE_STATUS_OPEN,
    DEFAULT_HOURS_BACKWARDS,
    MIN_HOURS_BACKWARDS,
)
from ..core.UtilsManager import get_last_success_time, UNIX_FORMAT


@output_handler
def main():
    siemplify = SiemplifyJob()
    siemplify.script_name = SYNC_CLOSURE_SCRIPT_NAME
    siemplify.LOGGER.info("--------------- JOB STARTED ---------------")

    api_root = extract_action_param(
        siemplify=siemplify, param_name="API Root", is_mandatory=True, print_value=True
    )
    username = extract_action_param(
        siemplify=siemplify, param_name="Username", is_mandatory=True, print_value=True
    )
    password = extract_action_param(
        siemplify=siemplify, param_name="Password", is_mandatory=True, print_value=False
    )
    environment_ = extract_action_param(
        siemplify=siemplify,
        param_name="Environment",
        print_value=True,
    )
    environments = [environment_] if environment_ else []

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
    incident_table = extract_action_param(
        siemplify=siemplify,
        param_name="Incident Table",
        is_mandatory=True,
        print_value=True,
    )
    manager = None

    try:
        fetch_time_ms = get_last_success_time(
            siemplify,
            offset_with_metric={"hours": hours_backwards},
            time_format=UNIX_FORMAT,
        )

        if hours_backwards < MIN_HOURS_BACKWARDS:
            raise Exception(
                "\"Max Hours Backwards\" parameter must be greater or equal to "
                f"{MIN_HOURS_BACKWARDS}"
            )

        manager = BMCRemedyITSMManager(
            api_root=api_root,
            username=username,
            password=password,
            verify_ssl=verify_ssl,
            siemplify_logger=siemplify.LOGGER,
        )

        cases_id = siemplify.get_cases_ids_by_filter(
            environments=environments,
            tags=[BMC_REMEDY_ITSM_TAG],
            status=CaseFilterStatusEnum.CLOSE,
            start_time_from_unix_time_in_ms=fetch_time_ms,
            update_time_from_unix_time_in_ms=fetch_time_ms,
            operator=CaseFilterOperatorEnum.OR,
            sort_by=CaseFilterSortByEnum.UPDATE_TIME,
            sort_order=CaseFilterSortOrderEnum.ASC,
        )

        closed_cases = []
        open_cases = []

        for case_id in cases_id:
            case = get_full_case_details(siemplify, case_id)
            closed_cases.append(case)

        siemplify.LOGGER.info(
            f"Found {len(closed_cases)} closed cases with tag {BMC_REMEDY_ITSM_TAG} "
            "since last fetch time."
        )

        siemplify.LOGGER.info(f"--- Start Closing Incidents in {INTEGRATION_NAME} ---")

        for case in closed_cases:
            case_tags = [
                item.get("displayName", item.get("tag"))
                for item in case.get("tags", [])
                if INCIDENTS_TAG in item.get("displayName", item.get("tag"))
            ]
            request_ids = [tag.split(TAG_SEPARATOR)[1].strip() for tag in case_tags]
            if request_ids:
                request_id = request_ids[0]
                try:
                    incidents = manager.get_incident_details_by_table(
                        table_name=incident_table, incident_id=request_id
                    )
                    if incidents:
                        incident = incidents[0]
                        if incident.status in [
                            CLOSED_STATUS,
                            CANCELLED_STATUS,
                            RESOLVED_STATUS,
                        ]:
                            siemplify.LOGGER.info(
                                f"Incident - {request_id} status is {incident.status}. "
                                "Skipping..."
                            )
                        else:
                            manager.update_incident_by_table(
                                request_id=incident.request_id,
                                table_name=incident_table,
                            )
                            siemplify.LOGGER.info(
                                f"Incident - {request_id} status was updated to "
                                f"{CLOSED_STATUS}"
                            )
                    else:
                        siemplify.LOGGER.error(
                            "Job wasn't able to get details for the Incident with ID "
                            f"{request_id}. Reason: Incident wasn't "
                            f"found in {INTEGRATION_NAME}."
                        )
                except BMCRemedyITSMNotFoundException:
                    siemplify.LOGGER.error(
                        f"Job wasn't able to close the Incident with ID {request_id}. "
                        "Reason: Incident "
                        f"wasn't found in {INTEGRATION_NAME}."
                    )
                except BMCRemedyITSMJobException:
                    siemplify.LOGGER.error(
                        f"Job wasn\'t able to close the incident \"{request_id}\"."
                        " Reason: assignee or assignee group "
                        "wasn\'t provided in the incident. Please add them via "
                        "\"Update Incident\" actions."
                    )
                except Exception as e:
                    siemplify.LOGGER.error(
                        f"Failed to close the incident {request_id} in "
                        f"{INTEGRATION_NAME}."
                    )
                    siemplify.LOGGER.exception(e)

        siemplify.LOGGER.info(
            "--- Finished synchronizing closed cases from "
            f"Siemplify to {INTEGRATION_NAME} incidents ---"
        )

        cases_id = siemplify.get_cases_by_filter(
            environments=environments,
            tags=[BMC_REMEDY_ITSM_TAG],
            statuses=[CASE_STATUS_OPEN],
        )
        for case_id in cases_id:
            case = get_full_case_details(siemplify, case_id)
            open_cases.append(case)

        siemplify.LOGGER.info(
            f"Found {len(open_cases)} open cases with tag {BMC_REMEDY_ITSM_TAG}."
        )

        siemplify.LOGGER.info("--- Start Closing Alerts in Siemplify ---")

        for case in open_cases:
            case_tags = [
                item.get("displayName", item.get("tag"))
                for item in case.get("tags", [])
                if INCIDENTS_TAG in item.get("displayName", item.get("tag"))
            ]
            request_ids = [tag.split(TAG_SEPARATOR)[1].strip() for tag in case_tags]
            if request_ids:
                request_id = request_ids[0]
                try:
                    incidents = manager.get_incident_details_by_table(
                        table_name=incident_table, incident_id=request_id
                    )
                    if incidents:
                        incident = incidents[0]
                        if incident.status in [
                            CLOSED_STATUS,
                            CANCELLED_STATUS,
                            RESOLVED_STATUS,
                        ]:
                            close_alerts_for_case(
                                case=case,
                                incident_status=incident.status,
                                siemplify=siemplify,
                            )
                    else:
                        siemplify.LOGGER.error(
                            "Job wasn't able to get details for the Incident with ID "
                            f"{request_id}. Reason: Incident wasn't "
                            f"found in {INTEGRATION_NAME}."
                        )
                except BMCRemedyITSMNotFoundException:
                    siemplify.LOGGER.error(
                        "Job wasn't able to get details for the Incident with ID "
                        f"{request_id}. Reason: Incident wasn't "
                        f"found in {INTEGRATION_NAME}."
                    )
                except Exception as e:
                    siemplify.LOGGER.error(
                        f"Failed to get details for the incident {request_id} "
                        f"from {INTEGRATION_NAME}."
                    )
                    siemplify.LOGGER.exception(e)
        all_cases = sorted(
            closed_cases, key=lambda case: (
                case.get("modification_time_unix_time_in_ms", 1)
            )
        )
        new_timestamp = (
            all_cases[-1].get("modification_time_unix_time_in_ms", 1) + 1
            if all_cases
            else unix_now()
        )
        siemplify.save_timestamp(new_timestamp=new_timestamp)
        siemplify.LOGGER.info(
            f" --- Finish synchronize closed incidents from {INTEGRATION_NAME} "
            "to Siemplify cases --- "
        )
        siemplify.LOGGER.info("--------------- JOB FINISHED ---------------")

    except Exception as error:
        siemplify.LOGGER.error(f"Got exception on main handler. Error: {error}")
        siemplify.LOGGER.exception(error)
        raise

    finally:
        try:
            if manager:
                siemplify.LOGGER.info(f"Logging out from {INTEGRATION_NAME}..")
                manager.logout()
                siemplify.LOGGER.info(
                    f"Successfully logged out from {INTEGRATION_NAME}"
                )
        except Exception as error:
            siemplify.LOGGER.error(f"Logging out failed. Error: {error}")
            siemplify.LOGGER.exception(error)


def close_alerts_for_case(
    case: SingleJson,
    incident_status: str,
    siemplify: SiemplifyJob,
) -> None:
    """Close alerts for the given case.

    Args:
        case(SingleJson): The case to close alerts for.
        incident_status(str): The status of the incident in BMC Remedy ITSM.
        siemplify(SiemplifyJob): The SiemplifyJob object.
    """
    case_id = case.get("id")
    for item in case.get("tags", case.get("alerts", [])):
        alert_id = item.get("alert", item.get("identifier", ""))
        if not alert_id:
            continue

        try:
            siemplify.close_alert(
                root_cause=ROOT_CAUSE,
                reason=REASON,
                comment=COMMENT.format(status=incident_status),
                case_id=case_id,
                alert_id=alert_id,
            )
            siemplify.LOGGER.info(f"Alert {alert_id} was closed")
        except BMCRemedyITSMJobException as error:
            siemplify.LOGGER.error(
                f"Failed to close alert {alert_id} of case {case_id}"
            )
            siemplify.LOGGER.exception(error)


if __name__ == "__main__":
    main()
