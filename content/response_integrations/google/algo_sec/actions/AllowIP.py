from __future__ import annotations
from soar_sdk.SiemplifyUtils import output_handler
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyDataModel import EntityTypes
from TIPCommon import extract_configuration_param, extract_action_param
from ..core.AlgoSecManager import AlgoSecManager
from ..core.constants import (
    SLEEP_TIME,
    INTEGRATION_NAME,
    INTEGRATION_DISPLAY_NAME,
    ALLOW_IP_SCRIPT_NAME,
    ALLOW_DEAULT_SUBJECT,
)
from ..core.UtilsManager import convert_comma_separated_to_list
import time

SUPPORTED_ENTITY_TYPES = [EntityTypes.ADDRESS]
LINK_TITLE = "Change Request Link"


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = ALLOW_IP_SCRIPT_NAME
    siemplify.LOGGER.info("----------------- Main - Param Init -----------------")

    api_root = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="API Root",
        is_mandatory=True,
        print_value=True,
    )
    username = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Username",
        is_mandatory=True,
        print_value=True,
    )
    password = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Password",
        is_mandatory=True,
    )
    verify_ssl = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Verify SSL",
        input_type=bool,
        is_mandatory=True,
        print_value=True,
    )

    # Action parameters
    template = extract_action_param(
        siemplify, param_name="Template", is_mandatory=True, print_value=True
    )
    source = extract_action_param(
        siemplify, param_name="Source", is_mandatory=True, print_value=True
    )
    service = extract_action_param(
        siemplify, param_name="Service", is_mandatory=True, print_value=True
    )
    subject = extract_action_param(
        siemplify,
        param_name="Subject",
        print_value=True,
        default_value=ALLOW_DEAULT_SUBJECT,
    )
    owner = extract_action_param(siemplify, param_name="Owner", print_value=True)
    due_date = extract_action_param(siemplify, param_name="Due Date", print_value=True)
    expiration_date = extract_action_param(
        siemplify, param_name="Expiration Date", print_value=True
    )
    custom_fields = extract_action_param(
        siemplify, param_name="Custom Fields", print_value=True
    )

    siemplify.LOGGER.info("----------------- Main - Started -----------------")

    source = [src.lower() for src in convert_comma_separated_to_list(source)]
    service = [srv.lower() for srv in convert_comma_separated_to_list(service)]

    result = True
    status = EXECUTION_STATE_COMPLETED
    suitable_entities = [
        entity
        for entity in siemplify.target_entities
        if entity.entity_type in SUPPORTED_ENTITY_TYPES
    ]
    ip_addresses = [entity.identifier for entity in suitable_entities]

    try:
        manager = AlgoSecManager(
            api_root=api_root,
            username=username,
            password=password,
            verify_ssl=verify_ssl,
            siemplify_logger=siemplify.LOGGER,
        )

        request_obj = manager.create_request(
            ip_addresses=ip_addresses,
            template=template,
            source=source,
            service=service,
            subject=subject,
            owner=owner,
            due_date=due_date,
            expiration_date=expiration_date,
            custom_fields=custom_fields,
            is_block=False,
        )

        time.sleep(SLEEP_TIME)
        result_obj = manager.get_request_details(request_id=request_obj.id)

        siemplify.result.add_result_json(result_obj.to_json())
        siemplify.result.add_link(LINK_TITLE, request_obj.redirect_url)
        output_message = (
            f"Successfully created a traffic change request to allow traffic to the provided entities "
            f"in {INTEGRATION_DISPLAY_NAME}"
        )

    except Exception as e:
        siemplify.LOGGER.error(
            f"General error performing action {ALLOW_IP_SCRIPT_NAME}"
        )
        siemplify.LOGGER.exception(e)
        result = False
        status = EXECUTION_STATE_FAILED
        output_message = f"Error executing action {ALLOW_IP_SCRIPT_NAME}. Reason: {e}"

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(f"Output Message: {output_message}")
    siemplify.LOGGER.info(f"Result: {result}")
    siemplify.LOGGER.info(f"Status: {status}")

    siemplify.end(output_message, result, status)


if __name__ == "__main__":
    main()
