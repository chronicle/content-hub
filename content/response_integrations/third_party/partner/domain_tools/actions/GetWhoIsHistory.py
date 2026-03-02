"""
Action script for DomainTools - Get WhoisHistory.

Enrich external domain entity with DomainTools threat Intelligence data
and return CSV output, including JSON results.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyDataModel import DomainEntityInfo, EntityTypes
from soar_sdk.SiemplifyUtils import output_handler
from TIPCommon.extraction import extract_action_param, extract_configuration_param
from TIPCommon.transformation import (
    add_prefix_to_dict_keys,
    construct_csv,
    dict_to_flat,
    flat_dict_to_csv,
)

from ..core.constants import INTEGRATION_NAME, WHOIS_HISTORY_SCRIPT_NAME
from ..core.datamodels import WhoisHistoryModel
from ..core.DomainToolsManager import DomainToolsManager
from ..core.UtilsManager import extract_domain_from_string

SUPPORTED_ENTITY_TYPES: list[str] = [EntityTypes.URL, EntityTypes.HOSTNAME, EntityTypes.DOMAIN]


@output_handler
def main() -> None:
    """Enrich external domain entity with DomainTools threat Intelligence data."""
    siemplify = SiemplifyAction()
    siemplify.script_name = WHOIS_HISTORY_SCRIPT_NAME
    siemplify.LOGGER.info("----------------- Main - Get Whois History Started -----------------")

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
        siemplify, provider_name=INTEGRATION_NAME, param_name="Verify SSL", is_mandatory=True
    )

    enriched_entities: list[Any] = []
    failed_entities: list[Any] = []
    json_results: list[dict[str, Any]] = []
    result_value: bool = False
    status: int = EXECUTION_STATE_COMPLETED
    output_message: str = ""
    csv_table_results: list[dict] = []

    try:
        dt_manager = DomainToolsManager(
            username=username,
            api_key=api_key,
            verify_ssl=verify_ssl,
            siemplify_logger=siemplify.LOGGER,
        )

        domain_param = extract_action_param(siemplify, param_name="Domain", print_value=True)
        if domain_param:
            now_ts = int(datetime.now().timestamp())
            domain_entity = DomainEntityInfo(
                domain_param,
                creation_time=now_ts,
                modification_time=now_ts,
                case_identifier="",
                alert_identifier="",
                entity_type=EntityTypes.DOMAIN,
                is_internal=False,
                is_suspicious=False,
                is_artifact=False,
                is_enriched=False,
                is_vulnerable=False,
                is_pivot=False,
                additional_properties={},
            )
            target_entities = [domain_entity]
        else:
            target_entities: list[Any] = [
                entity
                for entity in siemplify.target_entities
                if entity.entity_type in SUPPORTED_ENTITY_TYPES
            ]

        for entity in target_entities:
            try:
                domain: str = extract_domain_from_string(entity.identifier)
                siemplify.LOGGER.info(f"Processing entity: {entity.identifier}")

                dt_whois_history: WhoisHistoryModel = dt_manager.get_whois_history(domain=domain)
                dt_whois_history_dict = dt_whois_history.to_dict()

                flattened_whois_data: dict[str, Any] = dict_to_flat(dt_whois_history_dict)
                json_entity_res = {
                    "Entity": entity.identifier,
                    "EntityResult": dt_whois_history_dict,
                }

                if not dt_whois_history.record_count:
                    siemplify.LOGGER.info(f"No Whois History data found for {domain}")
                    json_entity_res["EntityResult"] = {
                        "status": "No Whois History record found on this domain"
                    }
                else:
                    # create a table result
                    siemplify.result.add_entity_table(
                        entity.identifier, flat_dict_to_csv(flattened_whois_data)
                    )
                    csv_table_results = dt_whois_history.to_table_data()

                enriched_entities.append(entity)
                json_results.append(json_entity_res)

                prefixed_whois_data = add_prefix_to_dict_keys(flattened_whois_data, "DT")
                entity.additional_properties.update(prefixed_whois_data)

                siemplify.LOGGER.info(f"Successfully enriched {entity.identifier}")
            except Exception as e:
                failed_entities.append(entity)
                siemplify.LOGGER.error(
                    f"Unable to enrich entity: {entity.identifier}. Reason: {str(e)}"
                )
                siemplify.LOGGER.exception(e)
                continue

        if enriched_entities:
            siemplify.update_entities(enriched_entities)
            siemplify.result.add_result_json(json_results)
            result_value = True

            output_message += "Entities Enriched By DomainTools:\n{0}".format(
                "\n".join(map(str, enriched_entities))
            )

            if failed_entities:
                output_message += (
                    f"Action wasn't able to enrich the following entities using information from "
                    f"{INTEGRATION_NAME}: {', '.join(failed_entities)}\n"
                )
            # create a summary table for all entities enriched
            if csv_table_results:
                siemplify.result.add_data_table(
                    "DomainTools Whois History", construct_csv(csv_table_results)
                )
        else:
            output_message = "No entities were enriched."
            result_value = False

    except Exception as err:
        output_message = f"Error running action: {str(err)}"
        status = EXECUTION_STATE_FAILED
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(err)
        result_value = False

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(f"Status: {status}")
    siemplify.LOGGER.info(f"Result: {result_value}")
    siemplify.LOGGER.info(f"Output Message: {output_message}")
    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()
