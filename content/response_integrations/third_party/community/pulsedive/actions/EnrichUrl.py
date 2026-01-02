from __future__ import annotations

from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyDataModel import EntityTypes
from soar_sdk.SiemplifyUtils import convert_dict_to_json_result_dict, output_handler
from TIPCommon import construct_csv, extract_action_param, extract_configuration_param

from ..core.constants import (
    DEFAULT_COMMENTS_COUNT,
    ENRICH_URL_SCRIPT_NAME,
    INTEGRATION_NAME,
    PROVIDER_NAME,
    RISK_NAME,
    RISK_SCORE,
)
from ..core.exceptions import ForceRaiseException
from ..core.PulsediveManager import PulsediveManager
from ..core.UtilsManager import get_entity_original_identifier


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = ENRICH_URL_SCRIPT_NAME

    siemplify.LOGGER.info("----------------- Main - Param Init -----------------")

    api_root = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="API Root",
    )
    api_key = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="API Key",
    )
    verify_ssl = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Verify SSL",
        default_value=True,
        input_type=bool,
    )

    retrieve_comments = extract_action_param(
        siemplify,
        param_name="Retrieve Comments",
        is_mandatory=False,
        input_type=bool,
    )
    max_returned_comments = extract_action_param(
        siemplify,
        param_name="Max Comments To Return",
        is_mandatory=False,
        input_type=int,
        default_value=DEFAULT_COMMENTS_COUNT,
    )
    only_suspicious_insight = extract_action_param(
        siemplify,
        param_name="Only Suspicious Entity Insight",
        is_mandatory=False,
        input_type=bool,
        default_value=False,
    )
    threshold = extract_action_param(
        siemplify,
        param_name="Threshold",
        is_mandatory=True,
        print_value=True,
    )

    siemplify.LOGGER.info("----------------- Main - Started -----------------")

    successful_entities = []
    failed_entities = []
    global_is_risky = False

    status = EXECUTION_STATE_COMPLETED
    json_results = {}
    result_value = "false"
    output_message = ""

    suitable_entities = [
        entity
        for entity in siemplify.target_entities
        if entity.entity_type == EntityTypes.URL
    ]
    result_value, output_message = False, ""

    try:
        manager = PulsediveManager(
            api_root=api_root,
            api_key=api_key,
            verify_ssl=verify_ssl,
        )

        for entity in suitable_entities:
            siemplify.LOGGER.info(
                f"Started processing entity: {get_entity_original_identifier(entity)}",
            )

            try:
                identifier = get_entity_original_identifier(entity)
                is_risky = False
                url_data = manager.get_indicator_data(
                    indicator=identifier,
                    retrieve_comments=retrieve_comments,
                    comment_limit=max_returned_comments,
                )

                if int(RISK_SCORE.get(url_data.threshold)) >= int(
                    RISK_SCORE.get(RISK_NAME.get(threshold)),
                ):
                    is_risky = True
                    entity.is_suspicious = True
                    global_is_risky = True

                # Enrich entity
                enrichment_data = url_data.to_enrichment_data()
                entity.additional_properties.update(enrichment_data)

                # Fill json with every entity data
                json_results[get_entity_original_identifier(entity)] = url_data.to_json(
                    comments=url_data.comments,
                )

                # Create case wall table for comments
                if url_data.comments:
                    comments_table = construct_csv(
                        [comment.to_table() for comment in url_data.comments],
                    )
                    siemplify.result.add_data_table(
                        title=f"Comments: {get_entity_original_identifier(entity)}",
                        data_table=comments_table,
                    )

                if not only_suspicious_insight or (
                    only_suspicious_insight and is_risky
                ):
                    siemplify.add_entity_insight(
                        entity,
                        url_data.to_insight(threshold),
                        triggered_by=INTEGRATION_NAME,
                    )

                entity.is_enriched = True
                successful_entities.append(entity)
                siemplify.LOGGER.info(
                    f"Finished processing entity {get_entity_original_identifier(entity)}",
                )

            except Exception as e:
                if isinstance(e, ForceRaiseException):
                    raise
                failed_entities.append(get_entity_original_identifier(entity))
                siemplify.LOGGER.error(
                    f"An error occurred on entity {get_entity_original_identifier(entity)}",
                )
                siemplify.LOGGER.exception(e)

        if successful_entities:
            output_message += f"Successfully enriched the following URLs using {PROVIDER_NAME}: \n {', '.join([get_entity_original_identifier(entity) for entity in successful_entities])} \n"
            siemplify.update_entities(successful_entities)

        if failed_entities:
            output_message += f"Action wasn’t able to enrich the following URLs using {PROVIDER_NAME}: \n {', '.join(failed_entities)} \n"

        if not successful_entities:
            output_message = "No URLs were enriched"
            result_value = False

        # Main JSON result
        if json_results:
            result = {
                "results": convert_dict_to_json_result_dict(json_results),
                "is_risky": global_is_risky,
            }
            siemplify.result.add_result_json(result)

    except Exception as err:
        output_message = f"Error executing action “Enrich URL”. Reason: {err}"
        result_value = False
        status = EXECUTION_STATE_FAILED
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(err)

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(f"Status: {status}:")
    siemplify.LOGGER.info(f"Result Value: {result_value}")
    siemplify.LOGGER.info(f"Output Message: {output_message}")
    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()
