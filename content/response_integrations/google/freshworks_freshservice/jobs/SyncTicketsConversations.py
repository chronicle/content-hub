from __future__ import annotations
import datetime
from TIPCommon import extract_action_param

from ..core.FreshworksFreshserviceManager import FreshworksFreshserviceManager
from soar_sdk.SiemplifyJob import SiemplifyJob
from soar_sdk.SiemplifyUtils import output_handler, convert_datetime_to_unix_time
from ..core.consts import (
    TICKETS_SYNC_CONVERSATIONS_JOB_NAME,
    INTEGRATION_DISPLAY_NAME,
    DEFAULT_TIME_FRAME,
    PARAMETERS_DEFAULT_DELIMITER,
    SIEMPLIFY_COMMENT_PREFIX,
    FRESHSERVICE_COMMENT_PREFIX,
    CONVERSATION_TYPES,
    COMMENT_PRIVATE_NOTE,
    COMMENT_PUBLIC_NOTE,
    COMMENT_REPLY,
    SYNC_SIEMPLIFY_COMMENTS_AS_TYPES,
    CASE_STATUS_OPEN,
    DEVICE_PRODUCT,
    DATE_FORMAT,
    NOTE,
    NOTES,
    REPLIES,
    CONVERSATION_SOURCE_EMAIL,
    FORM,
    STATUS,
    META,
    FEEDBACK,
    FORWARD_EMAIL,
    FRESHSERVICE_TAG,
)
from ..core.exceptions import FreshworksFreshserviceTicketsConversationsJobError
from ..core.utils import (
    validate_timestamp,
    load_csv_to_list,
    is_siemplify_alert_matches_freshservice_ticket,
)


