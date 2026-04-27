from __future__ import annotations
from soar_sdk.SiemplifyAction import SiemplifyAction
from ..core.McAfeeMvisionEPOManager import McAfeeMvisionEPOManager
from soar_sdk.SiemplifyUtils import output_handler, convert_dict_to_json_result_dict
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from TIPCommon import extract_configuration_param, construct_csv
from ..core.constants import ENRICH_ENDPOINT_SCRIPT_NAME, INTEGRATION_NAME, ENRICHMENT_PREFIX
from ..core.exceptions import EndpointNotFoundException
from soar_sdk.SiemplifyDataModel import EntityTypes


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = ENRICH_ENDPOINT_SCRIPT_NAME
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

    siemplify.LOGGER.info("----------------- Main - Started -----------------")
    status = EXECUTION_STATE_COMPLETED
    result_value = True
    enriched_entities = []
    enriched_entity_identifiers = []
    output_message = ""
    json_results = {}
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

        for entity in suitable_entities:
            try:
                siemplify.LOGGER.info(
                    f"\n\nStarted processing entity: {entity.identifier}"
                )
                msg = f"Action was not able to enrich the following endpoints from McAfee Mvision ePO\n: {entity.identifier}"
                device = manager.find_entity_or_fail(
                    entity.identifier,
                    is_host=entity.entity_type == EntityTypes.HOSTNAME,
                )
                enriched_entity_identifiers.append(entity.identifier)
                enriched_entities.append(entity)
                json_results[entity.identifier] = device.to_json()
                entity.additional_properties.update(
                    device.to_enrichment_data(ENRICHMENT_PREFIX)
                )
                entity.is_enriched = True
                siemplify.result.add_data_table(
                    title=f"Installed products on {entity.identifier}",
                    data_table=construct_csv(
                        [
                            product_installed.to_table_data()
                            for product_installed in device.products_installed
                        ]
                    ),
                )

                msg = f"Successfully enriched the following endpoint from McAfee Mvision ePO:  \n {entity.identifier}"
                siemplify.LOGGER.info(msg)
            except EndpointNotFoundException:
                failed_entities.append(entity.identifier)
                siemplify.LOGGER.error(msg)
            except Exception as e:
                failed_entities.append(entity.identifier)
                siemplify.LOGGER.error(msg)
                siemplify.LOGGER.exception(e)
            siemplify.LOGGER.info(f"Finished processing entity: {entity.identifier}")

        if failed_entities:
            output_message += "Action was not able to enrich the following endpoints from McAfee Mvision ePO: \n{}\n".format(
                "\n".join(failed_entities)
            )

        if enriched_entities:
            siemplify.result.add_result_json(
                convert_dict_to_json_result_dict(json_results)
            )
            siemplify.update_entities(enriched_entities)
            output_message += "Successfully enriched the following endpoints from McAfee Mvision ePO: \n{}\n".format(
                "\n".join(enriched_entity_identifiers)
            )

        else:
            siemplify.LOGGER.info("\n No entities where processed.")
            output_message = "No entities where processed."
            result_value = False

    except Exception as e:
        output_message = (
            f"Error executing action '{ENRICH_ENDPOINT_SCRIPT_NAME}'. Reason: {e}"
        )
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
