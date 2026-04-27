from __future__ import annotations
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler

from TIPCommon.extraction import extract_configuration_param, extract_action_param

from ..core.constants import INTEGRATION_NAME, UPDATE_REQUEST_ACTION, UPDATE_REQUEST_TYPE
from ..core.ServiceDeskPlusManagerV3 import ServiceDeskPlusManagerV3
from ..core.utils import string_to_multi_value


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = UPDATE_REQUEST_ACTION
    siemplify.LOGGER.info("----------------- Main - Param Init -----------------")

    api_root = extract_configuration_param(
        siemplify, provider_name=INTEGRATION_NAME, param_name="Api Root"
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
    )

    # Action Parameters
    request_id = extract_action_param(
        siemplify, param_name="Request ID", is_mandatory=True, input_type=str
    )
    subject = extract_action_param(
        siemplify, param_name="Subject", is_mandatory=False, input_type=str
    )
    requester = extract_action_param(
        siemplify, param_name="Requester", is_mandatory=False, input_type=str
    )
    description = extract_action_param(
        siemplify, param_name="Description", is_mandatory=False, input_type=str
    )
    assets = string_to_multi_value(
        extract_action_param(siemplify, param_name="Assets", print_value=True)
    )
    request_status = extract_action_param(
        siemplify, param_name="Status", is_mandatory=False, input_type=str
    )
    technician = extract_action_param(
        siemplify, param_name="Technician", is_mandatory=False, input_type=str
    )
    priority = extract_action_param(
        siemplify, param_name="Priority", is_mandatory=False, input_type=str
    )
    urgency = extract_action_param(
        siemplify, param_name="Urgency", is_mandatory=False, input_type=str
    )
    category = extract_action_param(
        siemplify, param_name="Category", is_mandatory=False, input_type=str
    )
    request_template = extract_action_param(
        siemplify, param_name="Request Template", is_mandatory=False, input_type=str
    )
    request_type = extract_action_param(
        siemplify, param_name="Request Type", is_mandatory=False, input_type=str
    )
    due_by_time = extract_action_param(
        siemplify, param_name="Due By Time (ms)", is_mandatory=False, input_type=int
    )
    mode = extract_action_param(
        siemplify, param_name="Mode", is_mandatory=False, input_type=str
    )
    level = extract_action_param(
        siemplify, param_name="Level", is_mandatory=False, input_type=str
    )
    site = extract_action_param(
        siemplify, param_name="Site", is_mandatory=False, input_type=str
    )
    group = extract_action_param(
        siemplify, param_name="Group", is_mandatory=False, input_type=str
    )
    impact = extract_action_param(
        siemplify, param_name="Impact", is_mandatory=False, input_type=str
    )

    siemplify.LOGGER.info("----------------- Main - Started -----------------")
    status = EXECUTION_STATE_COMPLETED
    result_value = True

    try:

        servicedesk_manager = ServiceDeskPlusManagerV3(
            api_root=api_root, api_key=api_key, verify_ssl=verify_ssl
        )
        result = servicedesk_manager.request(
            action_type=UPDATE_REQUEST_TYPE,
            request_id=request_id,
            description=description,
            subject=subject,
            requester=requester,
            status=request_status,
            technician=technician,
            priority=priority,
            urgency=urgency,
            category=category,
            request_template=request_template,
            request_type=request_type,
            due_by_time=due_by_time,
            mode=mode,
            level=level,
            assets=assets,
            site=site,
            group=group,
            impact=impact,
        )

        output_message = (
            f"Successfully updated ServiceDesk Plus request with ID: {request_id}"
        )

        siemplify.result.add_result_json(result.to_json())

    except Exception as e:
        output_message = f"Error executing action {UPDATE_REQUEST_ACTION}. Reason: {e}"
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
