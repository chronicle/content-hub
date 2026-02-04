from __future__ import annotations

from soar_sdk.SiemplifyJob import SiemplifyJob
from soar_sdk.SiemplifyUtils import output_handler, utc_now

from ..core.constants import (
    CANCELED,
    CASE_RULE_GENERATOR,
    CLOSED,
    RESOLVED,
    STATES,
    STATES_NAMES,
    SYNC_CLOSURE,
)
from ..core.ServiceNowManager import ServiceNowManager, ServiceNowRecordNotFoundException
from ..core.UtilsManager import (
    get_case_and_alerts_ids,
    get_incidents_numbers_from_case,
    validate_timestamp,
)

# =====================================
#             CONSTANTS               #
# =====================================
OPEN_CASE_STATUS = "1"
CLOSE_CASE_STATUS = "2"
CLOSE_INCIDENT_REASON = "Closed By Google SecOps"
CLOSE_INCIDENT_CODE = "Resolved by caller"
NO_INCIDENTS_FOUND = "No Record found"

ROOT_CAUSE = "None"
CLOSE_ALERT_REASON = "Maintenance"
CLOSE_ALERT_COMMENT = "{} in ServiceNow"
DEFAULT_HOURS_BACKWARD = 24

INCIDENT_STATES_FOR_CLOSE_ALERT = [STATES[RESOLVED], STATES[CLOSED], STATES[CANCELED]]


def close_incidents_in_servicenow(siemplify, sn_manager, last_execution_time):
    """
    Close incidents in ServiceNow if they are closed in Siemplify
    :param siemplify: {SiemplifyJob} Instance of class SiemplifyJob
    :param sn_manager: {ServiceNowManager} Instance of class ServiceNowManager
    :param last_execution_time: {float} Last job execution time
    """
    siemplify.LOGGER.info("--- Start synchronize closure from Google SecOps to ServiceNow ---")

    last_execution_time_sn = sn_manager.convert_datetime_to_sn_format(last_execution_time)

    ticket_ids_for_closed_cases = siemplify.get_alerts_ticket_ids_from_cases_closed_since_timestamp(
        int(last_execution_time.timestamp() * 1000), None
    )

    siemplify.save_timestamp(new_timestamp=utc_now())

    closed_cases = []

    for ticket_id in ticket_ids_for_closed_cases:
        try:
            closed_cases.extend([
                siemplify._get_case_by_id(case_id)
                for case_id in siemplify.get_cases_by_ticket_id(ticket_id)
            ])
        except Exception as e:
            siemplify.LOGGER.error(f"Failed to fetch case with ticket id {ticket_id}. Reason {e}")

    siemplify.LOGGER.info(f"Found {len(closed_cases)} closed cases since {last_execution_time_sn}")

    incidents_numbers_to_close = [
        incident_number
        for case in closed_cases
        for incident_number in get_incidents_numbers_from_case(
            chronicle_soar=siemplify,
            case=case,
        )
    ]

    if not incidents_numbers_to_close:
        return

    try:
        incidents_to_close = sn_manager.get_incidents(
            numbers=incidents_numbers_to_close,
            states=INCIDENT_STATES_FOR_CLOSE_ALERT,
            state_match=False,
            fields=["sys_id", "state", "number"],
        )

        for incident in incidents_to_close:
            try:
                sn_manager.close_incident(
                    incident.number,
                    CLOSE_INCIDENT_REASON,
                    close_notes=CLOSE_INCIDENT_REASON,
                    close_code=CLOSE_INCIDENT_CODE,
                )
                siemplify.LOGGER.info(f"Incident {incident.number} closed in Service now")
            except Exception as e:
                siemplify.LOGGER.error(f"Failed to close incident {incident.number}. Reason: {e}")

    except Exception as e:
        siemplify.LOGGER.error(f"Failed to fetch incidents Reason: {e}")

    siemplify.LOGGER.info("--- Finish synchronize closure from Google SecOps to ServiceNow ---")


