from __future__ import annotations
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyDataModel import EntityTypes
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyUtils import convert_dict_to_json_result_dict, output_handler

from TIPCommon import (
    add_prefix_to_dict,
    construct_csv,
    extract_action_param,
    extract_configuration_param,
)

from ..core.APIVoidManager import (
    APIVoidInvalidAPIKeyError,
    APIVoidManager,
    APIVoidManagerError,
    APIVoidNotFound,
)
from ..core.constants import (
    GET_IP_REPUTATION_SCRIPT_NAME,
    INSIGHT_MSG,
    INTEGRATION_NAME,
    LIMIT_EXCEEDED,
)


SUPPORTED_ENTITIES = [EntityTypes.ADDRESS]


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = GET_IP_REPUTATION_SCRIPT_NAME

    siemplify.LOGGER.info("---------------- Main - Param Init ----------------")

    # Configuration
    api_root = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Api Root",
        is_mandatory=True,
        input_type=str,
    )
    api_key = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Api Key",
        is_mandatory=True,
        input_type=str,
    )
    verify_ssl = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Verify SSL",
        default_value=False,
        input_type=bool,
    )

    # Parameters
    threshold = extract_action_param(
        siemplify,
        param_name="Threshold",
        is_mandatory=False,
        input_type=int,
        default_value=0,
        print_value=True,
    )
    create_insights = extract_action_param(
        siemplify, param_name="Create Insights", is_mandatory=True, input_type=bool
    )

    siemplify.LOGGER.info("----------------- Main - Started -----------------")

    result_value = "true"
    enriched_entities = []
    missing_entities = []
    failed_entities = []
    json_results = {}
    status = EXECUTION_STATE_COMPLETED

    try:
        apivoid_manager = APIVoidManager(api_root, api_key, verify_ssl=verify_ssl)

        for entity in siemplify.target_entities:
            try:
                if entity.entity_type not in SUPPORTED_ENTITIES:
                    siemplify.LOGGER.info(
                        f"Entity {entity.identifier} is of unsupported type. Skipping."
                    )
                    continue

                if entity.is_internal:
                    siemplify.LOGGER.info(
                        f"Entity {entity.identifier} is internal. Skipping."
                    )
                    continue

                siemplify.LOGGER.info(f"Started processing entity: {entity.identifier}")

                reputation_obj = apivoid_manager.get_ip_reputation(entity.identifier)
                enrichment_data = reputation_obj.as_enrichment_data()

                if create_insights and enrichment_data.get("country_code"):
                    siemplify.LOGGER.info(
                        f'Entity {entity.identifier} country code: {enrichment_data.get("country_code")}'
                    )
                    siemplify.add_entity_insight(
                        entity,
                        INSIGHT_MSG.format(enrichment_data.get("country_code")),
                        triggered_by=INTEGRATION_NAME,
                    )

                siemplify.LOGGER.info(f"Enriching entity {entity.identifier}")
                enrichment_data = add_prefix_to_dict(enrichment_data, INTEGRATION_NAME)
                entity.additional_properties.update(enrichment_data)

                if reputation_obj.get_blacklist_report():
                    siemplify.LOGGER.info(
                        f"Adding blacklist report for entity {entity.identifier}"
                    )
                    siemplify.result.add_entity_table(
                        entity.identifier,
                        construct_csv(reputation_obj.get_blacklist_report()),
                    )

                json_results[entity.identifier] = reputation_obj.as_json()

                if int(
                    reputation_obj.as_json().get("blacklists", {}).get("detections", 0)
                ) > int(threshold):
                    siemplify.LOGGER.info(
                        "Entity {0} has {1} detections. "
                        "Marking as suspicious.".format(
                            entity.identifier,
                            int(
                                reputation_obj.as_json()
                                .get("blacklists", {})
                                .get("detections", 0)
                            ),
                        )
                    )
                    entity.is_suspicious = True

                entity.is_enriched = True
                enriched_entities.append(entity)

            except APIVoidNotFound as e:
                siemplify.LOGGER.error(e)
                missing_entities.append(entity)

            except APIVoidInvalidAPIKeyError as e:
                siemplify.LOGGER.error(e)
                raise APIVoidInvalidAPIKeyError("API key is invalid.")

            except APIVoidManagerError as e:
                msg = str(e)
                siemplify.LOGGER.error(e)
                if LIMIT_EXCEEDED in msg.lower():
                    raise APIVoidManagerError(msg)

                failed_entities.append(entity)

            except Exception as e:
                failed_entities.append(entity)
                # An error occurred - skip entity and continue
                siemplify.LOGGER.error(
                    f"An error occurred on entity: {entity.identifier}"
                )
                siemplify.LOGGER.exception(e)

        if enriched_entities:
            enriched_entities_data = "\n   ".join(
                [entity.identifier for entity in enriched_entities]
            )
            output_message = (
                "APIVoid: Fetched reputation for the following "
                "entities:\n   {0}".format(enriched_entities_data)
            )

            siemplify.update_entities(enriched_entities)

        else:
            output_message = f"{INTEGRATION_NAME}: No entities were enriched."
            result_value = "false"

        if failed_entities:
            failed_entities_data = "\n   ".join(
                [entity.identifier for entity in failed_entities]
            )
            output_message += (
                "\n\nAn error occurred on the following "
                "entities:\n   {0}".format(failed_entities_data)
            )

        if missing_entities:
            missing_entities_data = "\n   ".join(
                [entity.identifier for entity in missing_entities]
            )
            output_message += (
                "\nNo reputation was found for the following "
                "entities:\n   {0}".format(missing_entities_data)
            )

    except Exception as e:
        output_message = (
            f'Error executing action "{GET_IP_REPUTATION_SCRIPT_NAME}". Reason: {e}'
        )
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(e)
        status = EXECUTION_STATE_FAILED
        result_value = "false"

    siemplify.result.add_result_json(convert_dict_to_json_result_dict(json_results))

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(f"Status: {status}:")
    siemplify.LOGGER.info(f"Result Value: {result_value}")
    siemplify.LOGGER.info(f"Output Message: {output_message}")
    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()
