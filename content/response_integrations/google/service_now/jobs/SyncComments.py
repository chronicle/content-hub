from __future__ import annotations

from soar_sdk.SiemplifyJob import SiemplifyJob
from soar_sdk.SiemplifyUtils import convert_unixtime_to_datetime, output_handler, utc_now

from ..core.constants import CASE_RULE_GENERATOR, INTEGRATION_NAME, SYNC_COMMENTS
from ..core.ServiceNowManager import ServiceNowManager, ServiceNowRecordNotFoundException
from ..core.UtilsManager import get_incidents_numbers_from_case, validate_timestamp

# =====================================
#             CONSTANTS               #
# =====================================
OPEN_CASE_STATUS = "1"
CLOSE_CASE_STATUS = "2"
SIEMPLIFY_COMMENT_PREFIX = "Google SecOps: "
SN_COMMENT_PREFIX = f"{INTEGRATION_NAME}: "


def get_comment_body(comment):
    """
    Get comment body
    :param comment: {Comment or dict}
    :return: {str} pure comment body
    """
    if isinstance(comment, dict):
        return clean_prefix(comment.get("comment"))

    return clean_prefix(comment.value)


def clean_prefix(comment_body):
    """
    Clean comment prefixes
    :param comment_body: {str} comment with prefix
    :return: {str}
    """
    if comment_body.startswith(SIEMPLIFY_COMMENT_PREFIX):
        clean_body = comment_body.split(SIEMPLIFY_COMMENT_PREFIX, 1)
    elif comment_body.startswith(SN_COMMENT_PREFIX):
        clean_body = comment_body.split(SN_COMMENT_PREFIX, 1)
    else:
        clean_body = comment_body

    return "".join(clean_body)


def get_new_comments_to_add(case_comments, sn_comments):
    """
    Extract new comments from Servicenow and Siemplify
    :param case_comments: {list} List of Siemplify comments
    :param sn_comments: {sn_comments} List of Servicenow comments
    :return: {tuple} Of comments from case and comments from servicenow
    """
    new_comments_from_sn = sn_comments.copy()
    new_comments_from_case = case_comments.copy()

    for case_comment in case_comments:
        if case_comment in new_comments_from_sn:
            new_comments_from_sn.remove(case_comment)

    for sn_comment in sn_comments:
        if sn_comment in new_comments_from_case:
            new_comments_from_case.remove(sn_comment)

    return new_comments_from_case, new_comments_from_sn


def comments_mapper(comments):
    """
    Map comments bodies
    :param comments {list} List of comments
    """
    return [get_comment_body(comment) for comment in comments]


