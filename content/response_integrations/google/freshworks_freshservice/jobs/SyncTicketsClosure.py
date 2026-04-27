from __future__ import annotations
from TIPCommon import (
    extract_action_param,
    validate_timestamp,
    siemplify_fetch_timestamp,
    siemplify_save_timestamp,
    convert_datetime_to_unix_time,
)

from ..core.FreshworksFreshserviceManager import FreshworksFreshserviceManager
from soar_sdk.SiemplifyJob import SiemplifyJob
from soar_sdk.SiemplifyUtils import output_handler
from ..core.consts import (
    TICKETS_SYNC_CLOSURE_JOB_NAME,
    INTEGRATION_DISPLAY_NAME,
    DEFAULT_TIME_FRAME,
    TICKETS_CONNECTOR_SUPPORTED_TICKET_TYPES,
    MAPPED_NUMERIC_TICKET_STATUSES,
    CLOSED_TICKET,
    PARAMETERS_DEFAULT_DELIMITER,
    DEVICE_PRODUCT,
)
from ..core.exceptions import FreshworksFreshserviceTicketsClosureJobError
from ..core.utils import is_siemplify_alert_matches_freshservice_ticket


@output_handler
def main():
    siemplify = SiemplifyJob()
    siemplify.script_name = TICKETS_SYNC_CLOSURE_JOB_NAME
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
    default_ticket_description = extract_action_param(
        siemplify,
        param_name="Default Ticket Description",
        is_mandatory=True,
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

        if hours_backwards < 0:
            raise FreshworksFreshserviceTicketsClosureJobError(
                '"Offset time in hours" must be non-negative.'
            )

        # Get last Successful execution time.
        last_successful_execution_time = validate_timestamp(
            last_run_timestamp=siemplify_fetch_timestamp(
                siemplify=siemplify, datetime_format=True
            ),
            offset_in_hours=hours_backwards,
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

        ticket_ids_for_closed_cases = []
        for ticket_type in TICKETS_CONNECTOR_SUPPORTED_TICKET_TYPES:
            try:
                siemplify.LOGGER.info(
                    f"Fetching closed cases for tickets of type: {ticket_type}"
                )
                ticket_ids_for_closed_cases.extend(
                    siemplify.get_alerts_ticket_ids_from_cases_closed_since_timestamp(
                        timestamp_unix_ms=convert_datetime_to_unix_time(
                            last_successful_execution_time
                        ),
                        rule_generator=f"Freshservice_{ticket_type}",
                    )
                )
            except Exception as error:
                siemplify.LOGGER.error(
                    "Failed to get alert ticket ids with ticket type"
                    f" {ticket_type} of closed cases since last fetch time: "
                    f"{last_successful_execution_time}"
                )
                siemplify.LOGGER.exception(error)

        ticket_ids_for_closed_cases = list(set(ticket_ids_for_closed_cases))
        siemplify.LOGGER.info(
            f"Found {len(ticket_ids_for_closed_cases)} closed alert "
            f"with ids:{PARAMETERS_DEFAULT_DELIMITER.join(ticket_ids_for_closed_cases)}"
        )

        if ticket_ids_for_closed_cases:
            siemplify.LOGGER.info(
                f"--- Started Closing Tickets in {INTEGRATION_DISPLAY_NAME} ---"
            )

        for ticket_id in ticket_ids_for_closed_cases:
            # Verify alert's case is not a test case.
            related_cases = siemplify.get_cases_by_ticket_id(ticket_id)
            for case_id in related_cases:
                case_content = siemplify._get_case_by_id(case_id)
                for alert in case_content.get("cyber_alerts", []):
                    is_test_case = (
                        alert.get("additional_properties", {}).get("IsTestCase")
                        == "True"
                    )
                    needs_to_be_closed = (
                        is_siemplify_alert_matches_freshservice_ticket(
                            alert, str(ticket_id), DEVICE_PRODUCT
                        )
                        and not is_test_case
                    )
                    if needs_to_be_closed:
                        try:
                            siemplify.LOGGER.info(
                                f"Closing ticket {ticket_id}"
                                f" in {INTEGRATION_DISPLAY_NAME}"
                            )
                            ticket = manager.get_ticket(ticket_id)
                            ticket_description = (
                                ticket.description or default_ticket_description
                            )
                            manager.update_ticket(
                                ticket_id=ticket_id,
                                status=MAPPED_NUMERIC_TICKET_STATUSES[CLOSED_TICKET],
                                description=ticket_description,
                            )
                        except Exception as error:
                            siemplify.LOGGER.error(
                                f"Failed to close ticket {ticket_id}. Reason: {error}"
                            )
                            siemplify.LOGGER.exception(error)

        if ticket_ids_for_closed_cases:
            siemplify.LOGGER.info(
                f"--- Finished synchronizing closed alerts from Siemplify to {INTEGRATION_DISPLAY_NAME} ---"
            )
            siemplify_save_timestamp(siemplify=siemplify, datetime_format=True)
        siemplify.LOGGER.info("--------------- JOB FINISHED ---------------")

    except Exception as e:
        siemplify.LOGGER.error(f"Got exception on main handler. Error: {e}")
        siemplify.LOGGER.exception(e)
        raise


if __name__ == "__main__":
    main()
