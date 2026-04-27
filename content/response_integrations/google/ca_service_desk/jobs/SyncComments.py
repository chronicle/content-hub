from __future__ import annotations
from soar_sdk.SiemplifyUtils import output_handler

# -*- coding: utf-8 -*-
# ==============================================================================
# title           :CaSoapManager.py
# description     :This Module contain all CA Desk operations functionality using Soap API
# author          :zdemoniac@gmail.com
# date            :1-9-18
# python_version  :2.7
# libraries       :time, xml, zeep
# requirements    :pip install zeep, ticketFields names in CA
# product_version :
# ==============================================================================

# =====================================
#              IMPORTS                #'
# =====================================
from ..core.CaSoapManager import CaSoapManager
from soar_sdk.SiemplifyJob import SiemplifyJob
import arrow


# =====================================
#             CONSTANTS               #
# =====================================
# Configurations.
DEFAULT_DAYS_BACKWARDS = 0

CA_RULE_NAME = "CA Desk Manager Ticket."
OPEN_CASE_STATUS_ENUM = 1
ID_PREFIX_IN_SUMMERY = "SIEMPLIFY_CASE_ID:"

# Prefixes.
CA_PREFIX = "CA: History Sync Job CA <-> Siemplify"
SIEMPLIFY_PREFIX = "SIEMPLIFY:"


