from __future__ import annotations
import json
import sys
from soar_sdk.SiemplifyUtils import output_handler
from soar_sdk.ScriptResult import (
    EXECUTION_STATE_COMPLETED,
    EXECUTION_STATE_FAILED,
    EXECUTION_STATE_INPROGRESS,
    EXECUTION_STATE_TIMEDOUT,
)
from soar_sdk.SiemplifyAction import SiemplifyAction
from TIPCommon import extract_configuration_param, extract_action_param
from ..core.constants import (
    INTEGRATION_NAME,
    INTEGRATION_DISPLAY_NAME,
    GET_REPUTATION_SCRIPT_NAME,
    QUERY_TYPE_MAPPING,
    CATEGORY_QUERY_TYPE_MAPPING,
)
from soar_sdk.SiemplifyDataModel import EntityTypes
from ..core.TalosManager import TalosManager
from ..core.UtilsManager import get_domain_from_entity, get_entity_original_identifier
from ..core.TalosExceptions import TalosNotFoundManagerError
from soar_sdk.SiemplifyUtils import (
    convert_dict_to_json_result_dict,
    convert_unixtime_to_datetime,
    unix_now,
)
from TIPCommon import construct_csv


SUPPORTED_ENTITY_TYPES = [EntityTypes.HOSTNAME, EntityTypes.ADDRESS, EntityTypes.URL]
ENRICHMENT_PREFIX = "CiscoTalos"


def query_entity_report(
    siemplify, manager, entity, successful_entity_identifiers, failed_entity_identifiers
):
    """
    Query entity report
    :param siemplify: SiemplifyAction object
    :param manager: TalosManager manager object
    :param entity: SiemplifyEntity object
    :param successful_entity_identifiers: {list} list of successful entity identifiers
    :param failed_entity_identifiers: {list} list of failed entity identifiers
    :return: {tuple} reputation, category_info, blocked_info, successful_entity_identifiers, failed_entity_identifiers
    """
    siemplify.LOGGER.info(f"\nStarted processing entity: {entity.identifier}")
    threat_reputation = None
    reputation = None
    category_info = None
    blocked_info = None
    entity_identifier = get_entity_original_identifier(entity)
    try:
        try:
            if entity.entity_type == EntityTypes.ADDRESS:
                # get reputation for ip
                reputation = manager.get_ip_reputation(entity_identifier)
            elif entity.entity_type == EntityTypes.URL:
                domain = get_domain_from_entity(entity_identifier)
                try:
                    threat_reputation = manager.get_url_reputation(domain)
                    # get reputation for domain
                    reputation = manager.get_domain_reputation(domain)
                except Exception as e:
                    # API call happen when domain API giving error
                    # get url reputation for domain url
                    siemplify.LOGGER.error(
                        f"Domain API call failed: {entity.identifier}: Error is: {e}"
                    )
                    threat_reputation = manager.get_url_reputation(domain)
            elif entity.entity_type == EntityTypes.HOSTNAME:
                # get reputation for hostname
                reputation = manager.get_hostname_reputation(entity_identifier)
        except TalosNotFoundManagerError:
            siemplify.LOGGER.info(f"No reputation was found for {entity.identifier}")
        except Exception as e:
            siemplify.LOGGER.error(f"Unable to get reputation for {entity.identifier}")
            siemplify.LOGGER.exception(e)
        identifier = (
            get_domain_from_entity(entity_identifier)
            if entity.entity_type == EntityTypes.URL
            else entity_identifier
        )
        query_type = (
            QUERY_TYPE_MAPPING.get("ip")
            if entity.entity_type == EntityTypes.ADDRESS
            else QUERY_TYPE_MAPPING.get("domain")
        )
        category_query_type = (
            CATEGORY_QUERY_TYPE_MAPPING.get("ip")
            if entity.entity_type == EntityTypes.ADDRESS
            else CATEGORY_QUERY_TYPE_MAPPING.get("domain")
        )
        # get category info for ip/domain/hostname
        try:
            category_info = manager.get_category_info(category_query_type, identifier)
        except TalosNotFoundManagerError:
            siemplify.LOGGER.info(f"No category info was found for {entity.identifier}")
        except Exception as e:
            siemplify.LOGGER.error(
                f"Unable to get category info for {entity.identifier}"
            )
            siemplify.LOGGER.exception(e)
        # get blocked info for ip/domain/hostname
        try:
            blocked_info = manager.get_blocked_info(query_type, identifier)
        except Exception as e:
            siemplify.LOGGER.error(
                f"Unable to get blocked info for {entity.identifier}"
            )
            siemplify.LOGGER.exception(e)
        if reputation or threat_reputation:
            successful_entity_identifiers.append(entity.identifier)
        else:
            failed_entity_identifiers.append(entity.identifier)
    except Exception as e:
        siemplify.LOGGER.error(
            f"Failed processing entities: {entity.identifier}: Error is: {e}"
        )
        failed_entity_identifiers.append(entity.identifier)
    siemplify.LOGGER.info(f"Finished processing entity {entity.identifier}\n")
    return (
        threat_reputation,
        reputation,
        category_info,
        blocked_info,
        successful_entity_identifiers,
        failed_entity_identifiers,
    )


