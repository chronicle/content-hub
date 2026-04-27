from __future__ import annotations
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyDataModel import EntityTypes
from ..core.RSAManager import RSAManager
from soar_sdk.SiemplifyUtils import output_handler, convert_dict_to_json_result_dict
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from TIPCommon import extract_configuration_param, extract_action_param
from ..core.constants import INTEGRATION_NAME, ENRICH_FILE_SCRIPT_NAME, ENRICHMENT_PREFIX
from ..core.RSAExceptions import IncorrectHashTypeException


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = ENRICH_FILE_SCRIPT_NAME
    siemplify.LOGGER.info("----------------- Main - Param Init -----------------")

    # Configuration.
    ui_api_root = extract_configuration_param(
        siemplify, provider_name=INTEGRATION_NAME, param_name="Web API Root"
    )
    ui_username = extract_configuration_param(
        siemplify, provider_name=INTEGRATION_NAME, param_name="Web Username"
    )
    ui_password = extract_configuration_param(
        siemplify, provider_name=INTEGRATION_NAME, param_name="Web Password"
    )
    verify_ssl = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Verify SSL",
        default_value=True,
        input_type=bool,
        is_mandatory=True,
    )

    # Parameters
    risk_score_threshold = extract_action_param(
        siemplify, param_name="Risk Score Threshold", input_type=int
    )

    siemplify.LOGGER.info("----------------- Main - Started -----------------")
    status = EXECUTION_STATE_COMPLETED
    result_value = True
    output_message = ""
    json_results = {}
    successful_entities = []
    failed_entities = []
    suitable_entities = [
        entity
        for entity in siemplify.target_entities
        if entity.entity_type == EntityTypes.FILENAME
        or entity.entity_type == EntityTypes.FILEHASH
    ]

    try:
        rsa_manager = RSAManager(
            ui_api_root=ui_api_root,
            ui_username=ui_username,
            ui_password=ui_password,
            verify_ssl=verify_ssl,
        )

        service_object = rsa_manager.find_required_service_id()
        for entity in suitable_entities:
            siemplify.LOGGER.info(f"Started processing entity: {entity.identifier}")
            try:
                if entity.entity_type == EntityTypes.FILENAME:
                    entity_object = rsa_manager.search_for_filename(
                        service_id=service_object.id, value=entity.identifier
                    )
                else:
                    entity_object = rsa_manager.search_for_filehash(
                        service_id=service_object.id, value=entity.identifier
                    )

                if entity_object:
                    enrichment_data = entity_object.to_enrichment_data(
                        prefix=ENRICHMENT_PREFIX
                    )
                    entity.additional_properties.update(enrichment_data)
                    entity.is_enriched = True
                    if (
                        risk_score_threshold
                        and entity_object.global_risk_score > risk_score_threshold
                    ):
                        entity.is_suspicious = True

                    # JSON result
                    json_results[entity.identifier] = entity_object.to_json()
                    siemplify.LOGGER.info(
                        f"Successfully enriched the following file from RSA NetWitness: {entity.identifier}"
                    )
                    successful_entities.append(entity)
                else:
                    failed_entities.append(entity)

            except IncorrectHashTypeException as e:
                failed_entities.append(entity)
                siemplify.LOGGER.exception(e)

            siemplify.LOGGER.info(f"Finished processing entity {entity.identifier}")

        if successful_entities:
            siemplify.update_entities(successful_entities)
            siemplify.result.add_result_json(
                convert_dict_to_json_result_dict(json_results)
            )
            output_message += "Successfully enriched the following files from RSA NetWitness: {}".format(
                "\n".join([entity.identifier for entity in successful_entities])
            )

        if failed_entities:
            output_message += "\n\n Action was not able to enrich the following files from RSA NetWitness: {}".format(
                "\n".join([entity.identifier for entity in failed_entities])
            )

        if not successful_entities:
            output_message = "No entities were enriched."
            result_value = False

    except Exception as e:
        output_message = f'Error executing action "Enrich File". Reason: {e}'
        result_value = False
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(e)
        status = EXECUTION_STATE_FAILED

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(
        f"\n  status: {status}\n  is_success: {result_value}\n  output_message: {output_message}"
    )
    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()
