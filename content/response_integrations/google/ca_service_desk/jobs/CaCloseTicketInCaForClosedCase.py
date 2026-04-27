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
#              IMPORTS                #
# =====================================
from ..core.CaSoapManager import CaSoapManager
from soar_sdk.SiemplifyJob import SiemplifyJob

# =====================================
#             CONSTANTS               #
# =====================================
# Configurations.
DEFAULT_DAYS_BACKWARDS = 0
DATE_TIME_STR_FORMAT = "%d-%m-%Y %H:%M:%S"

# Consts.
CA_ALERTS_RULE = "CA Desk Manager Ticket."
UTC_TIMEZONE_STRING = "UTC"
DEFAULT_CLOSURE_COMMENT = "Closed at Siemplify."


# =====================================
#              CLASSES                #
# =====================================
@output_handler
def main():
    try:
        # Define SiemplifyJob object.
        siemplify = SiemplifyJob()

        # Obtain Script Name.
        siemplify.script_name = siemplify.parameters["Script Name"]

        siemplify.LOGGER.info("--------------- JOB ITERATION STARTED ---------------")

        # Parameters
        # Credentials
        api_root = siemplify.parameters["API Root"]  # Default: 'http://xxxxx:8080'
        username = siemplify.parameters["Username"]
        password = siemplify.parameters["Password"]

        group_filter_str = siemplify.parameters["Group Filter"]
        group_field = siemplify.parameters.get("Group Field", "group.combo_name")
        ticket_final_status = siemplify.parameters["Ticket Final Status"]

        # Convert str lists to list.
        group_filter = group_filter_str.split(",") if group_filter_str else []

        # Define Ca Desk Manager object.
        ca_manager = CaSoapManager(api_root, username, password)

        # Get last Successful execution time.
        last_success_time_unixtime = siemplify.fetch_timestamp(datetime_format=False)
        siemplify.LOGGER.info(
            f'Got last successful run: {str(last_success_time_unixtime).encode("utf-8")}'
        )

        siemplify.LOGGER.info(
            f'Converted last run time to unixtime:{str(last_success_time_unixtime).encode("utf-8")}'
        )
        # Get alerts that were dismissed or the cases they are contained in closed since last success run.
        ticket_ids_to_close = (
            []
        )  # Ticket ids of the dismissed alerts since last success time.

        # Get alert ticket ids from closed cases.
        siemplify.LOGGER.info("Get alert IDs from closed cases.")
        ticket_ids_to_close.extend(
            siemplify.get_alerts_ticket_ids_from_cases_closed_since_timestamp(
                last_success_time_unixtime, CA_ALERTS_RULE
            )
        )
        siemplify.LOGGER.info(
            f"Got {len(ticket_ids_to_close)} alert IDs from closed cases."
        )

        siemplify.LOGGER.info("Unify alert IDs list.")
        # Unify alert ids list.
        ticket_ids_to_close = list(set(ticket_ids_to_close))

        siemplify.LOGGER.info(
            f'Found {str(len(ticket_ids_to_close)).encode("utf-8")} closed alert with ids:{str(ticket_ids_to_close).encode("utf-8")} since:{str(last_success_time_unixtime).encode("utf-8")}'
        )

        siemplify.LOGGER.info("Run on alerts ticket ids")
        # Run on tickets ids list and close the ticket at the Ca Desk Manager.
        for ticket_id in ticket_ids_to_close:
            siemplify.LOGGER.info(
                f'Get related cases for alert with ticket id: {str(ticket_id).encode( "utf-8")}'
            )
            # Verify alert's case is not a test case.
            related_cases = siemplify.get_cases_by_ticket_id(ticket_id)
            siemplify.LOGGER.info(
                f'Got related cases for alert with ticket id {str(ticket_id).encode("utf-8")}: {str(related_cases).encode("utf-8")}'
            )
            siemplify.LOGGER.info(
                f'Run on related cases for alert with ticket id {str(ticket_id).encode("utf-8")}'
            )
            for case_id in related_cases:
                siemplify.LOGGER.info(f"Run on case id: {ticket_id}")
                # Get alert's case content.
                siemplify.LOGGER.info("")
                case_content = siemplify._get_case_by_id(str(case_id))
                # Get the alert content from the case.
                alerts = case_content["cyber_alerts"]
                for alert in alerts:
                    if ticket_id == alert["additional_properties"]["TicketId"]:
                        if alert["additional_properties"]["IsTestCase"] == "False":
                            # Close incident.
                            try:
                                # Get Description from case closure reason.
                                description = ""
                                case_closure_reason_data = (
                                    siemplify.get_case_closure_details(
                                        [str((case_id)).encode("utf-8")]
                                    )
                                )

                                # Get incident group.
                                incident_group = ca_manager.get_incident_by_id(
                                    ticket_id, [group_field]
                                )
                                # verify group filter.
                                if (
                                    group_filter
                                    and (incident_group[group_field]) in group_filter
                                ):
                                    ca_manager.change_ticket_status(
                                        ticket_id, ticket_final_status
                                    )
                                    if case_closure_reason_data:
                                        closure_data_list = [
                                            f"{key}:{str(val).encode('utf-8')}"
                                            for key, val in case_closure_reason_data[
                                                0
                                            ].items()
                                        ]
                                        description = ", ".join(closure_data_list)
                                        ca_manager.add_comment_to_incident(
                                            ref_num=ticket_id, comment=description
                                        )

                                    else:
                                        ca_manager.add_comment_to_incident(
                                            ref_num=ticket_id,
                                            comment=DEFAULT_CLOSURE_COMMENT,
                                        )

                                    siemplify.LOGGER.info(
                                        f"Ticket with id:{ticket_id} closed."
                                    )
                                else:
                                    siemplify.LOGGER.info(
                                        f'Ticket "{ticket_id}" did not matched to group.For group {group_filter}'
                                    )
                            except Exception as e:
                                siemplify.LOGGER.error(f"An error closing ticket: {e}")
                                siemplify.LOGGER._log.exception(e)

        # Update last successful run time.
        siemplify.save_timestamp(datetime_format=True)
        siemplify.LOGGER.info("--------------- JOB ITERATION FINISHED ---------------")
    except Exception as err:
        siemplify.LOGGER.error(f"Got exception on main handler.Error: {err}")
        raise


if __name__ == "__main__":
    main()
