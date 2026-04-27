from __future__ import annotations
from soar_sdk.SiemplifyAction import SiemplifyAction
from ..core.McAfeeMvisionEPOManager import McAfeeMvisionEPOManager
from soar_sdk.SiemplifyUtils import output_handler
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from TIPCommon import extract_configuration_param, extract_action_param
from ..core.constants import ADD_TAG_SCRIPT_NAME, INTEGRATION_NAME
from ..core.exceptions import TagNotFoundException, EndpointNotFoundException
from soar_sdk.SiemplifyDataModel import EntityTypes


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = ADD_TAG_SCRIPT_NAME
    siemplify.LOGGER.info("----------------- Main - Param Init -----------------")

    # Configuration
    api_root = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="API Root",
        is_mandatory=True,
    )
    client_id = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Client ID",
        is_mandatory=True,
    )
    client_secret = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Client Secret",
        is_mandatory=True,
    )
    verify_ssl = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Verify SSL",
        default_value=True,
        input_type=bool,
    )

    scopes = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Scopes",
        is_mandatory=True,
    )

    group_name = extract_configuration_param(
        siemplify, provider_name=INTEGRATION_NAME, param_name="Group Name"
    )

    # Parameters
    tag_name = extract_action_param(siemplify, param_name="Tag Name", is_mandatory=True)

    siemplify.LOGGER.info("----------------- Main - Started -----------------")
    status = EXECUTION_STATE_COMPLETED
    result_value = True
    enriched_entities = []
    output_message = ""
    failed_entities = []
    suitable_entities = [
        entity
        for entity in siemplify.target_entities
        if entity.entity_type == EntityTypes.ADDRESS
        or entity.entity_type == EntityTypes.HOSTNAME
    ]
    try:
        manager = McAfeeMvisionEPOManager(
            api_root,
            client_id,
            client_secret,
            scopes,
            group_name,
            verify_ssl,
            siemplify.LOGGER,
        )
        tag = manager.find_tag_or_fail(tag_name)

        for entity in suitable_entities:
            try:
                siemplify.LOGGER.info(
                    f"\n\nStarted processing entity: {entity.identifier}"
                )

                device = manager.find_entity_or_fail(
                    entity.identifier,
                    is_host=entity.entity_type == EntityTypes.HOSTNAME,
                )
                manager.add_or_remove_tag(device, tag)
                enriched_entities.append(entity)
                msg = f"Successfully added tag {tag_name} to {entity.identifier}"
                siemplify.LOGGER.info(msg)
                output_message += f"\n\n{msg}"
            except EndpointNotFoundException:
                failed_entities.append(entity)
                msg = f"Action wasn't able to add tag '{tag_name}' to {entity.identifier}. Reason: Endpoint {entity.identifier} was not found in McAfee Mvision ePO."
                siemplify.LOGGER.error(msg)
                output_message += f"\n\n{msg}"
            except Exception as e:
                msg = f"Action wasn't able to add tag '{tag_name}' to {entity.identifier}."
                output_message += f"\n\n{msg}"
                failed_entities.append(entity)
                siemplify.LOGGER.error(msg)
                siemplify.LOGGER.exception(e)
            siemplify.LOGGER.info(f"Finished processing entity: {entity.identifier}")

        if not enriched_entities:
            siemplify.LOGGER.info("\n No entities where processed.")
            output_message = "No entities where processed."
            result_value = False

    except TagNotFoundException as e:
        result_value = False
        output_message = f"Action wasn't able to add tag '{tag_name}'. Reason: Tag '{tag_name}' was not found in McAfee Mvision ePO. Please check for any spelling mistakes. In order to get the list of available tags execute action 'List Tags'"
        siemplify.LOGGER.error(output_message)

    except Exception as e:
        output_message = f"Error executing action '{ADD_TAG_SCRIPT_NAME}'. Reason: {e}"
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
