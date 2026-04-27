from __future__ import annotations
import datetime
import json
import sys

from TIPCommon import extract_configuration_param, extract_action_param

from ..core.IronportConstants import (
    INTEGRATION_NAME,
    SCRIPT_GET_ALL_RECIPIENTS_BY_SUBJECT,
    DAYS,
    API_TIME_FORMAT,
    DEFAULT_MAX_RECIPIENTS_TO_RETURN,
    DEFAULT_MESSAGES_PAGE_SIZE,
    MAX_PAGE_SIZE,
    MIN_PAGE_SIZE,
)
from ..core.IronportExceptions import (
    IronportAsyncOSMessagesException,
    IronportManagerException,
)
from ..core.IronportManagerAPI import IronportManagerAPI
from ..core.IronportUtils import is_script_approaching_timeout
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from soar_sdk.ScriptResult import EXECUTION_STATE_INPROGRESS
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler, unix_now


def get_recipients(
    siemplify,
    ironport_manager,
    action_start,
    start_date,
    end_date,
    limit,
    subject,
    page_size,
    last_messages_offset=0,
    recipients=None,
):
    """
    Main part of the action that gets the initial information for a ticket
    :param siemplify: SiemplifyAction object.
    :param ironport_manager: IronportManagerAPI manager object.
    :param action_start: {int} Action start time
    :param start_date: {str} String formatted date. Get recipients from start date.
    :param end_date: {str} String formatted date. Get recipients until end date.
    :param subject: {str} The subject of the message for which to get the all recipients
    :param page_size: {int} The page size of searching for messages
    :param last_messages_offset: {int} Last messages offset that was reached. If first run, 0 will be used as initial offset.
    :param recipients: {list} Fetched recipients from previous iterations. If first run, empty list will be used.
    :param limit: Max recipients to return
    :return: {output message, json result, execution_state}
    """

    status = EXECUTION_STATE_COMPLETED
    output_messages = []
    recipients = set(recipients) if recipients else set()

    try:

        while True:
            if is_script_approaching_timeout(action_start):
                siemplify.LOGGER.info(
                    "Action run cycle reached timeout. "
                    f"Reached offset {last_messages_offset}. "
                    "More messages will be fetched in the next action iteration"
                )
                status = EXECUTION_STATE_INPROGRESS
                break
            siemplify.LOGGER.info(
                f"Fetching messages from offset {last_messages_offset}"
            )
            has_more_messages, messages = ironport_manager.get_messages_page(
                start_date=start_date,
                end_date=end_date,
                subjects=[subject],
                offset=last_messages_offset,
                limit=page_size,
            )
            fetched_recipients = [message.recipients for message in messages]
            siemplify.LOGGER.info(
                f"Successfully fetched {len(fetched_recipients)} recipients"
            )

            for message_recipients in fetched_recipients:
                recipients.update(message_recipients)

            last_messages_offset += page_size

            if not has_more_messages:
                siemplify.LOGGER.info(f"Finished fetching all messages")
                break

            if limit and len(recipients) >= limit:
                siemplify.LOGGER.info(
                    'Reached "Max Recipients to Return" limit. '
                    "Stopped fetching messages. "
                )
                break

        if status == EXECUTION_STATE_INPROGRESS:
            output_messages.append("Waiting for all recipients to be fetched")
            result_value = json.dumps(
                {
                    # Initial start date from first iteration run
                    "start_date": start_date,
                    # Initial end date from first iteration run
                    "end_date": end_date,
                    "last_message_offset": last_messages_offset,
                    "recipients": list(recipients),
                }
            )
        else:
            # Finished fetching all messages
            recipients = list(recipients)
            if limit and len(recipients) > limit:
                recipients = recipients[:limit]
                output_messages.append(
                    "The Recipient list got truncated because of the "
                    " 'Max Recipients to Return' limit."
                )

            siemplify.result.add_result_json({subject: recipients})
            result_value = json.dumps(recipients)
            output_messages.append(
                f"Found {len(recipients)} recipients for the specified email subject "
                f"{subject}"
            )

    except IronportAsyncOSMessagesException as e:
        message = (
            f"Failed to get recipients for the specified subject {subject}. "
            f"Error is {e}"
        )
        siemplify.LOGGER.error(message)
        siemplify.LOGGER.exception(e)
        output_messages.append(message)
        result_value = json.dumps([])
        status = EXECUTION_STATE_COMPLETED

    except IronportManagerException as e:
        message = f"Failed to execute action! Error is {e}"
        siemplify.LOGGER.error(message)
        siemplify.LOGGER.exception(e)
        output_messages.append(message)
        result_value = json.dumps([])
        status = EXECUTION_STATE_FAILED

    output_message = "\n".join(output_messages)
    return output_message, result_value, status


