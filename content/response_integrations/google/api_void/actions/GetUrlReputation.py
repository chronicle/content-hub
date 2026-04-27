from __future__ import annotations
import re

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
from ..core.constants import GET_URL_REPUTATION_SCRIPT_NAME, INTEGRATION_NAME, LIMIT_EXCEEDED


SUPPORTED_ENTITIES = [EntityTypes.URL]


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = GET_URL_REPUTATION_SCRIPT_NAME
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

    siemplify.LOGGER.info("----------------- Main - Started -----------------")

    result_value = "false"
    enriched_entities = []
    missing_entities = []
    failed_entities = []
    json_results = {}
    output_message = ""
    status = EXECUTION_STATE_COMPLETED

    target_entities = [
        entity
        for entity in siemplify.target_entities
        if entity.entity_type in SUPPORTED_ENTITIES
    ]

    try:
        apivoid_manager = APIVoidManager(api_root, api_key, verify_ssl=verify_ssl)

        for entity in target_entities:
            try:
                siemplify.LOGGER.info(f"Started processing entity: {entity.identifier}")

                if not re.match(r"^[a-zA-Z]+://", entity.identifier):
                    siemplify.LOGGER.info(
                        "Seems like schema is missing from the URL. "
                        "Prepending http://"
                    )
                    url = "http://" + entity.identifier

                else:
                    url = entity.identifier

                reputation_obj = apivoid_manager.get_url_reputation(url)
                enrichment_data = reputation_obj.as_enrichment_data()

                siemplify.LOGGER.info(f"Enriching entity {entity.identifier}")
                enrichment_data = add_prefix_to_dict(enrichment_data, INTEGRATION_NAME)
                entity.additional_properties.update(enrichment_data)

                if reputation_obj.get_blacklist_report():
                    siemplify.LOGGER.info(
                        "Adding blacklist report for "
                        "entity {0}".format(entity.identifier)
                    )
                    siemplify.result.add_data_table(
                        f"{entity.identifier} - Domain Blacklist Report",
                        construct_csv(reputation_obj.get_blacklist_report()),
                    )

                json_results[entity.identifier] = reputation_obj.as_json()

                if reputation_obj.risk_score > int(threshold):
                    siemplify.LOGGER.info(
                        "Entity {0} has risk score of {1}. Marking as "
                        "suspicious.".format(
                            entity.identifier, reputation_obj.risk_score
                        )
                    )
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
                    "An error occurred on " "entity: {0}".format(entity.identifier)
                )
                siemplify.LOGGER.exception(e)

        if enriched_entities:
            enriched_entities_data = "\n   ".join(
                [entity.identifier for entity in enriched_entities]
            )
            output_message = (
                "APIVoid: Fetched reputation for the following "
                "entities:\n   {0}\n\n".format(enriched_entities_data)
            )

            siemplify.update_entities(enriched_entities)
            result_value = "true"

        if failed_entities:
            failed_entities_data = "\n   ".join(
                [entity.identifier for entity in failed_entities]
            )
            output_message += (
                "An error occurred on the following "
                "entities:\n   {0}\n\n".format(failed_entities_data)
            )

        if missing_entities:
            missing_entities_data = "\n   ".join(
                [entity.identifier for entity in missing_entities]
            )
            output_message += (
                "Could not find reputation for the following "
                "entities:\n   {0}".format(missing_entities_data)
            )

        if (
            not enriched_entities
            and (failed_entities or missing_entities)
            or not target_entities
        ):
            output_message = "APIVoid: No URLs found."

    except Exception as e:
        output_message = (
            f'Error executing action "{GET_URL_REPUTATION_SCRIPT_NAME}". Reason: {e}'
        )
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(e)
        status = EXECUTION_STATE_FAILED

    siemplify.result.add_result_json(convert_dict_to_json_result_dict(json_results))
    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(f"Status: {status}:")
    siemplify.LOGGER.info(f"Result Value: {result_value}")
    siemplify.LOGGER.info(f"Output Message: {output_message}")
    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()