# =====================================
#              CLASSES                #
# =====================================
@output_handler
def main():
    try:
        siemplify = SiemplifyJob()

        siemplify.script_name = siemplify.parameters["Script Name"]

        siemplify.LOGGER.info("--------------- JOB ITERATION STARTED ---------------")

        # Parameters.
        api_root = siemplify.parameters["API Root"]
        username = siemplify.parameters["Username"]
        password = siemplify.parameters["Password"]
        summery_field = siemplify.parameters.get("Summery Field", "summary")
        ticket_type_field = siemplify.parameters.get("Ticket Type Field", "type.sym")
        analyst_name_field = siemplify.parameters.get(
            "Analyst Type Field", "analyst.combo_name"
        )
        time_stamp_field = siemplify.parameters.get("Time Stamp Field", "time_stamp")
        ticket_fields_str = siemplify.parameters["Ticket Fields"]
        time_zone_string = siemplify.parameters["Timezone String"]

        # Turn str lists params to lists object.
        ticket_fields = ticket_fields_str.split(",") if ticket_fields_str else []

        # Configurations.
        ca_manager = CaSoapManager(api_root, username, password)

        # Get last Successful execution time.
        last_success_time = siemplify.fetch_timestamp(datetime_format=False)
        siemplify.LOGGER.info(
            f'Got last successful run: {str(last_success_time).encode("utf-8")}'
        )

        # ----------------- Sync Tickets Comment to Siemplify -----------------
        siemplify.LOGGER.info("########## Sync Tickets Comment to Siemplify ##########")

        # Get tickets that where modified since last success time.
        last_modified_ticket_ids = ca_manager.get_incident_ids_by_filter(
            last_modification_unixtime_milliseconds=last_success_time
        )
        siemplify.LOGGER.info(
            f'Found {str(len(last_modified_ticket_ids)).encode("utf-8")} modified tickets with ids: {str(last_modified_ticket_ids).encode("utf-8")} since {str(last_success_time).encode("utf-8")}'
        )

        for ticket_id in last_modified_ticket_ids:
            siemplify.LOGGER.info(
                f'Run on CA incident with id: {str(ticket_id).encode("utf-8")}'
            )
            # Get Last comments for ticket.
            ticket_comments = ca_manager.get_incident_comments_since_time(
                ticket_id, last_success_time
            )
            siemplify.LOGGER.info(
                f'Found {str(len(ticket_comments)).encode("utf-8")} comment for ticket with id: {str(ticket_id).encode("utf-8")}'
            )
            # Get Cases id for ticket.
            siemplify.LOGGER.info(
                f'Get case IDs for ticket_id: {str(ticket_id).encode("utf-8")}'
            )
            cases_ids_for_ticket = siemplify.get_cases_by_ticket_id(ticket_id)
            siemplify.LOGGER.info(
                f'Got {len(cases_ids_for_ticket)} case related to ticket id {str(ticket_id).encode("utf-8")}, the cases IDs are: {str(cases_ids_for_ticket).encode("utf-8")}'
            )

            # Add comments to cases.
            for case_id in cases_ids_for_ticket:
                siemplify.LOGGER.info(
                    f'Add comments to case with id: {str(case_id).encode("utf-8")}'
                )

                # Fetch case comments.
                case_comments_objs_list = siemplify.get_case_comments(str(case_id))
                case_comments_list = [
                    case_comment["comment"] for case_comment in case_comments_objs_list
                ]

                # fetch alert id for case.
                case_obj = siemplify._get_case_by_id(str(case_id))
                if case_obj:
                    alert_ids = [
                        cyber_alert["external_id"]
                        for cyber_alert in case_obj["cyber_alerts"]
                    ]
                else:
                    alert_ids = []

                # Sort comments by time.
                ticket_comments = sorted(
                    ticket_comments, key=lambda item: item.get(time_stamp_field, 0)
                )

                for comment in ticket_comments:

                    # Validate that the comment is not from sieplify.
                    # Compare with Siemplify prefix without the column because of the split.
                    siemplify.LOGGER.info(
                        f"Check if prefix in comment. comment keys:{list(comment.keys())}"
                    )
                    if SIEMPLIFY_PREFIX not in comment.get("description", ""):
                        siemplify.LOGGER.info("No prefix found.")
                        # Add prefix to comment.
                        description = comment.get(
                            "description", "No Comment description"
                        )
                        if "description" in comment:
                            del comment["description"]

                        analyst = comment.get(analyst_name_field, None)
                        ticket_type = comment.get(ticket_type_field, None)
                        ticket_time_stamp = comment.get(time_stamp_field, None)

                        # Convert Unix time to UTC datetime.

                        ticket_time_datetime = (
                            arrow.get(float(ticket_time_stamp)).to(time_zone_string)
                            if ticket_time_stamp
                            else None
                        )
                        siemplify.LOGGER.info("Building Comment.")
                        case_comment = f"{CA_PREFIX} \nTicket ID:{ticket_id} \nComment: {description} \nAnalyst: {analyst} \nTicket Type: {ticket_type} \nTime: {ticket_time_datetime}"
                        # Add comment to case.
                        try:
                            # Validate alert in case.
                            if ticket_id in alert_ids:
                                if case_comment not in case_comments_list:
                                    siemplify.add_comment(
                                        case_id=case_id,
                                        comment=case_comment,
                                        alert_identifier=None,
                                    )
                                    siemplify.LOGGER.info("Comment Added")
                                else:
                                    siemplify.LOGGER.info(
                                        "Comment already exists in case."
                                    )
                            else:
                                siemplify.LOGGER.info(
                                    "Alert is not contained in case, comment was not added."
                                )
                        except Exception as err:
                            siemplify.LOGGER.error(
                                f"Error adding comment to case {case_id}, ERROR: {err}"
                            )

        # ----------------- Sync Tickets Created From Workflow to Siemplify Cases -----------------
        siemplify.LOGGER.info(
            "########## Sync Tickets Created From Workflow to Siemplify Cases ##########"
        )

        # Extract ticket ids from modified tickets that where opened from workflow.
        for ticket_id in last_modified_ticket_ids:
            siemplify.LOGGER.info(f"Run on ticket id {ticket_id}")
            # Bring the ticket.
            ticket_data = ca_manager.get_incident_by_id(ticket_id, ticket_fields)
            if (
                ticket_data[summery_field]
                and ID_PREFIX_IN_SUMMERY in ticket_data[summery_field]
            ):
                siemplify.LOGGER.info(
                    f"Incident with ID {ticket_id} was created workflow."
                )
                # Extract ticket comments.
                ticket_comments = ca_manager.get_incident_comments_since_time(
                    ticket_id, last_success_time
                )
                # Extract case id from ticket summery.
                case_id = ticket_data[summery_field].split(":")[1]

                # fetch alert id for case.
                case_obj = siemplify._get_case_by_id(str(case_id))
                if case_obj:
                    alert_ids = [
                        cyber_alert["external_id"]
                        for cyber_alert in case_obj["cyber_alerts"]
                    ]
                else:
                    alert_ids = []

                # Sort comments by time.
                ticket_comments = sorted(
                    ticket_comments, key=lambda item: item.get(time_stamp_field, 0)
                )

                for comment in ticket_comments:
                    # Validate that the comment is not from sieplify.
                    # Compare with Siemplify prefix without the column because of the split.
                    if SIEMPLIFY_PREFIX not in comment.get("description", ""):
                        # Add prefix to comment.
                        description = comment.get(
                            "description", "No Comment description"
                        )
                        if "description" in comment:
                            del comment["description"]

                        analyst = comment.get(analyst_name_field, None)
                        ticket_type = comment.get(ticket_type_field, None)
                        ticket_time_stamp = comment.get(time_stamp_field, None)

                        # Convert Unix time to UTC datetime.
                        ticket_time_datetime = (
                            arrow.get(float(ticket_time_stamp)).to(time_zone_string)
                            if ticket_time_stamp
                            else None
                        )

                        case_comment = f"{CA_PREFIX} \nTicket ID: {ticket_id} \nComment: {description} \nAnalyst: {analyst} \nTicket Type: {ticket_type} \nTime: {ticket_time_datetime}"

                        # Add comment to case.
                        try:
                            # Validate alert in case.
                            if ticket_id in alert_ids:
                                siemplify.add_comment(
                                    case_id=case_id,
                                    comment=case_comment,
                                    alert_identifier=None,
                                )
                                siemplify.LOGGER.info("Comment Added")
                            else:
                                siemplify.LOGGER.info(
                                    "Alert is not contained in case, comment was not added."
                                )
                        except Exception as err:
                            siemplify.LOGGER.error(
                                f"Error adding comment to case {case_id}, ERROR: {err}"
                            )
            else:
                siemplify.LOGGER.info(
                    f"Incident with id {ticket_id} was not created by workflow."
                )

        # # ----------------- Sync Siemplify Comments to Tickets -----------------
        # siemplify.LOGGER.info('########## Sync Siemplify Comments to Tickets ##########')
        scope_cases = []  # Cases that are in the relevant time scope.
        # Get all open cases.
        open_cases_ids = siemplify.get_cases_by_filter(statuses=[OPEN_CASE_STATUS_ENUM])

        for case_id in open_cases_ids:
            # Get case data.
            case = siemplify._get_case_by_id(str(case_id))
            for alert in case["cyber_alerts"]:
                siemplify.LOGGER.info(
                    f"Iterate over case {str(case_id).encode('utf-8')} alerts"
                )
                if alert["rule_generator"] == CA_RULE_NAME:
                    case_comments = siemplify.get_case_comments(case["identifier"])
                    siemplify.LOGGER.info(
                        f"Fetch case {str(case_id).encode('utf-8')} comments"
                    )
                    ticket_id = alert["external_id"]
                    for comment in case_comments:
                        # Covert to datetime
                        comment_time = comment["modification_time_unix_time_in_ms"]
                        # Check that the comment is newer than the JOB timestamp
                        if (
                            comment_time > last_success_time
                            and CA_PREFIX not in comment["comment"]
                        ):
                            siemplify.LOGGER.info(
                                f"Found Case {str(case_id).encode('utf-8')} new comment"
                            )
                            # Add to comment Siemplify prefix in order to identify the comment as a siemplify TN comment
                            comment_text = f"{SIEMPLIFY_PREFIX}{comment['comment']}"
                            # Update all Alert's tickets in ConnectWise
                            # Add the comment to CA ticket
                            try:
                                siemplify.LOGGER.info(
                                    f"Add comment to ticket {ticket_id}"
                                )
                                ca_manager.add_comment_to_incident(
                                    ref_num=ticket_id, comment=comment_text
                                )
                            except Exception as err:
                                siemplify.LOGGER.error(
                                    f"Failed to add comment to ticket {ticket_id}, error: {err}"
                                )

        # Update last successful run time.
        siemplify.save_timestamp(datetime_format=True)
        siemplify.LOGGER.info("--------------- JOB ITERATION FINISHED ---------------")

    except Exception as err:
        siemplify.LOGGER.error(f"Got exception on main handler.Error: {err}")
        raise


if __name__ == "__main__":
    main()