@output_handler
def main(is_first_run):
    siemplify = SiemplifyAction()
    siemplify.script_name = SCRIPT_GET_ALL_RECIPIENTS_BY_SUBJECT
    output_messages = []
    action_start = unix_now()

    mode = "Main" if is_first_run else "Fetch more messages"

    siemplify.LOGGER.info(f"----------------- {mode} - Started -----------------")
    siemplify.LOGGER.info(f"Action execution time - {action_start}")

    server_address = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Server Address",
        print_value=True,
        input_type=str,
        is_mandatory=True,
    )

    port = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="AsyncOS API Port",
        print_value=True,
        input_type=int,
        is_mandatory=True,
    )

    username = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Username",
        print_value=False,
        input_type=str,
        is_mandatory=True,
    )

    password = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Password",
        print_value=False,
        input_type=str,
        is_mandatory=True,
    )

    ca_certificate = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="CA Certificate File - parsed into Base64 String",
    )

    use_ssl = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Use SSL",
        print_value=True,
        input_type=bool,
        is_mandatory=True,
    )

    verify_ssl = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Verify SSL",
        print_value=True,
        input_type=bool,
        is_mandatory=True,
    )

    # Action parameters
    subject = extract_action_param(
        siemplify,
        param_name="Subject",
        print_value=True,
        input_type=str,
        is_mandatory=True,
    )

    try:

        ironport_manager = IronportManagerAPI(
            server_address=server_address,
            port=port,
            username=username,
            password=password,
            ca_certificate=ca_certificate,
            use_ssl=use_ssl,
            verify_ssl=verify_ssl,
        )
        limit = extract_action_param(
            siemplify,
            param_name="Max Recipients to Return",
            print_value=True,
            input_type=int,
            is_mandatory=False,
            default_value=DEFAULT_MAX_RECIPIENTS_TO_RETURN,
        )
        page_size = extract_action_param(
            siemplify,
            param_name="Page Size",
            print_value=True,
            input_type=int,
            is_mandatory=False,
            default_value=DEFAULT_MESSAGES_PAGE_SIZE,
        )

        if page_size < MIN_PAGE_SIZE or page_size > MAX_PAGE_SIZE:
            page_size = DEFAULT_MESSAGES_PAGE_SIZE
            siemplify.LOGGER.info(
                f"\"Page Size\" parameter is not in range of {MIN_PAGE_SIZE}-"
                f"{MAX_PAGE_SIZE}. "
                f"Using default of {DEFAULT_MESSAGES_PAGE_SIZE}"
            )

        if limit <= 0:
            limit = DEFAULT_MAX_RECIPIENTS_TO_RETURN
            siemplify.LOGGER.info(
                f"\"Max Recipients to Return\" parameter must be positive. "
                f"Using default value of {DEFAULT_MAX_RECIPIENTS_TO_RETURN}"
            )

        siemplify.LOGGER.info("----------------- Main - Started -----------------")

        if is_first_run:
            search_backwards_unit = extract_action_param(
                siemplify,
                param_name="Set Search Email Period in",
                print_value=True,
                is_mandatory=False,
                default_value=DAYS,
            )
            search_backwards_amount = extract_action_param(
                siemplify,
                param_name="Search Emails for Last X",
                print_value=True,
                input_type=int,
                is_mandatory=True,
            )
            start_date = datetime.datetime.utcnow() - datetime.timedelta(
                **{search_backwards_unit.lower(): search_backwards_amount}
            )
            start_date = start_date.strftime(API_TIME_FORMAT)
            end_date = datetime.datetime.utcnow().strftime(API_TIME_FORMAT)
            output_message, result_value, status = get_recipients(
                siemplify,
                ironport_manager,
                action_start,
                start_date,
                end_date,
                limit,
                subject,
                page_size,
            )
        else:
            additional_data = json.loads(siemplify.parameters["additional_data"])
            start_date = additional_data.get("start_date")
            end_date = additional_data.get("end_date")
            last_message_offset = additional_data.get("last_message_offset", 0)
            recipients = additional_data.get("recipients")
            output_message, result_value, status = get_recipients(
                siemplify,
                ironport_manager,
                action_start,
                start_date,
                end_date,
                limit,
                subject,
                page_size,
                last_message_offset,
                recipients,
            )

    except Exception as e:
        output_message = f"Failed to execute action! Error is {e}"
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(e)
        result_value = json.dumps([])
        status = EXECUTION_STATE_FAILED

    siemplify.LOGGER.info(f"----------------- {mode} - Finished -----------------")
    siemplify.LOGGER.info(f"Status: {status}")
    siemplify.LOGGER.info(f"Result Value: {result_value}")
    siemplify.LOGGER.info(f"Output Message: {output_message}")

    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    is_first_run = len(sys.argv) < 3 or sys.argv[2] == "True"
    main(is_first_run)
