from __future__ import annotations
from ..core.MandiantASMManager import MandiantASMManager
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from TIPCommon import (
    extract_configuration_param,
    extract_action_param,
    convert_comma_separated_to_list,
)
from ..core.constants import INTEGRATION_NAME, GET_ASM_ENTITY_DETAILS_SCRIPT_NAME


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = GET_ASM_ENTITY_DETAILS_SCRIPT_NAME
    siemplify.LOGGER.info("----------------- Main - Param Init -----------------")

    api_root = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="API Root",
        is_mandatory=True,
        print_value=True,
    )
    access_key = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Access Key",
        remove_whitespaces=False,
    )
    secret_key = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Secret Key",
        remove_whitespaces=False,
    )
    gti_api_key = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="GTI API Key",
        remove_whitespaces=False,
    )
    project_name = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Project Name",
        print_value=True,
    )
    verify_ssl = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Verify SSL",
        input_type=bool,
        is_mandatory=True,
        print_value=True,
    )

    entity_ids = extract_action_param(
        siemplify, param_name="Entity IDs", print_value=True, is_mandatory=True
    )

    entity_ids = convert_comma_separated_to_list(entity_ids)

    siemplify.LOGGER.info("----------------- Main - Started -----------------")

    result_value = True
    status = EXECUTION_STATE_COMPLETED
    output_message = ""
    successful_entities, failed_entities, json_results = [], [], []

    try:
        manager = MandiantASMManager(
            api_root=api_root,
            access_key=access_key,
            secret_key=secret_key,
            gti_api_key=gti_api_key,
            project_name=project_name,
            verify_ssl=verify_ssl,
            siemplify_logger=siemplify.LOGGER,
        )

        for entity_id in entity_ids:
            try:
                entity_details = manager.get_asm_entity_by_id(entity_id=entity_id)

                if entity_details:
                    successful_entities.append(entity_id)
                    json_results.append(entity_details.to_json())
                else:
                    failed_entities.append(entity_id)
            except Exception as e:
                failed_entities.append(entity_id)
                siemplify.LOGGER.error(f"An error occurred on entity: {entity_id}.")
                siemplify.LOGGER.exception(e)

        if successful_entities:
            output_message += (
                f"Successfully return details for the following entities using information from "
                f"Mandiant ASM: {', '.join(successful_entities)}\n"
            )
            siemplify.result.add_result_json(json_results)

            if failed_entities:
                output_message += (
                    f"Action wasn't able to return details for the following entities using "
                    f"information from Mandiant ASM: {', '.join(failed_entities)}\n"
                )
        else:
            raise Exception(
                f"none of the provided entities were valid or found. Please check the spelling"
            )

    except Exception as e:
        result_value = False
        status = EXECUTION_STATE_FAILED
        output_message = (
            f"Error executing action {GET_ASM_ENTITY_DETAILS_SCRIPT_NAME}. Reason: {e}"
        )
        siemplify.LOGGER.exception(e)

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(
        f"\n  status: {status}\n  is_success: {result_value}\n  output_message: {output_message}"
    )
    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()
