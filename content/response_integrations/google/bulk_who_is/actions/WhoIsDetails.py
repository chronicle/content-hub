from __future__ import annotations
from soar_sdk.SiemplifyUtils import output_handler, flat_dict_to_csv, get_domain_from_entity
from soar_sdk.SiemplifyDataModel import EntityTypes

# Imports
from soar_sdk.SiemplifyAction import SiemplifyAction
from ..core.WhoisManager import WhoisManager
from soar_sdk.SiemplifyUtils import convert_dict_to_json_result_dict
from TIPCommon import extract_configuration_param
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from urllib.parse import urlparse

# Consts

INTEGRATION_NAME = "BulkWhoIS"
SCRIPT_NAME = "BulkWhoIS - WhoIs Details"


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = SCRIPT_NAME
    result_value = "true"

    siemplify.LOGGER.info("================= Main - Param Init =================")

    # INIT INTEGRATION CONFIGURATION:
    verify_ssl = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Verify SSL",
        default_value=False,
        input_type=bool,
    )
    api_key = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Api Key",
        is_mandatory=True,
        input_type=str,
    )
    api_secret = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Secret Key",
        is_mandatory=True,
        input_type=str,
    )

    status = EXECUTION_STATE_COMPLETED
    entities_to_update = []
    json_results = {}
    siemplify.LOGGER.info("----------------- Main - Started -----------------")
    try:
        whois = WhoisManager(api_key, api_secret, verify_ssl=verify_ssl)
        for entity in siemplify.target_entities:
            entity_to_scan = ""
            detail_object = None

            if entity.entity_type == EntityTypes.URL:
                entity_to_scan = get_domain_from_entity(entity)

            if entity.entity_type == EntityTypes.HOSTNAME and not entity.is_internal:
                url_without_schema = urlparse(entity.identifier)
                url_without_schema = (
                    url_without_schema.hostname
                )  # Check if the URL contains schema
                if url_without_schema:
                    entity_to_scan = url_without_schema
                else:
                    entity_to_scan = entity.identifier

            if entity.entity_type == EntityTypes.ADDRESS:
                entity_to_scan = entity.identifier

            if entity_to_scan:
                try:
                    detail_object = whois.scan(entity_to_scan)
                except Exception as e:
                    # An error occurred - skip entity and continue
                    siemplify.LOGGER.error(
                        f"An error occurred on entity: {entity.identifier}.\n{str(e)}."
                    )
                    siemplify.LOGGER.exception(e)

            if detail_object and detail_object.success == True:
                enrichment_dict = detail_object.to_enrichment_data()
                entity.additional_properties.update(enrichment_dict)
                entity.is_enriched = True
                entities_to_update.append(entity)

                entity_table = flat_dict_to_csv(detail_object.to_dict())
                siemplify.result.add_entity_table(entity.identifier, entity_table)

                # build json
                json_results[entity.identifier] = enrichment_dict

        if entities_to_update:
            entities_names = [entity.identifier for entity in entities_to_update]
            output_message = (
                "The following entities were enriched by Whois: \n"
                + "\n".join(entities_names)
            )
            siemplify.update_entities(entities_to_update)

        else:
            output_message = "No entities were enriched."
    except Exception as e:
        siemplify.LOGGER.error(f"General error performing action {SCRIPT_NAME}")
        siemplify.LOGGER.exception(e)
        status = EXECUTION_STATE_FAILED
        result_value = "false"
        output_message = "Some errors occurred. Please check log"

    # add json
    siemplify.result.add_result_json(convert_dict_to_json_result_dict(json_results))
    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(
        f"\n  status: {status}\n  result_value: {result_value}\n  output_message: {output_message}"
    )
    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()