def close_cases_in_siemplify(siemplify, sn_manager):
    """
    Close cases in Siemplify if they are closed in ServiceNow
    :param siemplify: {SiemplifyJob} Instance of class SiemplifyJob
    :param sn_manager: {ServiceNowManager} Instance of class ServiceNowManager
    """
    siemplify.LOGGER.info("--- Start synchronize closure from ServiceNow to Google SecOps ---")
    fetched_open_cases_ids = siemplify.get_cases_by_filter(
        case_names=[CASE_RULE_GENERATOR],
        statuses=[OPEN_CASE_STATUS],
    )
    fetched_open_cases_ids.extend(
        siemplify.get_cases_by_filter(tags=["ServiceNow"], statuses=[OPEN_CASE_STATUS])
    )
    open_cases = [siemplify._get_case_by_id(case_id) for case_id in fetched_open_cases_ids]

    siemplify.LOGGER.info(f"Found {len(open_cases)} open cases")

    incident_number_open_case_map = {
        incident_number: case
        for case in open_cases
        for incident_number in get_incidents_numbers_from_case(
            chronicle_soar=siemplify,
            case=case,
        )
    }

    closed_incidents_in_sn = []
    closed_incidents_in_siemplify = []

    if incident_number_open_case_map:
        try:
            closed_incidents_in_sn = sn_manager.get_incidents(
                numbers=incident_number_open_case_map.keys(),
                states=INCIDENT_STATES_FOR_CLOSE_ALERT,
                state_match=True,
                fields=["sys_id", "state", "number"],
            )

            siemplify.LOGGER.info(
                f"Found {len(closed_incidents_in_sn)} closed incidents in Service now"
            )
        except ServiceNowRecordNotFoundException:
            siemplify.LOGGER.info("Not found incidents for opened cases")
        except Exception as e:
            siemplify.LOGGER.exception(e)
            siemplify.LOGGER.error(f"Failed to fetch incidents. Reason: {e}")

        for incident in closed_incidents_in_sn:
            case = incident_number_open_case_map[incident.number]
            for case_id, alert_ids in get_case_and_alerts_ids(case).items():
                for alert_id in alert_ids:
                    try:
                        siemplify.close_alert(
                            case_id=case_id,
                            alert_id=alert_id,
                            root_cause=ROOT_CAUSE,
                            reason=CLOSE_ALERT_REASON,
                            comment=CLOSE_ALERT_COMMENT.format(
                                STATES_NAMES.get(int(incident.state))
                            ),
                        )
                        closed_incidents_in_siemplify.append(incident.number)
                        siemplify.LOGGER.info(f"Alert for incident {incident.number} was closed")
                    except Exception as e:
                        siemplify.LOGGER.exception(e)
                        siemplify.LOGGER.error(
                            f"Failed to close alert for incident {incident.number} Reason: {e}."
                        )

    siemplify.LOGGER.info("--- Finish synchronize closure from ServiceNow to Google SecOps ---")


@output_handler
def main():
    siemplify = SiemplifyJob()

    try:
        siemplify.script_name = SYNC_CLOSURE

        siemplify.LOGGER.info("--------------- JOB STARTED ---------------")

        api_root = siemplify.extract_job_param(param_name="Api Root", is_mandatory=True)
        username = siemplify.extract_job_param(param_name="Username", is_mandatory=True)
        password = siemplify.extract_job_param(param_name="Password", is_mandatory=True)
        verify_ssl = siemplify.extract_job_param(
            param_name="Verify SSL", is_mandatory=True, input_type=bool
        )
        client_id = siemplify.extract_job_param(param_name="Client ID", is_mandatory=False)
        client_secret = siemplify.extract_job_param(param_name="Client Secret", is_mandatory=False)
        refresh_token = siemplify.extract_job_param(param_name="Refresh Token", is_mandatory=False)
        use_oauth = siemplify.extract_job_param(
            param_name="Use Oauth Authentication",
            default_value=False,
            input_type=bool,
            is_mandatory=False,
        )
        table_name = siemplify.extract_job_param(param_name="Table Name", is_mandatory=True)
        hours_backwards = siemplify.extract_job_param(
            param_name="Max Hours Backwards",
            is_mandatory=False,
            input_type=int,
            default_value=DEFAULT_HOURS_BACKWARD,
        )

        service_now_manager = ServiceNowManager(
            api_root=api_root,
            username=username,
            password=password,
            default_incident_table=table_name,
            verify_ssl=verify_ssl,
            siemplify_logger=siemplify.LOGGER,
            client_id=client_id,
            client_secret=client_secret,
            refresh_token=refresh_token,
            use_oauth=use_oauth,
        )

        last_successful_execution_time = validate_timestamp(
            siemplify.fetch_timestamp(datetime_format=True), hours_backwards
        )

        close_incidents_in_servicenow(
            siemplify, service_now_manager, last_successful_execution_time
        )
        close_cases_in_siemplify(siemplify, service_now_manager)

        siemplify.LOGGER.info("--------------- JOB FINISHED ---------------")
    except Exception as e:
        siemplify.LOGGER.error(f"Got exception on main handler.Error: {e}")
        siemplify.LOGGER.exception(e)


if __name__ == "__main__":
    main()
