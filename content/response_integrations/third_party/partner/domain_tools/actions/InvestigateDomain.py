from __future__ import annotations
from typing import Any


"""
Action script for DomainTools - Investigate Domain.

Enrich external domain entity with DomainTools threat Intelligence data
and return CSV output, including JSON results.
"""

from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyDataModel import EntityTypes
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyUtils import output_handler
from TIPCommon.extraction import extract_configuration_param
from TIPCommon.transformation import construct_csv, flat_dict_to_csv, dict_to_flat, add_prefix_to_dict_keys


from ..core.DomainToolsManager import DomainToolsManager
from ..core.exceptions import DomainToolsManagerError
from ..core.constants import INTEGRATION_NAME, INVESTIGATE_SCRIPT_NAME
from ..core.UtilsManager import (
    convert_list_to_comma_string,
    chunks,
    extract_domain_from_string
)
from ..core.datamodels import IrisInvestigateModel


SUPPORTED_ENTITY_TYPES: list[str] = [
    EntityTypes.URL,
    EntityTypes.HOSTNAME,
    EntityTypes.DOMAIN
]


@output_handler
def main() -> None:
    """Enrich external domain entity with DomainTools threat Intelligence data."""
    siemplify = SiemplifyAction()
    siemplify.script_name = INVESTIGATE_SCRIPT_NAME
    siemplify.LOGGER.info("----------------- Main - Investigate Domain Started -----------------")

    username: str = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Username",
        is_mandatory=True,
        print_value=True,
    )
    api_key: str = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="ApiToken",
        is_mandatory=True,
        print_value=True,
    )
    verify_ssl: str = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Verify SSL",
        is_mandatory=True
    )

    status: int = EXECUTION_STATE_COMPLETED
    output_message: str = ""
    result_value: bool = True
    json_results: list[dict[str, Any]] = []
    target_entities: list[Any] = [
        entity
        for entity in siemplify.target_entities
        if entity.entity_type in SUPPORTED_ENTITY_TYPES
    ]
    failed_entities: list = []
    success_entities: list = []
    csv_table_results: list[dict] = []

    try:
        dt_manager = DomainToolsManager(
            username=username,
            api_key=api_key,
            verify_ssl=verify_ssl,
            siemplify_logger=siemplify.LOGGER,
        )

        extracted_domains: dict[str, Any] = {
            extract_domain_from_string(entity.identifier): entity
            for entity in target_entities
        }

        if not extracted_domains:
            output_message = "No entities were extracted to be enrich."
            result_value = False
            siemplify.end(output_message, result_value, status)

        domains_to_enrich = convert_list_to_comma_string(list(extracted_domains.keys()))

        # iris investigate endpoint accept comma separated values up to 100
        # we do this to save up api calls
        domain_chunks = chunks(domains_to_enrich, 100)
        for chunk in domain_chunks:
            domain_iris_models: list[IrisInvestigateModel] = dt_manager.investigate_domains(domains=domains_to_enrich)

            if not domain_iris_models:
                output_message = "No entities were extracted to be enrich."
                result_value = False
                siemplify.end(output_message, result_value, status)

            # get the corresponding domain entity
            for domain_model in domain_iris_models:
                entity = extracted_domains[domain_model.name]
                siemplify.LOGGER.info(f"Processing entity: {entity.identifier}")
                try:
                    domain_dict = domain_model.to_dict()
                    json_results.append({"Entity": entity.identifier, "EntityResult": domain_dict})

                    flattened_iris_data: dict[str, Any] = dict_to_flat(domain_dict)
                    prefixed_iris_data = add_prefix_to_dict_keys(flattened_iris_data, "DT")
                    entity.additional_properties.update(prefixed_iris_data)

                    siemplify.result.add_entity_table(entity.identifier, flat_dict_to_csv(flattened_iris_data))

                    csv_table_results.append(domain_model.to_table_data())

                    entity.is_enriched = True
                    success_entities.append(entity)
                except Exception as e:
                    failed_entities.append(entity)
                    siemplify.LOGGER.error(
                        f"Unable to enrich entity: {entity.identifier}. Reason: {str(e)}")
                    siemplify.LOGGER.exception(e)
                    continue

        if success_entities:
            siemplify.update_entities(success_entities)
            siemplify.result.add_result_json(json_results)

            output_message += "Entities Enriched By DomainTools:\n{0}".format(
                "\n".join(map(str, success_entities))
            )

            if failed_entities:
                output_message += (
                    f"Action wasn't able to enrich the following entities using information from "
                    f"{INTEGRATION_NAME}: {', '.join(failed_entities)}\n"
                )

            # create a summary table for all entities enriched
            if csv_table_results:
                siemplify.result.add_data_table("DomainTools Iris Investigated Domains", construct_csv(csv_table_results))
        else:
            output_message = "No entities were enriched."
            result_value = False
    except Exception as err:
        output_message = f"Error running action: {str(err)}"
        status = EXECUTION_STATE_FAILED
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(err)
        result_value = "false"

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(f"Status: {status}")
    siemplify.LOGGER.info(f"Result: {result_value}")
    siemplify.LOGGER.info(f"Output Message: {output_message}")
    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()
