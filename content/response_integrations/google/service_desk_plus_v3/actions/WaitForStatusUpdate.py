from __future__ import annotations
from soar_sdk.ScriptResult import (
    EXECUTION_STATE_COMPLETED,
    EXECUTION_STATE_FAILED,
    EXECUTION_STATE_INPROGRESS,
)
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler

from TIPCommon.extraction import extract_configuration_param, extract_action_param

from ..core.constants import INTEGRATION_NAME, WAIT_FOR_STATUS_UPDATE_ACTION
from ..core.ServiceDeskPlusManagerV3 import ServiceDeskPlusManagerV3


def compare_request_statuses(siemplify, servicedesk_manager, request_id, values):
    """
    Function that compares the request statuses
    :param siemplify: SiemplifyAction object.
    :param servicedesk_manager: ServiceDesk manager object.
    :param request_id: Request ID
    :param values: Status values to check
    :return: {output message, json result, execution_state}
    """

    try:
        result = servicedesk_manager.get_request(request_id=request_id)

        if result.status:
            for value in values:
                if value != result.status:
                    status = EXECUTION_STATE_INPROGRESS
                    result_value = True
                    output_message = f"Status of the request with ID: {request_id} was not updated. Will check again later...."

                else:
                    status = EXECUTION_STATE_COMPLETED
                    result_value = True
                    output_message = f"Status of the request with ID: {request_id} was changed, the current status is: {result.status}."
                    siemplify.result.add_result_json(result.to_json())

        else:
            status = EXECUTION_STATE_COMPLETED
            result_value = False
            output_message = (
                f"Unable to get status of the request with this ID: {request_id}"
            )

    except Exception as e:
        output_message = (
            f"Error executing action {WAIT_FOR_STATUS_UPDATE_ACTION}. Reason: {e}"
        )
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(e)
        status = EXECUTION_STATE_FAILED
        result_value = False

    return output_message, result_value, status


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = WAIT_FOR_STATUS_UPDATE_ACTION
    siemplify.LOGGER.info("----------------- Main - Param Init -----------------")

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
    request_id = extract_action_param(
        siemplify,
        param_name="Request ID",
        is_mandatory=True,
        input_type=str,
        print_value=True,
    )
    values = extract_action_param(
        siemplify,
        param_name="Values",
        is_mandatory=True,
        input_type=str,
        print_value=True,
    ).split(",")

    siemplify.LOGGER.info("----------------- Main - Started -----------------")
    try:
        servicedesk_manager = ServiceDeskPlusManagerV3(
            api_root=api_root, api_key=api_key, verify_ssl=verify_ssl
        )
        output_message, result_value, status = compare_request_statuses(
            siemplify, servicedesk_manager, request_id, values
        )

    except Exception as e:
        output_message = (
            f"Error executing action {WAIT_FOR_STATUS_UPDATE_ACTION}. Reason: {e}"
        )
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(e)
        status = EXECUTION_STATE_FAILED
        result_value = False

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(
        f"\n  status: {status}\n  result_value: {result_value}\n  output_message: {output_message}"
    )

    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()
