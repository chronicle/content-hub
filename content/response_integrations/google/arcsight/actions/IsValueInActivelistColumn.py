from __future__ import annotations
from soar_sdk.SiemplifyUtils import output_handler
from ..core.ArcsightManager import ArcsightManager
from soar_sdk.SiemplifyAction import SiemplifyAction
from TIPCommon import extract_configuration_param, extract_action_param
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from ..core.constants import IS_VALUE_IN_ACTIVELIST_COLUMN_SCRIPT_NAME, INTEGRATION_NAME
from ..core.exceptions import ColumnNotFoundException
from ..core.UtilsManager import get_entity_original_identifier


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = IS_VALUE_IN_ACTIVELIST_COLUMN_SCRIPT_NAME
    siemplify.LOGGER.info("----------------- Main - Param Init -----------------")

    api_root = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Api Root",
        is_mandatory=True,
    )
    username = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Username",
        is_mandatory=True,
    )
    password = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Password",
        is_mandatory=True,
    )
    ca_certificate_file = extract_configuration_param(
        siemplify, provider_name=INTEGRATION_NAME, param_name="CA Certificate File"
    )
    verify_ssl = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Verify SSL",
        default_value=False,
        input_type=bool,
    )

    list_uuid = extract_action_param(
        siemplify, param_name="Active list UUID", print_value=True
    )
    column_name = extract_action_param(
        siemplify, param_name="Column name", print_value=True, is_mandatory=True
    )
    list_name = extract_action_param(
        siemplify, param_name="Active list name", print_value=True
    )

    siemplify.LOGGER.info("----------------- Main - Started -----------------")
    # Default output
    result_value = True
    output_message = ""
    status = EXECUTION_STATE_COMPLETED
    successful_entities, failed_entities = [], []

    try:
        fetched_by_uuid = bool(list_uuid)

        if not list_uuid and not list_name:
            raise Exception(
                "either ‘Active list UUID' or 'Active list name’ should be provided."
            )

        arcsight_manager = ArcsightManager(
            server_ip=api_root,
            username=username,
            password=password,
            verify_ssl=verify_ssl,
            ca_certificate_file=ca_certificate_file,
        )
        arcsight_manager.login()

        if not list_uuid:
            list_uuid = arcsight_manager.get_activelist_uuid(activelist_name=list_name)

        result = arcsight_manager.get_activelist_entries_by_uuid(list_uuid)

        try:
            if column_name not in result.columns:
                raise ColumnNotFoundException(
                    f"Invalid column was provided. Available columns: {', '.join(result.columns)}"
                )

            result_json = result.to_json(map_columns=True)
            values_for_given_column_name = [item[column_name] for item in result_json]

            for entity in siemplify.target_entities:
                siemplify.LOGGER.info(
                    f"Started processing entity: {get_entity_original_identifier(entity)}"
                )

                if result.enries_count:
                    if (
                        get_entity_original_identifier(entity)
                        in values_for_given_column_name
                    ):
                        entity.additional_properties["IsInActivelist"] = True
                        successful_entities.append(entity)
                    else:
                        failed_entities.append(entity)

                siemplify.LOGGER.info(
                    f"Finished processing entity: {get_entity_original_identifier(entity)}"
                )
            if successful_entities and result_json:
                filtered_json = [
                    item
                    for item in result_json
                    for entity in successful_entities
                    if get_entity_original_identifier(entity) == item[column_name]
                ]
                siemplify.result.add_result_json(filtered_json)
            siemplify.update_entities(successful_entities)

        except ColumnNotFoundException:
            raise
        except Exception as err:
            siemplify.LOGGER.error(output_message)
            siemplify.LOGGER.exception(err)

        if successful_entities:
            output_message += "Successfully found the following entities in active list {} from {}:\n {} \n".format(
                f"with UUID {list_uuid}" if fetched_by_uuid else list_name,
                INTEGRATION_NAME,
                ", ".join(
                    [
                        get_entity_original_identifier(entity)
                        for entity in successful_entities
                    ]
                ),
            )

        if failed_entities:
            output_message += "Action didn’t find the following entities in active list {} from {}:\n {} \n".format(
                f"with UUID {list_uuid}" if fetched_by_uuid else list_name,
                INTEGRATION_NAME,
                ", ".join(
                    [
                        get_entity_original_identifier(entity)
                        for entity in failed_entities
                    ]
                ),
            )

        if not successful_entities:
            output_message = "No entities were found in active list {} from {}".format(
                f"with UUID {list_uuid}" if fetched_by_uuid else list_name,
                INTEGRATION_NAME,
            )
            result_value = False

        arcsight_manager.logout()
    except Exception as e:
        output_message = f"Error executing action {IS_VALUE_IN_ACTIVELIST_COLUMN_SCRIPT_NAME}. Reason: {e}"
        status = EXECUTION_STATE_FAILED
        result_value = False
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(e)

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(
        f"\n  status: {status}\n  is_success: {result_value}\n  output_message: {output_message}"
    )
    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()
