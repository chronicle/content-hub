from __future__ import annotations
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyDataModel import EntityTypes
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyUtils import (
    add_prefix_to_dict,
    construct_csv,
    create_entity_json_result_object,
    dict_to_flat,
    get_domain_from_entity,
    output_handler,
)

from TIPCommon import extract_action_param, extract_configuration_param

from ..core.APIVoidManager import (
    APIVoidInvalidAPIKeyError,
    APIVoidManager,
    APIVoidManagerError,
    APIVoidNotFound,
)
from ..core.constants import (
    GET_DOMAIN_REPUTATION_SCRIPT_NAME,
    INSIGHT_MSG,
    INTEGRATION_NAME,
    LIMIT_EXCEEDED,
)


SUPPORTED_ENTITIES = [EntityTypes.HOSTNAME, EntityTypes.URL]


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = GET_DOMAIN_REPUTATION_SCRIPT_NAME

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
        is_mandatory=True,
        default_value=0,
        print_value=True,
        input_type=int,
    )
    create_insights = extract_action_param(
        siemplify, param_name="Create Insights", is_mandatory=True, input_type=bool
    )

    siemplify.LOGGER.info("----------------- Main - Started -----------------")

    try:
        apivoid_manager = APIVoidManager(api_root, api_key, verify_ssl=verify_ssl)

        enriched_entities = []
        missing_entities = []
        failed_entities = []
        json_results = []
        output_message = ""
        result_value = "false"
        status = EXECUTION_STATE_COMPLETED

        target_entities = [
            entity
            for entity in siemplify.target_entities
            if entity.entity_type in SUPPORTED_ENTITIES
        ]

        for entity in target_entities:
            domain = None

            if entity.entity_type == EntityTypes.HOSTNAME:
                domain = entity.identifier

            if entity.entity_type == EntityTypes.URL:
                domain = get_domain_from_entity(entity)

            if domain:
                siemplify.LOGGER.info(f"Started processing entity: {entity.identifier}")
                try:
                    reputation_obj = apivoid_manager.get_domain_reputation(
                        entity.identifier
                    )
                    enrichment_data = dict_to_flat(reputation_obj.as_enrichment_data())

                    if create_insights and enrichment_data.get("country_code"):
                        siemplify.add_entity_insight(
                            entity,
                            INSIGHT_MSG.format(enrichment_data.get("country_code")),
                            triggered_by=INTEGRATION_NAME,
                        )

                    enrichment_data = add_prefix_to_dict(
                        enrichment_data, INTEGRATION_NAME
                    )
                    entity.additional_properties.update(enrichment_data)

                    siemplify.result.add_entity_table(
                        entity.identifier,
                        construct_csv(reputation_obj.get_blacklist_report()),
                    )

                    json_results.append(
                        create_entity_json_result_object(
                            entity.identifier, reputation_obj.as_json()
                        )
                    )

                    if int(
                        reputation_obj.as_json().get("blacklists", {}).get("detections")
                    ) > int(threshold):
                        entity.is_suspicious = True

                    entity.is_enriched = True
                    enriched_entities.append(entity)
                    siemplify.LOGGER.info(f"Processed entity: {entity.identifier}")

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
                        f"An error occurred on entity: {entity.identifier}.\n{str(e)}."
                    )
                    siemplify.LOGGER.exception(e)

        if enriched_entities:
            entities_names = [entity.identifier for entity in enriched_entities]

            output_message += (
                "{0}: Fetched reputation for the following"
                " entities:\n{1}\n".format(INTEGRATION_NAME, "\n".join(entities_names))
            )

            siemplify.update_entities(enriched_entities)
            result_value = "true"

        if failed_entities:
            output_message += (
                "An error occurred on the following"
                " entities:\n{0}\n".format(
                    "\n".join([entity.identifier for entity in failed_entities])
                )
            )

        if missing_entities:
            output_message += (
                "No reputation found for the following"
                " entities:\n{}".format(
                    "\n".join([entity.identifier for entity in missing_entities])
                )
            )

        if (
            not enriched_entities
            and (missing_entities or failed_entities)
            or not target_entities
        ):
            output_message = f"{INTEGRATION_NAME}: No entities were enriched."

    except Exception as e:
        output_message = (
            f'Error executing action "{GET_DOMAIN_REPUTATION_SCRIPT_NAME}". Reason: {e}'
        )
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(e)
        status = EXECUTION_STATE_FAILED

    siemplify.result.add_result_json(json_results)
    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(f"Status: {status}:")
    siemplify.LOGGER.info(f"Result Value: {result_value}")
    siemplify.LOGGER.info(f"Output Message: {output_message}")
    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()
