from __future__ import annotations

from greynoise.exceptions import RateLimitError, RequestFailure
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler

from ..core.api_manager import APIManager
from ..core.constants import (
    INTEGRATION_NAME,
    IP_LOOKUP_SCRIPT_NAME,
    NO_IP_ENTITIES_ERROR,
    IP_NOT_FOUND_ERROR,
    COMMUNITY_TIER_MESSAGE,
    RESULT_VALUE_TRUE,
    RESULT_VALUE_FALSE,
    COMMON_ACTION_ERROR_MESSAGE,
)
from ..core.utils import (
    get_integration_params,
    get_ip_entities,
    generate_ip_lookup_insight,
)
from ..core.datamodels import IPLookupResult


def process_entity_response(
    entity, response, is_community, siemplify, successful_entities, not_found_entities, json_results
):
    """
    Process a single IP entity response and update tracking lists.

    Args:
        entity: Entity to process
        response (dict): API response data
        is_community (bool): Whether using community tier
        siemplify (SiemplifyAction): SiemplifyAction instance
        successful_entities (list): List to append successful entities
        not_found_entities (list): List to append not found entities
        json_results (list): List to append JSON results
    """
    ip_address = entity.identifier
    result = IPLookupResult(response)
    json_results.append({"Entity": ip_address, "EntityResult": response})

    if result.is_found():
        entity.additional_properties.update(result.get_enrichment_data())
        entity.is_enriched = True
        entity.is_suspicious = result.is_suspicious()
        successful_entities.append(entity)

        # Create Insight
        insight_html = generate_ip_lookup_insight(response, ip_address)
        if insight_html:
            siemplify.add_entity_insight(entity, insight_html, triggered_by=INTEGRATION_NAME)

        siemplify.LOGGER.info(f"Successfully processed IP: {ip_address}")
    else:
        not_found_entities.append(entity)
        siemplify.LOGGER.info(IP_NOT_FOUND_ERROR.format(ip_address))


def process_community_tier(
    greynoise_manager,
    ip_entities,
    siemplify,
    successful_entities,
    failed_entities,
    not_found_entities,
    json_results,
):
    """
    Process IP entities using Community tier API (individual lookups).

    Args:
        greynoise_manager (APIManager): APIManager instance
        ip_entities (list): List of IP entities to process
        siemplify (SiemplifyAction): SiemplifyAction instance
        successful_entities (list): List to append successful entities
        failed_entities (list): List to append failed entities
        not_found_entities (list): List to append not found entities
        json_results (list): List to append JSON results
    """
    siemplify.LOGGER.info(f"Processing {len(ip_entities)} IPs individually (Community)")

    for entity in ip_entities:
        ip_address = entity.identifier
        siemplify.LOGGER.info(f"Processing IP: {ip_address}")

        try:
            response = greynoise_manager.ip(ip_address)

            if response:
                process_entity_response(
                    entity,
                    response,
                    True,
                    siemplify,
                    successful_entities,
                    not_found_entities,
                    json_results,
                )
            else:
                failed_entities.append(entity)

        except RequestFailure as e:
            failed_entities.append(entity)
            siemplify.LOGGER.error(f"API request failed for {ip_address}: {str(e)}")
            continue

        except Exception as e:
            failed_entities.append(entity)
            siemplify.LOGGER.error(f"Error processing {ip_address}: {str(e)}")
            continue


def process_enterprise_tier(
    greynoise_manager,
    ip_entities,
    siemplify,
    successful_entities,
    failed_entities,
    not_found_entities,
    json_results,
):
    """
    Process IP entities using Enterprise tier API (batch lookup).

    Args:
        greynoise_manager (APIManager): APIManager instance
        ip_entities (list): List of IP entities to process
        siemplify (SiemplifyAction): SiemplifyAction instance
        successful_entities (list): List to append successful entities
        failed_entities (list): List to append failed entities
        not_found_entities (list): List to append not found entities
        json_results (list): List to append JSON results
    """
    ip_list = [entity.identifier for entity in ip_entities]
    siemplify.LOGGER.info(f"Processing {len(ip_list)} IPs via batch lookup (Enterprise)")

    try:
        responses = greynoise_manager.ip_multi(ip_list, include_invalid=True)

        # Create a mapping of IP to response
        response_map = {r.get("ip"): r for r in responses}

        for entity in ip_entities:
            ip_address = entity.identifier
            response = response_map.get(ip_address)

            if response:
                process_entity_response(
                    entity,
                    response,
                    False,
                    siemplify,
                    successful_entities,
                    not_found_entities,
                    json_results,
                )
            else:
                failed_entities.append(entity)
                siemplify.LOGGER.info(f"No response for IP: {ip_address}")

    except RequestFailure as e:
        siemplify.LOGGER.error(f"IP Multi lookup failed: {str(e)}")
        for entity in ip_entities:
            failed_entities.append(entity)


