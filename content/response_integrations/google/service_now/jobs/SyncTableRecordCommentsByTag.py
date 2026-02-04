from __future__ import annotations

from soar_sdk.SiemplifyJob import SiemplifyJob
from soar_sdk.SiemplifyUtils import output_handler
from TIPCommon.extraction import extract_action_param
from TIPCommon.rest.soar_api import get_full_case_details

from ..core.constants import (
    CASE_STATUS_OPEN,
    RECORDS_TAG,
    SERVICE_NOW_TAG,
    SIEMPLIFY_COMMENT_PREFIX,
    SN_COMMENT_PREFIX,
    SYNC_COMMENTS_BY_TAG,
    TAG_SEPARATOR,
)
from ..core.ServiceNowManager import ServiceNowManager, ServiceNowRecordNotFoundException


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
    siemplify.script_name = SYNC_COMMENTS_BY_TAG
    siemplify.LOGGER.info("--------------- JOB STARTED ---------------")

    api_root = extract_action_param(
        siemplify=siemplify, param_name="API Root", is_mandatory=True, print_value=True
    )
    username = extract_action_param(
        siemplify=siemplify, param_name="Username", is_mandatory=True, print_value=True
    )
    password = extract_action_param(siemplify=siemplify, param_name="Password", is_mandatory=True)
    verify_ssl = extract_action_param(
        siemplify=siemplify,
        param_name="Verify SSL",
        is_mandatory=True,
        default_value=True,
        input_type=bool,
        print_value=True,
    )
    table_name = extract_action_param(
        siemplify=siemplify,
        param_name="Table Name",
        is_mandatory=True,
        print_value=True,
    )

    try:
        service_now_manager = ServiceNowManager(
            api_root=api_root,
            username=username,
            password=password,
            default_incident_table=table_name,
            verify_ssl=verify_ssl,
            siemplify_logger=siemplify.LOGGER,
        )

        cases_id = siemplify.get_cases_by_filter(
            tags=[SERVICE_NOW_TAG.format(table_name=table_name)],
            statuses=[CASE_STATUS_OPEN],
        )

        open_cases = {
            str(case_id): get_full_case_details(siemplify, case_id) for case_id in cases_id
        }

        siemplify.LOGGER.info(
            f"Found {len(open_cases)} open cases with tag {SERVICE_NOW_TAG.format(table_name=table_name)}."
        )

        siemplify.LOGGER.info("--- Start synchronize comments ServiceNow <-> Siemplify ---")

        for case_id, case in open_cases.items():
            siemplify.LOGGER.info(f"Started processing case: {case_id}")
            case_tags = [
                item.get("tag") or item.get("displayName")
                for item in case.get("tags", [])
                if RECORDS_TAG in (item.get("tag") or item.get("displayName"))
            ]
            record_ids = [tag.split(TAG_SEPARATOR)[1].strip() for tag in case_tags]
            if record_ids:
                record_id = record_ids[0]
                try:
                    ticket_sys_id = service_now_manager.get_ticket_id(
                        ticket_number=record_id, table_name=table_name
                    )
                    ticket_comments = service_now_manager.get_ticket_comments(
                        [ticket_sys_id],
                        fields=["element_id", "value"],
                        table_name=table_name,
                    )
                    case_comments = siemplify.get_case_comments(case_id)
                    raw_case_comments = comments_mapper(case_comments)
                    raw_sn_comments = comments_mapper(ticket_comments)
                    new_comments_from_case, new_comments_from_sn = get_new_comments_to_add(
                        raw_case_comments, raw_sn_comments
                    )
                    if not new_comments_from_case and not new_comments_from_sn:
                        continue

                    # Sync ServiceNow with Siemplify
                    if new_comments_from_case:
                        siemplify.LOGGER.info(
                            f"Found {len(new_comments_from_case)} comments to add in ServiceNow."
                        )

                    for si_comment in new_comments_from_case:
                        try:
                            comment_with_prefix = f"{SIEMPLIFY_COMMENT_PREFIX}{si_comment}"
                            service_now_manager.add_work_note_to_incident(
                                record_id, comment_with_prefix, table_name
                            )
                            siemplify.LOGGER.info(f"Added comment to ticket {record_id}")
                        except ServiceNowRecordNotFoundException as e:
                            siemplify.LOGGER.error(e)
                        except Exception as e:
                            siemplify.LOGGER.error(
                                f"Failed to add comment to ticket {record_id}, Reason: {e}"
                            )
                            siemplify.LOGGER.exception(e)

                    # Sync Siemplify with ServiceNow
                    if new_comments_from_sn:
                        siemplify.LOGGER.info(
                            f"Found {len(new_comments_from_sn)} comments to add in Siemplify."
                        )

                    for sn_comment in new_comments_from_sn:
                        try:
                            comment_with_prefix = f"{SN_COMMENT_PREFIX}{sn_comment}"
                            siemplify.add_comment(comment_with_prefix, case_id, None)
                            siemplify.LOGGER.info(f"Added comment to case with id: {case_id}")
                        except Exception as e:
                            siemplify.LOGGER.error(
                                f"Failed to add comment to case {case_id}, Reason: {e}"
                            )
                            siemplify.LOGGER.exception(e)

                except Exception as e:
                    siemplify.LOGGER.error(
                        f"Error processing case with id {case_id}. Ticket ID: {record_id}."
                    )
                    siemplify.LOGGER.exception(e)

            siemplify.LOGGER.info(f"Finished processing case: {case_id}")

        siemplify.LOGGER.info("--- Finish synchronize comments ServiceNow <-> Siemplify ---")
        siemplify.LOGGER.info("--------------- JOB FINISHED ---------------")

    except Exception as error:
        siemplify.LOGGER.error(f"Got exception on main handler. Error: {error}")
        siemplify.LOGGER.exception(error)
        raise


if __name__ == "__main__":
    main()
