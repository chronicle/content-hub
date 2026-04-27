from __future__ import annotations
import datetime

from TIPCommon import extract_configuration_param, extract_action_param, construct_csv

from ..core.FreshworksFreshserviceManager import FreshworksFreshserviceManager
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler
from ..core.consts import (
    INTEGRATION_IDENTIFIER,
    INTEGRATION_DISPLAY_NAME,
    LIST_TICKETS_SCRIPT_NAME,
    DATE_FORMAT,
    ALL,
    ROWS_PER_PAGE_PARAM_NAME,
    START_AT_PAGE_PARAM_NAME,
    MAX_ROWS_TO_RETURN_PARAM_NAME,
)
from ..core.exceptions import FreshworksFreshserviceValidationError
from ..core.utils import remove_none_dictionary_values


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = f"{INTEGRATION_IDENTIFIER} - {LIST_TICKETS_SCRIPT_NAME}"
    siemplify.LOGGER.info("=================== Main - Param Init ===================")

    # Integration configuration
    api_root = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_IDENTIFIER,
        param_name="API Root",
        is_mandatory=True,
        print_value=True,
    )
    api_key = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_IDENTIFIER,
        param_name="API Key",
        is_mandatory=True,
        print_value=False,
        remove_whitespaces=False,
    )
    verify_ssl = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_IDENTIFIER,
        param_name="Verify SSL",
        input_type=bool,
        is_mandatory=True,
        default_value=True,
        print_value=True,
    )

    # Action configuration
    ticket_type = extract_action_param(
        siemplify,
        param_name="Ticket Type",
        print_value=True,
        default_value=ALL,
        is_mandatory=False,
    )
    requester_email = extract_action_param(
        siemplify, param_name="Requester", print_value=True, is_mandatory=False
    )
    include_stats = extract_action_param(
        siemplify,
        param_name="Include Stats",
        input_type=bool,
        print_value=True,
        default_value=False,
        is_mandatory=False,
    )
    workspace_id = extract_action_param(
        siemplify,
        param_name="Workspace ID",
        print_value=True,
        is_mandatory=False,
    )

    siemplify.LOGGER.info("----------------- Main - Started -----------------")

    # Action results
    status = EXECUTION_STATE_COMPLETED
    result_value = False

    try:
        search_for_last_x_hours = extract_action_param(
            siemplify,
            param_name="Search for Last X hours",
            input_type=int,
            print_value=True,
            is_mandatory=False,
        )
        rows_per_page = extract_action_param(
            siemplify,
            param_name=ROWS_PER_PAGE_PARAM_NAME,
            input_type=int,
            print_value=True,
            default_value=30,
            is_mandatory=False,
        )
        start_at_page = extract_action_param(
            siemplify,
            param_name=START_AT_PAGE_PARAM_NAME,
            input_type=int,
            print_value=True,
            default_value=1,
            is_mandatory=False,
        )
        max_rows_to_return = extract_action_param(
            siemplify,
            param_name=MAX_ROWS_TO_RETURN_PARAM_NAME,
            input_type=int,
            print_value=True,
            default_value=30,
            is_mandatory=False,
        )

        if isinstance(search_for_last_x_hours, int) and search_for_last_x_hours < 0:
            raise FreshworksFreshserviceValidationError(
                '"Search for Last X hours" parameter provided must be non-negative.'
            )
        if rows_per_page <= 0:
            raise FreshworksFreshserviceValidationError(
                f'"{ROWS_PER_PAGE_PARAM_NAME}" parameter provided must be positive.'
            )
        if start_at_page <= 0:
            raise FreshworksFreshserviceValidationError(
                f'"{START_AT_PAGE_PARAM_NAME}" parameter provided must be positive.'
            )
        if max_rows_to_return <= 0:
            raise FreshworksFreshserviceValidationError(
                f"'{MAX_ROWS_TO_RETURN_PARAM_NAME}'"
                " parameter provided must be positive."
            )

        manager = FreshworksFreshserviceManager(
            api_root=api_root,
            api_key=api_key,
            verify_ssl=verify_ssl,
            siemplify=siemplify,
        )

        tickets = manager.get_filtered_tickets(
            **remove_none_dictionary_values(
                updated_since=(
                    datetime.datetime.strftime(
                        datetime.datetime.now()
                        - datetime.timedelta(hours=search_for_last_x_hours),
                        DATE_FORMAT,
                    )
                    if isinstance(search_for_last_x_hours, int)
                    else None
                ),
                limit=max_rows_to_return,
                ticket_type=ticket_type if ticket_type != ALL else None,
                rows_per_page=rows_per_page,
                start_at_page=start_at_page,
                requester_email=requester_email,
                include_stats=include_stats,
                workspace_id=workspace_id,
            )
        )
        if tickets:
            siemplify.result.add_result_json(
                {"tickets": [ticket.to_json() for ticket in tickets]}
            )
            siemplify.result.add_data_table(
                title=f"{INTEGRATION_DISPLAY_NAME} Tickets Found",
                data_table=construct_csv([ticket.to_csv() for ticket in tickets]),
            )
            output_message = f"Successfully fetched {INTEGRATION_DISPLAY_NAME} tickets."
            result_value = True
        else:
            output_message = f"No tickets were found for the provided input parameters."

    except FreshworksFreshserviceValidationError as error:
        output_message = (
            f"Failed to list tickets with the provided parameters! Error is: {error}"
        )
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(error)

    except Exception as error:
        output_message = (
            f'Error executing action "{LIST_TICKETS_SCRIPT_NAME}". Reason: {error}'
        )
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(error)
        status = EXECUTION_STATE_FAILED

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(f"Status: {status}")
    siemplify.LOGGER.info(f"Result Value: {result_value}")
    siemplify.LOGGER.info(f"Output Message: {output_message}")
    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()
