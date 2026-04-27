from __future__ import annotations
from soar_sdk.SiemplifyUtils import output_handler, convert_dict_to_json_result_dict
from soar_sdk.SiemplifyAction import SiemplifyAction
from ..core.BlueLivManager import BlueLivManager
from TIPCommon import extract_configuration_param, extract_action_param, construct_csv
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from ..core.consts import INTEGRATION_NAME, LIST_ENTITY_THREATS


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = LIST_ENTITY_THREATS
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
        param_name="User Name",
        is_mandatory=True,
        print_value=True,
    )
    password = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Password",
        is_mandatory=True,
        print_value=False,
    )
    organization_id = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Organization ID",
        is_mandatory=True,
        print_value=True,
    )
    verify_ssl = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Verify SSL",
        default_value=False,
        input_type=bool,
        is_mandatory=True,
    )

    status = EXECUTION_STATE_COMPLETED
    result_value = True
    output_message = ""
    json_result = {}
    successful_entities = []
    failed_entities = []
    successful_endpoints = []

    try:
        siemplify.LOGGER.info("----------------- Main - Started -----------------")

        label_filter = extract_action_param(
            siemplify,
            param_name="Label Filter",
            is_mandatory=False,
            print_value=True,
            default_value=None,
            input_type=str,
        )
        module_filter = extract_action_param(
            siemplify,
            param_name="Module Filter",
            is_mandatory=False,
            print_value=True,
            default_value=None,
            input_type=str,
        )

        limit = extract_action_param(
            siemplify,
            param_name="Max Threats To Return",
            default_value=50,
            is_mandatory=False,
            print_value=True,
            input_type=int,
        )

        if limit < 1:
            siemplify.LOGGER.error('"Max Threats To Return" must be greater than 0.')
            raise Exception('"Max Threats To Return" must be greater than 0.')

        blueliv_manager = BlueLivManager(
            api_root=api_root,
            username=username,
            password=password,
            organization_id=organization_id,
            verify_ssl=verify_ssl,
        )

        for entity in siemplify.target_entities:
            siemplify.LOGGER.info(f"Started processing entity: {entity.identifier}")
            try:
                entity_details = blueliv_manager.get_entity_data(
                    entity_id=entity.identifier,
                    label_filter=label_filter,
                    module_filter=module_filter,
                )

            except Exception as e:
                failed_entities.append(entity)
                siemplify.LOGGER.info(
                    f"Failed processing entity {entity.identifier}. Reason: {e}"
                )
                continue

            if entity_details:
                entity_details_list = [
                    entity_detail.to_csv() for entity_detail in entity_details
                ]
                json_result[entity.identifier] = (
                    entity_details_list[:limit] if limit else entity_details_list
                )
                successful_entities.append(entity)

                entity_table_list = [
                    entity_detail.to_table() for entity_detail in entity_details
                ]
                entity_table_list = (
                    entity_table_list[:limit] if limit else entity_table_list
                )

                siemplify.result.add_entity_table(
                    entity.identifier, construct_csv(entity_table_list)
                )

            else:
                failed_entities.append(entity)

            siemplify.LOGGER.info(f"Finished processing entity {entity.identifier}")

        if successful_entities:
            siemplify.result.add_result_json(
                convert_dict_to_json_result_dict(json_result)
            )

            siemplify.update_entities(successful_entities)
            output_message += "Successfully listed available threats to the following entities in {}: \n{}".format(
                INTEGRATION_NAME,
                "\n".join([entity.identifier for entity in successful_entities]),
            )

        if failed_entities:
            output_message += "\nNo related threats were found to the following entities in {}: \n{}".format(
                INTEGRATION_NAME,
                "\n".join([entity.identifier for entity in failed_entities]),
            )

        if not successful_entities:
            result_value = False
            output_message = f"No related threats were found to the provided entities in {INTEGRATION_NAME}."

    except Exception as e:
        output_message += f"Error executing action {LIST_ENTITY_THREATS}. Reason: {e}"
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