@output_handler
def main():
    siemplify = SiemplifyJob()
    siemplify.script_name = TICKETS_SYNC_CONVERSATIONS_JOB_NAME
    siemplify.LOGGER.info("=================== JOB STARTED ===================")

    api_root = extract_action_param(
        siemplify, param_name="API Root", is_mandatory=True, print_value=True
    )
    api_key = extract_action_param(
        siemplify,
        param_name="API Key",
        is_mandatory=True,
        print_value=False,
        remove_whitespaces=False,
    )
    verify_ssl = extract_action_param(
        siemplify,
        param_name="Verify SSL",
        input_type=bool,
        is_mandatory=False,
        default_value=True,
        print_value=True,
    )

    try:
        hours_backwards = extract_action_param(
            siemplify,
            param_name="Offset time in hours",
            default_value=DEFAULT_TIME_FRAME,
            input_type=int,
            is_mandatory=True,
            print_value=True,
        )
        siemplify_comment_prefix = extract_action_param(
            siemplify,
            param_name="Siemplify Comment Prefix",
            default_value=SIEMPLIFY_COMMENT_PREFIX,
            is_mandatory=True,
            print_value=True,
        )
        freshservice_comment_prefix = extract_action_param(
            siemplify,
            param_name="Freshservice Comment Prefix",
            default_value=FRESHSERVICE_COMMENT_PREFIX,
            is_mandatory=True,
            print_value=True,
        )
        conversation_types = extract_action_param(
            siemplify,
            param_name="Conversation Types To Sync",
            default_value=PARAMETERS_DEFAULT_DELIMITER.join(CONVERSATION_TYPES),
            is_mandatory=True,
            print_value=True,
        )
        fetch_private_notes = extract_action_param(
            siemplify,
            param_name="Fetch Private Notes?",
            default_value=False,
            input_type=bool,
            is_mandatory=False,
            print_value=True,
        )
        sync_siemplify_comments_as = extract_action_param(
            siemplify,
            param_name="Sync Comment from Siemplify as X",
            default_value=COMMENT_PRIVATE_NOTE,
            is_mandatory=True,
            print_value=True,
        )

        if hours_backwards < 0:
            raise FreshworksFreshserviceTicketsConversationsJobError(
                '"Offset time in hours" must be non-negative.'
            )

        conversation_types = load_csv_to_list(
            conversation_types, "Conversation Types To Sync"
        )
        invalid_conversation_types = [
            type for type in conversation_types if type not in CONVERSATION_TYPES
        ]
        if invalid_conversation_types:
            raise FreshworksFreshserviceTicketsConversationsJobError(
                "Following values are invalid"
                " for the 'Conversation Types To Sync' parameter: "
                f"{PARAMETERS_DEFAULT_DELIMITER.join(invalid_conversation_types)}."
                " Possible values are: "
                f"{PARAMETERS_DEFAULT_DELIMITER.join(CONVERSATION_TYPES)}"
            )

        if sync_siemplify_comments_as not in SYNC_SIEMPLIFY_COMMENTS_AS_TYPES:
            raise FreshworksFreshserviceTicketsConversationsJobError(
                f"Following values are invalid "
                " for the 'Sync Comment from Siemplify as X' parameter: "
                f"{sync_siemplify_comments_as}. Possible values are: "
                f"{PARAMETERS_DEFAULT_DELIMITER.join(SYNC_SIEMPLIFY_COMMENTS_AS_TYPES)}"
            )

        # Get last Successful execution time.
        last_successful_execution_time = validate_timestamp(
            siemplify.fetch_timestamp(datetime_format=True), hours_backwards
        )
        last_successful_execution_time_unix = convert_datetime_to_unix_time(
            last_successful_execution_time
        )
        siemplify.LOGGER.info(
            f"Last successful execution run: {last_successful_execution_time}"
        )

        manager = FreshworksFreshserviceManager(
            api_root=api_root,
            api_key=api_key,
            verify_ssl=verify_ssl,
            siemplify=siemplify,
        )
        siemplify.LOGGER.info(
            " --- Start synchronizing Case Comments from Siemplify to"
            f" {INTEGRATION_DISPLAY_NAME} --- "
        )

        fetched_open_cases_ids = siemplify.get_cases_by_filter(
            statuses=[CASE_STATUS_OPEN], tags=[FRESHSERVICE_TAG]
        )
        for case_id in fetched_open_cases_ids:
            case = siemplify._get_case_by_id(case_id)
            for alert in case.get("cyber_alerts", []):
                ticket_id = alert.get("additional_properties", {}).get("TicketId")
                device_product = alert.get("additional_properties", {}).get(
                    "DeviceProduct"
                )
                if device_product == DEVICE_PRODUCT:
                    case_comments = siemplify.get_case_comments(case_id)
                    for comment in case_comments:
                        comment_time = comment.get(
                            "modification_time_unix_time_in_ms", -1
                        )
                        comment_text = comment.get("comment") or ""
                        # Check that the comment is newer than the JOB timestamp
                        if (
                            comment_time > last_successful_execution_time_unix
                            and comment_text
                            and freshservice_comment_prefix not in comment_text
                        ):
                            siemplify.LOGGER.info(f"Found Case {case_id} new comment")
                            try:
                                freshservice_comment_with_prefix = (
                                    f"{siemplify_comment_prefix} {comment_text}"
                                )
                                if sync_siemplify_comments_as == COMMENT_REPLY:
                                    siemplify.LOGGER.info(
                                        f"Adding ticket reply to ticket {ticket_id}"
                                    )
                                    manager.add_ticket_reply(
                                        ticket_id=ticket_id,
                                        reply_text=freshservice_comment_with_prefix,
                                    )
                                elif sync_siemplify_comments_as == COMMENT_PRIVATE_NOTE:
                                    siemplify.LOGGER.info(
                                        f"Adding private note to ticket {ticket_id}"
                                    )
                                    manager.add_ticket_note(
                                        ticket_id=ticket_id,
                                        is_private=True,
                                        note_text=freshservice_comment_with_prefix,
                                    )
                                elif sync_siemplify_comments_as == COMMENT_PUBLIC_NOTE:
                                    siemplify.LOGGER.info(
                                        f"Adding public note to ticket {ticket_id}"
                                    )
                                    manager.add_ticket_note(
                                        ticket_id=ticket_id,
                                        is_private=False,
                                        note_text=freshservice_comment_with_prefix,
                                    )
                            except Exception as error:
                                siemplify.LOGGER.error(
                                    f"Failed to add comment to ticket {ticket_id}. "
                                    f"Reason: {error}"
                                )
                                siemplify.LOGGER.exception(error)

        siemplify.LOGGER.info(
            " --- Finish synchronize comments from Siemplify cases to"
            f" {INTEGRATION_DISPLAY_NAME} tickets --- "
        )
        siemplify.LOGGER.info(
            " --- Start synchronize Tickets Conversations "
            f"from {INTEGRATION_DISPLAY_NAME} to Siemplify --- "
        )

        updated_tickets = manager.get_filtered_tickets(
            updated_since=datetime.datetime.strftime(
                last_successful_execution_time, DATE_FORMAT
            ),
            include_requester=False,
            include_stats=False,
        )
        siemplify.LOGGER.info(
            f"Fetched {len(updated_tickets)} updated tickets to sync"
        )

        for ticket in updated_tickets:
            try:
                ticket_conversations = manager.get_ticket_conversations(
                    ticket_id=ticket.id
                )
                if ticket_conversations:
                    new_conversations = [
                        conversation
                        for conversation in ticket_conversations
                        if conversation.updated_at_unix
                        > last_successful_execution_time_unix
                        and siemplify_comment_prefix not in conversation.body_text
                    ]
                    # Fetch only public notes if "Fetch Private Notes?" parameter is unchecked
                    if not fetch_private_notes:
                        new_conversations = [
                            conversation
                            for conversation in new_conversations
                            if not conversation.private
                        ]

                    # Filter conversation types
                    if conversation_types:
                        conversation_sources = []
                        if NOTES in conversation_types:
                            conversation_sources.append(NOTE)
                        if REPLIES in conversation_types:
                            conversation_sources.extend(
                                [
                                    CONVERSATION_SOURCE_EMAIL,
                                    FORM,
                                    STATUS,
                                    META,
                                    FEEDBACK,
                                    FORWARD_EMAIL,
                                ]
                            )
                        new_conversations = [
                            conversation
                            for conversation in new_conversations
                            if conversation.source_name in conversation_sources
                        ]

                    if new_conversations:
                        # Fetch Case ids to update
                        siemplify.LOGGER.info(
                            f"Found {len(new_conversations)} new ticket conversations"
                            f" to sync in Siemplify for ticket: {ticket.id}"
                        )
                        # Search matching Siemplify Case
                        related_cases = siemplify.get_cases_by_filter(
                            ticked_ids_free_search=ticket.id,
                            tags=[FRESHSERVICE_TAG],
                            statuses=[CASE_STATUS_OPEN],
                        )
                        for case_id in related_cases:
                            case_data = siemplify._get_case_by_id(case_id)
                            case_matched = any(
                                    alert
                                    for alert in case_data.get("cyber_alerts", [])
                                    if is_siemplify_alert_matches_freshservice_ticket(
                                        alert, str(ticket.id), DEVICE_PRODUCT
                                    )
                            )
                            if case_matched:
                                # Add Case comments
                                case_comments = [
                                    comment.get("comment")
                                    for comment in siemplify.get_case_comments(case_id)
                                ]
                                for conversation in new_conversations:
                                    case_comment_with_prefix = (
                                        f"{freshservice_comment_prefix} "
                                        f"{conversation.body_text}"
                                    )
                                    if case_comment_with_prefix not in case_comments:
                                        try:
                                            siemplify.LOGGER.info(
                                                "Adding conversation with id "
                                                f"#{conversation.conversation_id}"
                                                f" to case {case_id}"
                                            )
                                            siemplify.add_comment(
                                                case_comment_with_prefix, case_id, None
                                            )
                                        except Exception as error:
                                            siemplify.LOGGER.error(
                                                "Failed to add case comment to case"
                                                f" with id {case_id}"
                                            )
                                            siemplify.LOGGER.exception(error)

            except Exception as error:
                siemplify.LOGGER.error(error)
                siemplify.LOGGER.exception(error)

        siemplify.LOGGER.info(
            " --- Finish synchronize Tickets Conversations"
            f" from {INTEGRATION_DISPLAY_NAME} to Siemplify --- "
        )

        siemplify.save_timestamp(datetime_format=True)
        siemplify.LOGGER.info("--------------- JOB FINISHED ---------------")

    except Exception as error:
        siemplify.LOGGER.error(
            f"Got exception on main handler. Error: {error}"
        )
        siemplify.LOGGER.exception(error)
        raise


if __name__ == "__main__":
    main()
