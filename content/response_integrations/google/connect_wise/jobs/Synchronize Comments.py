from __future__ import annotations
from soar_sdk.SiemplifyUtils import output_handler

# ==============================================================================
# title           :UpdateComments.py
# description     :Siemplify job for updating comments in CaseWall and in ConnectWize
# author          :org@siemplify.co
# date            :01-07-17
# python_version  :2.7
# ==============================================================================

# =====================================
#              IMPORTS                #
# =====================================
from connect_wise.core.ConnectWiseManager import ConnectWiseManager
from soar_sdk.SiemplifyJob import SiemplifyJob
from soar_sdk.SiemplifyUtils import convert_unixtime_to_datetime
import logging


# =====================================
#             CONSTANTS               #
# =====================================
CASES_OPEN_STATUS_ENUM = "1"
SIEMPLIFY_COMMENT_PREFIX = "TN: "
CW_COMMENT_PREFIX = "CW: "
CW_SIEMPLIFY_CATEGORY = "Siemplify"
CW_LASTUPDATED_CONDITIONS_STR = (
    "conditions=status/name='Completed' and lastUpdated>[{0}]"
)


# CR: In all of the logging, use unicode().encode("utf-8") like in the connectors


# =====================================
#              CLASSES                #
# =====================================
@output_handler
def main():
    siemplify = SiemplifyJob()

    try:

        # Parameters.
        api_root = siemplify.parameters["API Root"]
        company_name = siemplify.parameters["Company Name"]
        public_api_key = siemplify.parameters["API Public Key"]
        private_api_key = siemplify.parameters["API Private Key"]
        script_name = siemplify.parameters["Script Name"]

        siemplify.script_name = script_name

        siemplify.LOGGER.info("-----Job Started-----")

        cw_manager = ConnectWiseManager(
            api_root, company_name, public_api_key, private_api_key
        )

        last_successful_execution_time = siemplify.fetch_timestamp(datetime_format=True)

        siemplify.LOGGER.info(
            f"Last successfuly execution time - {str(last_successful_execution_time).encode('utf-8')}"
        )

        # Replicate all cases comments to ConnectWize tickets comments
        siemplify.LOGGER.info(
            " +++ Starts synchronize comments from cases to ConnectWise tickets +++ "
        )
        cases_ids = siemplify.get_cases_by_filter(statuses=[CASES_OPEN_STATUS_ENUM])

        siemplify.LOGGER.info(f"Found {len(cases_ids)} open cases")

        for case_id in cases_ids:
            siemplify.LOGGER.info(
                f'Run on case with id: {str(case_id).encode("utf-8")}'
            )
            case = siemplify._get_case_by_id(str(case_id))
            case_comments = siemplify.get_case_comments(case["identifier"])
            siemplify.LOGGER.info(
                f"Found {len(case_comments)} comments for case with id: {str(case_id).encode('utf-8')} "
            )

            for comment in case_comments:
                # Covert to datetime
                comment_time = convert_unixtime_to_datetime(
                    (comment["modification_time_unix_time_in_ms"])
                )

                # Check that the comment is newer than the JOB timestamp
                if comment_time > last_successful_execution_time:
                    siemplify.LOGGER.info(
                        f"Found Case {str(case_id).encode('utf-8')} new comment"
                    )

                    # Add to comment Siemplify prefix in order to identify the comment as a siemplify TN comment
                    comment_text = f"{SIEMPLIFY_COMMENT_PREFIX}{comment['comment']}"

                    # Update all Alert's tickets in ConnectWise
                    for alert in case["cyber_alerts"]:
                        siemplify.LOGGER.info(
                            f"Iterate over case {str(case_id).encode('utf-8')} alerts"
                        )
                        ticket_id = alert["additional_data"]

                        # Add the comment to CW ticket
                        try:
                            siemplify.LOGGER.info(
                                f"Add comment to ticket {str(ticket_id).encode('utf-8')}"
                            )
                            cw_manager.add_comment_to_ticket(ticket_id, comment_text)
                        except Exception as err:
                            siemplify.LOGGER.error(
                                f"Failed to add comment to ticket {ticket_id}, error: {err}"
                            )
                            siemplify.LOGGER._log.exception(err)

        siemplify.LOGGER.info(
            " --- Finish synchronize comments from cases to ConnectWise tickets --- "
        )

        # Replicate all ConnectWIze tickets comments to TN cases comments
        siemplify.LOGGER.info(
            " +++ Start synchronize comments from ConnectWise tickets to cases +++ "
        )
        cw_last_time_format = cw_manager.covert_datetime_to_cw_format(
            last_successful_execution_time
        )
        tickets = cw_manager.get_tickets_by_conditions(
            f"status/name!='Completed' and lastUpdated>[{cw_last_time_format}]"
        )
        siemplify.LOGGER.info(
            f"Found {len(tickets)} tickets since: {last_successful_execution_time}"
        )
        siemplify.LOGGER.info("Start iterating over the tickets")

        for ticket in tickets:
            # Ticket summary is the related alert id in TN
            alert_id = ticket["summary"]

            # Fetch case id of the relevant alert
            alert_cases_ids = siemplify.get_cases_by_ticket_id(alert_id)
            siemplify.LOGGER.info(
                f'Case ids {len(alert_cases_ids)} found for ticket with id: {str(ticket["id"]).encode("utf-8")}'
            )

            # Fetch only the open cases
            alert_open_cases_ids = []
            for case_id in alert_cases_ids:
                case_obj = siemplify._get_case_by_id(str(case_id))
                if str(case_obj["status"]) == CASES_OPEN_STATUS_ENUM:
                    alert_open_cases_ids.append(case_id)

            if alert_open_cases_ids:
                siemplify.LOGGER.info(
                    f"Got ticket's open cases attached to alert-{str(alert_id).encode('utf-8')}, cases count-{len(alert_open_cases_ids)}"
                )

                # Fetch all ticket's comments
                ticket_comments = cw_manager.get_ticket_comments_since_time(
                    str(ticket["id"]), last_successful_execution_time
                )
                if ticket_comments:
                    siemplify.LOGGER.info(
                        f"Fetch ticket-{str(ticket['id']).encode('utf-8')} last comments, new comments count: {len(ticket_comments)}"
                    )

                    # Get all comments that didn't come from TN system
                    comments_to_add = [
                        comment
                        for comment in ticket_comments
                        if not comment["text"].startswith(SIEMPLIFY_COMMENT_PREFIX)
                    ]
                    siemplify.LOGGER.info(
                        f"Found {len(comments_to_add)} relevant comments to update in cases"
                    )

                    for alert_case_id in alert_open_cases_ids:
                        for comment in comments_to_add:
                            comment_with_prefix = (
                                f"{CW_COMMENT_PREFIX}{comment['text']}"
                            )
                            siemplify.add_comment(comment_with_prefix, alert_case_id)
                            siemplify.LOGGER.info(
                                f"Add comments to case-{alert_case_id}"
                            )
                else:
                    logging.debug(f"No new comments in ticket -{str(ticket['id'])}")

                # Fetch all ticket's time entries
                ticket_times_entries = cw_manager.get_ticket_times_entries(
                    str(ticket["id"]), last_successful_execution_time
                )

                if ticket_times_entries:
                    siemplify.LOGGER.info(
                        f"Fetch ticket-{str(ticket['id']).encode('utf-8')} last time-entries, new relevant entries count: {len(ticket_comments)}"
                    )
                    for alert_case_id in alert_open_cases_ids:
                        for entry in ticket_times_entries:
                            comment_with_prefix = f"{CW_COMMENT_PREFIX}{entry['notes']}"
                            siemplify.add_comment(comment_with_prefix, alert_case_id)
                            siemplify.LOGGER.info(
                                f"Add time-entries to case-{alert_case_id}"
                            )
                else:
                    siemplify.LOGGER.info(
                        f"No new time_entries in ticket -{str(ticket['id']).encode('utf-8')}"
                    )

        siemplify.LOGGER.info(
            " --- Finish synchronize comments from ConnectWise tickets to cases --- "
        )
        siemplify.save_timestamp(datetime_format=True)
        siemplify.LOGGER.info("Update Job last execution timestamp")
        logging.info("-----Job Finished-----")

    except Exception as err:
        siemplify.LOGGER.error(f"Got exception on main handler, ERROR: {err}")
        raise


if __name__ == "__main__":
    main()
