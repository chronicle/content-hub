from __future__ import annotations
from soar_sdk.SiemplifyUtils import output_handler
from soar_sdk.SiemplifyDataModel import EntityTypes
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import (
    dict_to_flat,
    add_prefix_to_dict_keys,
    convert_dict_to_json_result_dict,
)
from ..core.McAfeeTIEDXLManager import McAfeeTIEDXLManager
from TIPCommon import extract_configuration_param, extract_action_param

SCRIPT_NAME = "Mcafee TIE & DXL - GetFileReputation"
INTEGRATION_NAME = "McAfeeTIEDXL"
ENRICHMENT_PREFIX = "McAfee_TIE_DXL"


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = SCRIPT_NAME

    server_addr = extract_configuration_param(
        siemplify, provider_name=INTEGRATION_NAME, param_name="Server Address"
    )

    broker_ca_bundle_path = extract_configuration_param(
        siemplify, provider_name=INTEGRATION_NAME, param_name="Broker CA Bundle Path"
    )

    cert_file_path = extract_configuration_param(
        siemplify, provider_name=INTEGRATION_NAME, param_name="Client Cert File Path"
    )

    private_key_path = extract_configuration_param(
        siemplify, provider_name=INTEGRATION_NAME, param_name="Client Key File Path"
    )

    enrich_with_all_services = extract_action_param(
        siemplify,
        param_name="Enrich with all services",
        is_mandatory=False,
        input_type=bool,
        default_value=False,
    )

    mcafee_dxl_manager = McAfeeTIEDXLManager(
        server_addr, broker_ca_bundle_path, cert_file_path, private_key_path
    )

    enriched_entities = []
    json_results = {}

    for entity in siemplify.target_entities:
        if entity.entity_type == EntityTypes.FILEHASH:
            try:
                reputations = mcafee_dxl_manager.get_file_reputation(entity.identifier)

                if reputations:
                    # Attach reputations as csv
                    csv_output = mcafee_dxl_manager.construct_csv(reputations)
                    siemplify.result.add_entity_table(
                        f"Reputations - {entity.identifier}", csv_output
                    )

                    json_results[entity.identifier] = reputations

                    if enrich_with_all_services:
                        reputation_enrichment = (
                            mcafee_dxl_manager.prepare_enrichment_repustations(
                                reputations
                            )
                        )
                        for reputation in reputation_enrichment:
                            reputation = dict_to_flat(reputation)
                            reputation = add_prefix_to_dict_keys(
                                reputation, ENRICHMENT_PREFIX
                            )
                            entity.additional_properties.update(reputation)

                    else:
                        # Get the worst trust level reputation and enrich entity with it
                        reputation_enrichment = (
                            mcafee_dxl_manager.get_worst_trust_level(reputations)
                        )
                        reputation_enrichment = dict_to_flat(reputation_enrichment)
                        reputation_enrichment = add_prefix_to_dict_keys(
                            reputation_enrichment, ENRICHMENT_PREFIX
                        )
                        entity.additional_properties.update(reputation_enrichment)

                    entity.is_enriched = True
                    enriched_entities.append(entity)

            except Exception as e:
                # An error occurred - skip entity and continue
                siemplify.LOGGER.error(
                    f"An error occurred on entity: {entity.identifier}.\n{str(e)}."
                )
                siemplify.LOGGER._log.exception(e)

    if enriched_entities:
        entities_names = [entity.identifier for entity in enriched_entities]

        output_message = (
            "McAfee TIE: The following entities were enriched:\n"
            + "\n".join(entities_names)
        )

        siemplify.update_entities(enriched_entities)

    else:
        output_message = "McAfee TIE: No entities were enriched."

    siemplify.result.add_result_json(convert_dict_to_json_result_dict(json_results))
    siemplify.end(output_message, True)


if __name__ == "__main__":
    main()
