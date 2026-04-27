from __future__ import annotations
import json
import sys

from soar_sdk.ScriptResult import (
    EXECUTION_STATE_COMPLETED,
    EXECUTION_STATE_FAILED,
    EXECUTION_STATE_INPROGRESS,
)
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler

from TIPCommon.extraction import extract_configuration_param, extract_action_param

from ..core.constants import INTEGRATION_NAME, ADD_NOTE_AND_WAIT_ACTION
from ..core.ServiceDeskPlusV3Exceptions import NoteNotFoundException
from ..core.ServiceDeskPlusManagerV3 import ServiceDeskPlusManagerV3


def start_operation(
    siemplify,
    servicedesk_manager,
    mark_first_response,
    add_to_linked_requests,
    request_id,
    show_to_requester,
    notify_technician,
    note,
):
    """
    Initial Function that adds a note and gets the current number of notes
    :param siemplify {Obj} Siemplify object
    :param servicedesk_manager {Obj} Object of the ServiceDesk manager
    :param add_to_linked_requests {bool} The note should be linked to requests
    :param request_id {str} Request of the of the ticket in ServiceDesk
    :param show_to_requester {bool} The note should be shown to the requester
    :param notify_technician {bool} The technician should be notified
    :param mark_first_response {bool} First response should be marked
    :param note {str} Note to add to the ticket
    """

    try:
        _result = servicedesk_manager.add_note(
            mark_first_response=mark_first_response,
            add_to_linked_requests=add_to_linked_requests,
            request_id=request_id,
            show_to_requester=show_to_requester,
            notify_technician=notify_technician,
            note=note,
        )

        request_notes = servicedesk_manager.get_notes(request_id=request_id)
        request_notes_num = len(request_notes.notes)
        output_message = f"Successfully added note to request with ID {request_id}"
        status = EXECUTION_STATE_INPROGRESS
        result_value = {"number_of_notes": request_notes_num}
        result_value = json.dumps(result_value)

    except Exception as e:
        output_message = (
            f"Error executing action {ADD_NOTE_AND_WAIT_ACTION}. Reason: {e}"
        )
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(e)
        status = EXECUTION_STATE_FAILED
        result_value = False

    return output_message, result_value, status


def query_operation_status(siemplify, servicedesk_manager, request_id):
    """
    Initial Function that adds a note and gets the current number of notes
    :param siemplify {Obj} Siemplify object
    :param servicedesk_manager {Obj} Object of the ServiceDesk manager
    :param request_id {str} Request of the of the ticket in ServiceDesk
    """
    try:
        request_notes = servicedesk_manager.get_notes(request_id=request_id)
        latest_note_id = "0"
        if request_notes.note_ids:
            latest_note_id = max(request_notes.note_ids)

        try:
            servicedesk_manager.get_note_with_id(
                request_id=request_id, note_id=latest_note_id
            )
            status = EXECUTION_STATE_COMPLETED
            result_value = True
            output_message = f"Note for Request with ID: {request_id} was added."
            siemplify.result.add_result_json(request_notes.raw_data)

        except NoteNotFoundException:
            status = EXECUTION_STATE_INPROGRESS
            output_message = f"There are no new notes for request with ID: {request_id}. Will check again later...."
            result_value = json.dumps({})

    except Exception as e:
        output_message = (
            f"Error executing action {ADD_NOTE_AND_WAIT_ACTION}. Reason: {e}"
        )
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(e)
        status = EXECUTION_STATE_FAILED
        result_value = False

    return output_message, result_value, status


@output_handler
def main(is_first_run):
    siemplify = SiemplifyAction()
    siemplify.script_name = ADD_NOTE_AND_WAIT_ACTION
    mode = "Main" if is_first_run else "Check changes"
    siemplify.LOGGER.info(f"----------------- {mode} - Param Init -----------------")

    api_root = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Api Root",
        print_value=True,
    )
    api_key = extract_configuration_param(
        siemplify, provider_name=INTEGRATION_NAME, param_name="Api Key"
    )
    verify_ssl = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Verify SSL",
        default_value=False,
        input_type=bool,
        print_value=True,
    )

    # Action Parameters
    note = extract_action_param(
        siemplify, param_name="Note", is_mandatory=True, input_type=str
    )
    request_id = extract_action_param(
        siemplify, param_name="Request ID", is_mandatory=True, input_type=str
    )
    show_to_requester = extract_action_param(
        siemplify,
        param_name="Show To Requester",
        default_value=False,
        is_mandatory=False,
        input_type=bool,
        print_value=True,
    )
    notify_technician = extract_action_param(
        siemplify,
        param_name="Notify Technician",
        default_value=False,
        is_mandatory=False,
        input_type=bool,
        print_value=True,
    )
    mark_first_response = extract_action_param(
        siemplify,
        param_name="Mark First Response",
        default_value=False,
        is_mandatory=False,
        input_type=bool,
        print_value=True,
    )
    add_to_linked_requests = extract_action_param(
        siemplify,
        param_name="Add To Linked Requests",
        default_value=False,
        is_mandatory=False,
        input_type=bool,
        print_value=True,
    )

    siemplify.LOGGER.info(f"----------------- {mode} - Started -----------------")
    status = EXECUTION_STATE_COMPLETED
    result_value = True

    try:
        servicedesk_manager = ServiceDeskPlusManagerV3(
            api_root=api_root, api_key=api_key, verify_ssl=verify_ssl
        )

        if is_first_run:
            output_message, result_value, status = start_operation(
                siemplify=siemplify,
                servicedesk_manager=servicedesk_manager,
                mark_first_response=mark_first_response,
                add_to_linked_requests=add_to_linked_requests,
                request_id=request_id,
                show_to_requester=show_to_requester,
                notify_technician=notify_technician,
                note=note,
            )
        else:
            output_message, result_value, status = query_operation_status(
                siemplify=siemplify,
                servicedesk_manager=servicedesk_manager,
                request_id=request_id,
            )

    except Exception as e:
        output_message = (
            f"Error executing action {ADD_NOTE_AND_WAIT_ACTION}. Reason: {e}"
        )
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(e)
        status = EXECUTION_STATE_FAILED
        result_value = False

    siemplify.LOGGER.info(f"----------------- {mode} - Finished -----------------")
    siemplify.LOGGER.info(
        f"\n  status: {status}\n  result_value: {result_value}\n  output_message: {output_message}"
    )

    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    is_first_run = len(sys.argv) < 3 or sys.argv[2] == "True"
    main(is_first_run)