def build_output_message(successful_entities, not_found_entities, failed_entities, is_community):
    """
    Build the output message based on processing results.

    Args:
        successful_entities (list): Successfully processed entities
        not_found_entities (list): Entities not found in dataset
        failed_entities (list): Entities that failed to process
        is_community (bool): Whether using community tier

    Returns:
        tuple: (output_message, result_value, status)
    """
    output_message = ""
    result_value = RESULT_VALUE_TRUE
    status = EXECUTION_STATE_COMPLETED

    if successful_entities:
        entities_names = ", ".join([entity.identifier for entity in successful_entities])
        output_message += (
            f"Successfully enriched {len(successful_entities)} IP(s): {entities_names}"
        )

    if not_found_entities:
        entities_names = ", ".join([entity.identifier for entity in not_found_entities])
        output_message += (
            f"\nNot found in GreyNoise dataset: {len(not_found_entities)} IP(s): {entities_names}"
        )

    if failed_entities:
        entities_names = ", ".join([entity.identifier for entity in failed_entities])
        output_message += f"\nFailed to process {len(failed_entities)} IP(s): {entities_names}"

    if not successful_entities and not not_found_entities:
        output_message = f"Failed to process all {len(failed_entities)} IP(s)"
        result_value = RESULT_VALUE_FALSE
        status = EXECUTION_STATE_FAILED

    if is_community:
        output_message += f"\n\nNote: {COMMUNITY_TIER_MESSAGE}"

    return output_message, result_value, status


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = IP_LOOKUP_SCRIPT_NAME
    siemplify.LOGGER.info("----------------- Main - Param Init -----------------")

    # Configuration Parameters
    api_key = get_integration_params(siemplify)

    siemplify.LOGGER.info("----------------- Main - Started -----------------")

    status = EXECUTION_STATE_COMPLETED
    result_value = RESULT_VALUE_TRUE
    output_message = ""
    successful_entities = []
    failed_entities = []
    not_found_entities = []
    json_results = []

    try:
        # Initialize GreyNoise manager
        greynoise_manager = APIManager(api_key, siemplify=siemplify)

        # Check if community tier
        is_community = greynoise_manager.is_community_key()
        if is_community:
            siemplify.LOGGER.info(COMMUNITY_TIER_MESSAGE)

        # Get IP entities
        ip_entities = get_ip_entities(siemplify)

        if not ip_entities:
            output_message = NO_IP_ENTITIES_ERROR
            result_value = RESULT_VALUE_TRUE
            status = EXECUTION_STATE_COMPLETED
            siemplify.LOGGER.info(output_message)
            siemplify.result.add_result_json(json_results)
            siemplify.end(output_message, result_value, status)
            return

        siemplify.LOGGER.info(f"Found {len(ip_entities)} IP entities to process")

        # Process entities based on tier
        if is_community:
            process_community_tier(
                greynoise_manager,
                ip_entities,
                siemplify,
                successful_entities,
                failed_entities,
                not_found_entities,
                json_results,
            )
        else:
            process_enterprise_tier(
                greynoise_manager,
                ip_entities,
                siemplify,
                successful_entities,
                failed_entities,
                not_found_entities,
                json_results,
            )

        # Build output message
        output_message, result_value, status = build_output_message(
            successful_entities, not_found_entities, failed_entities, is_community
        )

        # Update entities
        if successful_entities:
            siemplify.update_entities(successful_entities)

    except RateLimitError as e:
        output_message = f"Rate limit reached: {str(e)}"
        result_value = RESULT_VALUE_FALSE
        status = EXECUTION_STATE_FAILED
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(e)

    except RequestFailure as e:
        output_message = f"Failed to connect to the GreyNoise server: {str(e)}"
        result_value = RESULT_VALUE_FALSE
        status = EXECUTION_STATE_FAILED
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(e)

    except Exception as e:
        output_message = COMMON_ACTION_ERROR_MESSAGE.format(IP_LOOKUP_SCRIPT_NAME, e)
        result_value = RESULT_VALUE_FALSE
        status = EXECUTION_STATE_FAILED
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(e)
 
    finally:
        siemplify.result.add_result_json(json_results)

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(f"Status: {status}")
    siemplify.LOGGER.info(f"Result Value: {result_value}")
    siemplify.LOGGER.info(f"Output Message: {output_message}")
    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()