@output_handler
def main():
    siemplify = SiemplifyJob()

    try:
        siemplify.script_name = SYNC_COMMENTS

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
            siemplify.fetch_timestamp(datetime_format=True)
        )
        siemplify.LOGGER.info(
            f"Last successful execution run: {str(last_successful_execution_time)}"
        )

        new_timestamp = utc_now()

        opened_cases_ids = siemplify.get_cases_by_filter(
            case_names=[CASE_RULE_GENERATOR], statuses=[OPEN_CASE_STATUS]
        )

        open_cases = {
            str(case_id): siemplify._get_case_by_id(case_id) for case_id in opened_cases_ids
        }
        # ticket case by number layer
        ticket_case_id_by_number = {
            number: case.get("identifier")
            for case in open_cases.values()
            for number in get_incidents_numbers_from_case(case)
        }
        ticket_number_by_case_id = {
            case_id: number for number, case_id in ticket_case_id_by_number.items()
        }

        tickets = []

        for ticket_id in ticket_case_id_by_number.keys():
            try:
                tickets.extend(
                    service_now_manager.get_incidents_with_pagination(
                        numbers=[ticket_id], fields=["sys_id", "number"]
                    )
                )
            except ServiceNowRecordNotFoundException as e:
                siemplify.LOGGER.error(f"Failed to fetch incident with id {ticket_id}")
                siemplify.LOGGER.exception(e)

        ticket_number_by_sys_id = {ticket.sys_id: ticket.number for ticket in tickets}

        sn_comments = []
        for ticket_sys_id, number in ticket_number_by_sys_id.items():
            try:
                sn_comments.extend(
                    service_now_manager.get_ticket_comments(
                        [ticket_sys_id],
                        fields=["element_id", "value", "sys_created_on"],
                        order_by="sys_created_on",
                    )
                )
            except ServiceNowRecordNotFoundException as e:
                siemplify.LOGGER.error(f"Failed to fetch comment for incident with number {number}")
                siemplify.LOGGER.exception(e)

        cases_comments = []

        for case_id, case in open_cases.items():
            try:
                cases_comments.extend(siemplify.get_case_comments(case_id))
            except Exception as e:
                siemplify.LOGGER.exception(e)

        siemplify_comments = {}

        for case_comment in cases_comments:
            case_id = str(case_comment.get("case_id"))

            if not siemplify_comments.get(case_id):
                siemplify_comments[case_id] = []

            siemplify_comments[case_id].append(case_comment)

        # sort by creation_time_unix_time_in_ms
        for case_comment in cases_comments:
            case_id = str(case_comment.get("case_id"))
            siemplify_comments.get(case_id, []).sort(
                key=lambda comment: convert_unixtime_to_datetime(
                    comment.get("creation_time_unix_time_in_ms", 0)
                )
            )

        servicenow_comments = {}

        for sn_comment in sn_comments:
            sn_comment.number = ticket_number_by_sys_id.get(sn_comment.element_id)
            case_id = ticket_case_id_by_number.get(sn_comment.number, {})

            if not case_id:
                continue

            case_id = str(case_id)

            if not servicenow_comments.get(case_id):
                servicenow_comments[case_id] = []

            servicenow_comments[case_id].append(sn_comment)

        for case_id in open_cases:
            raw_case_comments = comments_mapper(siemplify_comments.get(case_id, []))
            raw_sn_comments = comments_mapper(servicenow_comments.get(case_id, []))
            ticket_number = ticket_number_by_case_id.get(case_id)
            new_comments_from_case, new_comments_from_sn = get_new_comments_to_add(
                raw_case_comments, raw_sn_comments
            )

            if not new_comments_from_case and not new_comments_from_sn:
                continue

            siemplify.LOGGER.info("--- Start synchronize comments ServiceNow <-> Google SecOps ---")

            siemplify.LOGGER.info(f"Run on case with id {case_id}")

            # Sync ServiceNow with Siemplify
            if new_comments_from_case:
                siemplify.LOGGER.info(
                    f"Found {len(new_comments_from_case)} comments to add ServiceNow."
                )

            for si_comment in new_comments_from_case:
                try:
                    comment_with_prefix = f"{SIEMPLIFY_COMMENT_PREFIX}{si_comment}"
                    service_now_manager.add_comment_to_incident(ticket_number, comment_with_prefix)
                    siemplify.LOGGER.info(f"Added comment to ticket {ticket_number}")
                except ServiceNowRecordNotFoundException as e:
                    siemplify.LOGGER.error(e)
                except Exception as e:
                    siemplify.LOGGER.error(
                        f"Failed to add comment to ticket {ticket_number}, Reason: {e}"
                    )
                    siemplify.LOGGER.exception(e)

            # Sync Siemplify with ServiceNow
            if new_comments_from_sn:
                siemplify.LOGGER.info(
                    f"Found {len(new_comments_from_sn)} comments to add Google SecOps."
                )

            for sn_comment in new_comments_from_sn:
                try:
                    comment_with_prefix = f"{SN_COMMENT_PREFIX}{sn_comment}"
                    siemplify.add_comment(comment_with_prefix, case_id, None)
                    siemplify.LOGGER.info(f"Added comments to case with id: {case_id}")
                except Exception as e:
                    siemplify.LOGGER.error(f"Failed to add comment to case {case_id}, Reason: {e}")
                    siemplify.LOGGER.exception(e)

            siemplify.LOGGER.info(
                "--- Finish synchronize comments ServiceNow <-> Google SecOps ---"
            )

        siemplify.LOGGER.info("Update Job last execution timestamp")
        siemplify.save_timestamp(new_timestamp=new_timestamp)
        siemplify.LOGGER.info("--------------- JOB FINISHED ---------------")

    except Exception as e:
        siemplify.LOGGER.error(f"Got exception on main handler.Error: {e}")
        siemplify.LOGGER.exception(e)


if __name__ == "__main__":
    main()
