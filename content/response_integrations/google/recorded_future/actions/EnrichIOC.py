from __future__ import annotations
from soar_sdk.SiemplifyAction import SiemplifyAction
from ..core.RecordedFutureManager import RecordedFutureManager
from soar_sdk.SiemplifyDataModel import EntityTypes
from soar_sdk.SiemplifyUtils import output_handler, convert_dict_to_json_result_dict
from TIPCommon import extract_configuration_param, extract_action_param
from ..core.constants import PROVIDER_NAME, ENRICH_IOC_SCRIPT_NAME
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from ..core.exceptions import RecordedFutureUnauthorizedError

SUPPORTED_ENTITIES = [
    EntityTypes.HOSTNAME,
    EntityTypes.CVE,
    EntityTypes.FILEHASH,
    EntityTypes.ADDRESS,
    EntityTypes.URL,
]


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = ENRICH_IOC_SCRIPT_NAME
    siemplify.LOGGER.info("----------------- Main - Started -----------------")

    api_url = extract_configuration_param(
        siemplify, provider_name=PROVIDER_NAME, param_name="ApiUrl"
    )
    api_key = extract_configuration_param(
        siemplify, provider_name=PROVIDER_NAME, param_name="ApiKey"
    )
    verify_ssl = extract_configuration_param(
        siemplify,
        provider_name=PROVIDER_NAME,
        param_name="Verify SSL",
        default_value=False,
        input_type=bool,
    )

    threshold = extract_action_param(
        siemplify, param_name="Risk Score Threshold", is_mandatory=True, input_type=int
    )

    result_value = True
    output_message = ""
    status = EXECUTION_STATE_COMPLETED

    json_results = {}
    successful_entities = []
    failed_entities = []

    filtered_entities = [
        entity
        for entity in siemplify.target_entities
        if entity.entity_type in SUPPORTED_ENTITIES
    ]

    try:
        recorded_future_manager = RecordedFutureManager(
            api_url, api_key, verify_ssl=verify_ssl
        )
        entity_common_objects = recorded_future_manager.get_ioc_related_entity_objects(
            filtered_entities
        )

        for entity in filtered_entities:
            entity_to_lower = entity.identifier.lower()
            siemplify.LOGGER.info(f"\n\nStarted processing entity: {entity_to_lower}")

            if entity_common_objects.get(entity_to_lower):
                successful_entities.append(entity)
                entity.additional_properties.update(
                    entity_common_objects.get(entity_to_lower).to_enrichment_data()
                )

                if (
                    int(entity_common_objects.get(entity_to_lower).risk_score)
                    > threshold
                ):
                    entity.is_suspicious = True

                entity.is_enriched = True
                json_results[entity_to_lower] = entity_common_objects.get(
                    entity_to_lower
                ).to_json()
                siemplify.LOGGER.info(
                    f"Successfully enriched entity: {entity_to_lower}"
                )
            else:
                failed_entities.append(entity)
                siemplify.LOGGER.error(
                    f"Action was not able to enrich the following entity: {entity_to_lower}"
                )

            siemplify.LOGGER.info(f"Finished processing entity: {entity_to_lower}")

        if successful_entities:
            siemplify.update_entities(successful_entities)
            siemplify.result.add_result_json(
                convert_dict_to_json_result_dict(json_results)
            )
            output_message += "\nSuccessfully enriched the following entities in Recorded Future:\n{}".format(
                "\n".join([entity.identifier for entity in successful_entities])
            )

        if failed_entities:
            output_message += "\nAction was not able to enrich the following entities in Recorded Future:\n{}".format(
                "\n".join([entity.identifier for entity in failed_entities])
            )

        if not successful_entities:
            output_message += "\nNo entities were enriched."
            result_value = False

    except RecordedFutureUnauthorizedError as e:
        result_value = False
        status = EXECUTION_STATE_FAILED
        output_message = (
            f"Unauthorized - please check your API token and try again. {e}"
        )
    except Exception as e:
        siemplify.LOGGER.error(
            f"General error performing action {ENRICH_IOC_SCRIPT_NAME}"
        )
        siemplify.LOGGER.exception(e)
        result_value = False
        status = EXECUTION_STATE_FAILED
        output_message = (
            f'Error executing action "{ENRICH_IOC_SCRIPT_NAME}". Reason: {e}'
        )

    siemplify.LOGGER.info("\n----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(f"Output Message: {output_message}")
    siemplify.LOGGER.info(f"Result: {result_value}")
    siemplify.LOGGER.info(f"Status: {status}")
    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()
