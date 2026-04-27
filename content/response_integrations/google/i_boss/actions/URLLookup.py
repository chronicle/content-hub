from __future__ import annotations
from soar_sdk.SiemplifyAction import SiemplifyAction
from ..core.IBossManager import IBossManager
from soar_sdk.SiemplifyUtils import output_handler, convert_dict_to_json_result_dict
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from TIPCommon import extract_configuration_param, extract_action_param
from ..core.constants import URLLOOKUP_SCRIPT_NAME, INTEGRATION_NAME, ENRICHMENT_PREFIX
from soar_sdk.SiemplifyDataModel import EntityTypes


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = URLLOOKUP_SCRIPT_NAME
    siemplify.LOGGER.info("----------------- Main - Param Init -----------------")

    cloud_api_root = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Cloud API Root",
        is_mandatory=True,
    )
    account_api_root = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Account API Root",
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
    verify_ssl = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Verify SSL",
        default_value=True,
        input_type=bool,
    )

    group_id = extract_action_param(
        siemplify, param_name="Group ID", is_mandatory=False, print_value=True
    )

    siemplify.LOGGER.info("----------------- Main - Started -----------------")
    status = EXECUTION_STATE_COMPLETED
    result_value = True
    output_message = ""
    successful_entities = []
    failed_entities = []
    json_results = {}
    suitable_entities = [
        entity
        for entity in siemplify.target_entities
        if entity.entity_type == EntityTypes.URL
        or entity.entity_type == EntityTypes.HOSTNAME
    ]

    try:
        manager = IBossManager(
            cloud_api_root,
            account_api_root,
            username,
            password,
            verify_ssl,
            siemplify.LOGGER,
        )
        for entity in suitable_entities:
            try:
                siemplify.LOGGER.info(f"Started processing entity: {entity.identifier}")

                url_lookup_data = manager.url_lookup(entity.identifier, group_id)

                if url_lookup_data:
                    enrichment_data = url_lookup_data.to_enrichment_data(
                        prefix=ENRICHMENT_PREFIX, group_id=group_id
                    )
                    entity.additional_properties.update(enrichment_data)
                    entity.is_enriched = True

                    json_results[entity.identifier] = url_lookup_data.to_json()
                    successful_entities.append(entity)

                else:
                    failed_entities.append(entity)

                siemplify.LOGGER.info(f"Finished processing entity {entity.identifier}")

            except Exception as e:
                failed_entities.append(entity)

        if failed_entities:
            output_message += (
                "Action was not able to retrieve information about the following "
                "entities: \n {}"
            ).format(
                "\n".join([entity.identifier for entity in failed_entities])
            )

        if successful_entities:
            output_message += (
                "\nSuccessfully retrieved information about the following "
                "entities \n {}"
            ).format(
                "\n".join([entity.identifier for entity in successful_entities])
            )
            siemplify.result.add_result_json(
                convert_dict_to_json_result_dict(json_results)
            )
            siemplify.update_entities(successful_entities)
        else:
            output_message = "No information was retrieved about entities."
            siemplify.LOGGER.info(output_message)
            result_value = False

    except Exception as e:
        output_message = (
            f"Error executing action '{URLLOOKUP_SCRIPT_NAME}'. Reason: {e}"
        )
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(e)
        status = EXECUTION_STATE_FAILED
        result_value = False

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(
        f"\n  status: {status}\n  "
        f"result_value: {result_value}\n  "
        f"output_message: {output_message}"
    )

    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()