@output_handler
def main(is_first_run):
    siemplify = SiemplifyAction()
    siemplify.script_name = GET_REPUTATION_SCRIPT_NAME
    siemplify.LOGGER.info("----------------- Main - Param Init -----------------")
    use_ssl = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Use SSL",
        is_mandatory=True,
        input_type=bool,
        default_value=False,
        print_value=True,
    )
    additional_data = json.loads(
        extract_action_param(
            siemplify=siemplify, param_name="additional_data", default_value="{}"
        )
    )
    siemplify.LOGGER.info("----------------- Main - Started -----------------")
    result = True
    status = EXECUTION_STATE_COMPLETED
    output_message = ""
    reputation_json_data = {}
    json_results = additional_data.get("json_results", {})
    entity_tables = additional_data.get("entity_tables", {})
    enrichment_data = additional_data.get("enrichment_data", {})
    successful_entity_identifiers = additional_data.get(
        "successful_entity_identifiers", []
    )
    failed_entity_identifiers = additional_data.get("failed_entity_identifiers", [])
    initial_suitable_entity_identifiers = additional_data.get(
        "initial_suitable_entity_identifiers", []
    )
    if is_first_run:
        suitable_entities = [
            entity
            for entity in siemplify.target_entities
            if entity.entity_type in SUPPORTED_ENTITY_TYPES
        ]
    else:
        suitable_entities = [
            entity
            for entity in siemplify.target_entities
            if entity.identifier in initial_suitable_entity_identifiers
        ]
    try:
        if unix_now() >= siemplify.execution_deadline_unix_time_ms:
            siemplify.LOGGER.error(
                f"Timed out. execution deadline "
                f"({convert_unixtime_to_datetime(siemplify.execution_deadline_unix_time_ms)}) has "
                f"passed"
            )
            status = EXECUTION_STATE_TIMEDOUT
        talos_manager = TalosManager(use_ssl=use_ssl)
        talos_manager.test_connectivity()
        not_processed_entities = [
            entity
            for entity in suitable_entities
            if entity.identifier
            not in successful_entity_identifiers + failed_entity_identifiers
        ]
        if not_processed_entities:
            current_entity = not_processed_entities[0]
            (
                threat_reputation,
                reputation,
                category_info,
                blocked_info,
                successful_entity_identifiers,
                failed_entity_identifiers,
            ) = query_entity_report(
                siemplify,
                talos_manager,
                current_entity,
                successful_entity_identifiers,
                failed_entity_identifiers,
            )

            reputation_data = (
                {} if reputation is None else {"reputation": reputation.to_json()}
            )
            threat_reputation_data = (
                {}
                if threat_reputation is None
                else {"threat_reputation": threat_reputation.to_json()}
            )
            reputation_json_data = {**reputation_data, **threat_reputation_data}
            reputation_table_data = (
                {} if reputation is None else {**reputation.to_table()}
            )
            threat_reputation_table_data = (
                {} if threat_reputation is None else {**threat_reputation.to_table()}
            )
            reputation_table_data_main = {
                **reputation_table_data,
                **threat_reputation_table_data,
            }

        if reputation_json_data:
            json_results[current_entity.identifier] = {
                **reputation_json_data,
                "category_info": category_info.to_json() if category_info else {},
                "blocked_info": blocked_info.to_json() if blocked_info else {},
            }

            entity_tables[current_entity.identifier] = construct_csv(
                [
                    {
                        **reputation_table_data_main,
                        **(category_info.to_table() if category_info else {}),
                        **(blocked_info.to_table() if blocked_info else {}),
                    }
                ]
            )
            if reputation is not None:
                enrichment_data[current_entity.identifier] = (
                    reputation.to_enrichment_data(prefix=ENRICHMENT_PREFIX)
                )
            if threat_reputation is not None:
                enrichment_data[current_entity.identifier] = (
                    threat_reputation.to_enrichment_data(prefix=ENRICHMENT_PREFIX)
                )

        if successful_entity_identifiers:
            output_message += "Successfully enriched the following entities using information from {}: \n{}".format(
                INTEGRATION_DISPLAY_NAME, "\n".join(successful_entity_identifiers)
            )
        if failed_entity_identifiers:
            output_message += "\nAction wasn't able to enrich the following entities using information from {}: \n{}".format(
                INTEGRATION_DISPLAY_NAME, "\n".join(failed_entity_identifiers)
            )
        if len(suitable_entities) == len(successful_entity_identifiers) + len(
            failed_entity_identifiers
        ):
            if successful_entity_identifiers:
                siemplify.result.add_result_json(
                    convert_dict_to_json_result_dict(json_results)
                )
                for key, value in entity_tables.items():
                    siemplify.result.add_entity_table(key, value)
                updated_entities = []
                for suitable_entity in suitable_entities:
                    if suitable_entity.identifier in successful_entity_identifiers:
                        suitable_entity.additional_properties.update(
                            enrichment_data.get(suitable_entity.identifier, {})
                        )
                        suitable_entity.is_enriched = True
                        updated_entities.append(suitable_entity)
                siemplify.update_entities(updated_entities)
            else:
                result = False
                output_message = "None of the provided entities were enriched."
        else:
            status = EXECUTION_STATE_INPROGRESS
            result = json.dumps(
                {
                    "successful_entity_identifiers": successful_entity_identifiers,
                    "failed_entity_identifiers": failed_entity_identifiers,
                    "json_results": json_results,
                    "entity_tables": entity_tables,
                    "enrichment_data": enrichment_data,
                    "initial_suitable_entity_identifiers": [
                        entity.identifier for entity in suitable_entities
                    ],
                }
            )
    except Exception as e:
        siemplify.LOGGER.error(
            f"General error performing action {GET_REPUTATION_SCRIPT_NAME}"
        )
        siemplify.LOGGER.exception(e)
        result = False
        status = EXECUTION_STATE_FAILED
        output_message = (
            f"Error executing action {GET_REPUTATION_SCRIPT_NAME}. Reason: {e}"
        )
    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(f"Status: {status}")
    siemplify.LOGGER.info(f"Result: {result}")
    siemplify.LOGGER.info(f"Output Message: {output_message}")
    siemplify.end(output_message, result, status)


if __name__ == "__main__":
    is_first_run = len(sys.argv) < 3 or sys.argv[2] == "True"
    main(is_first_run)
