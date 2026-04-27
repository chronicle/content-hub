from __future__ import annotations
from soar_sdk.ScriptResult import (
    EXECUTION_STATE_COMPLETED,
    EXECUTION_STATE_FAILED,
    EXECUTION_STATE_INPROGRESS,
)
from soar_sdk.SiemplifyUtils import output_handler
from soar_sdk.SiemplifyAction import SiemplifyAction

from TIPCommon.extraction import extract_configuration_param, extract_action_param
from TIPCommon.transformation import dict_to_flat

from ..core.constants import INTEGRATION_NAME, WAIT_FOR_FIELD_UPDATE_ACTION
from ..core.ServiceDeskPlusManagerV3 import ServiceDeskPlusManagerV3


def compare_request_statuses(
    siemplify, servicedesk_manager, request_id, values, field_name
):
    """
    Function that compares the request fields
    :param siemplify: SiemplifyAction object.
    :param servicedesk_manager: ServiceDesk manager object.
    :param request_id: Request ID
    :param values: Values of the field to watch
    :param field_name: Field to track
    :return: {output message, json result, execution_state}
    """

    try:
        result = servicedesk_manager.get_request(request_id=request_id)
        # In order to be able to get particular value from nested JSON, the original JSON is transformed using dict_to_flat function, which puts together the keys with '_'
        field_name_underscore = field_name.replace(".", "_")
        field_value = str(dict_to_flat(result.orig_request).get(field_name_underscore))

        if field_value:
            for value in values:
                if value != field_value:
                    status = EXECUTION_STATE_INPROGRESS
                    result_value = True
                    output_message = f"Field {field_name} of the request with ID: {request_id} was not updated. Current value of this field is {field_value}. Will check again later...."

                else:
                    status = EXECUTION_STATE_COMPLETED
                    result_value = True
                    output_message = f"Field {field_name} of the request with ID: {request_id} was changed, the current value of this field is: {field_value}."
                    siemplify.result.add_result_json(result.to_json())

        else:
            status = EXECUTION_STATE_COMPLETED
            result_value = False
            output_message = f"Unable to get field: {field_name} from the request with this ID: {request_id}"

    except Exception as e:
        output_message = (
            f"Error executing action {WAIT_FOR_FIELD_UPDATE_ACTION}. Reason: {e}"
        )
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(e)
        status = EXECUTION_STATE_FAILED
        result_value = False

    return output_message, result_value, status


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = WAIT_FOR_FIELD_UPDATE_ACTION
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
    field_name = extract_action_param(
        siemplify,
        param_name="Field Name",
        is_mandatory=True,
        input_type=str,
        print_value=True,
    )

    siemplify.LOGGER.info("----------------- Main - Started -----------------")
    try:

        servicedesk_manager = ServiceDeskPlusManagerV3(
            api_root=api_root, api_key=api_key, verify_ssl=verify_ssl
        )
        output_message, result_value, status = compare_request_statuses(
            siemplify, servicedesk_manager, request_id, values, field_name
        )

    except Exception as e:
        output_message = (
            f"Error executing action {WAIT_FOR_FIELD_UPDATE_ACTION}. Reason: {e}"
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
