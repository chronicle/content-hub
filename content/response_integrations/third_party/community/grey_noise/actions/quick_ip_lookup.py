from __future__ import annotations
import json

from greynoise.exceptions import RateLimitError, RequestFailure
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler
from ..core.api_manager import APIManager
from ..core.constants import (
    INTEGRATION_NAME,
    QUICK_IP_LOOKUP_SCRIPT_NAME,
    RESULT_VALUE_TRUE,
    RESULT_VALUE_FALSE,
    COMMON_ACTION_ERROR_MESSAGE,
    NO_IP_ENTITIES_ERROR,
)
from ..core.utils import (
    get_integration_params,
    get_ip_entities,
    generate_quick_ip_insight,
)
from ..core.datamodels import QuickLookupResult


def process_ip_lookups(greynoise_manager, ip_entities, siemplify):
    """
    Process IP lookups and return results with tracking lists.

    Args:
        greynoise_manager (APIManager): APIManager instance.
        ip_entities (list): List of IP entities to process.
        siemplify (SiemplifyAction): SiemplifyAction instance.

    Returns:
        tuple: (output_message, successful_entities, json_results)
    """
    siemplify.LOGGER.info(f"Processing {len(ip_entities)} IP addresses.")

    ip_list = [entity.identifier for entity in ip_entities]
    results = greynoise_manager.quick_lookup(ip_list, include_invalid=True)

    # Create entity map for lookup
    entity_map = {entity.identifier.lower(): entity for entity in ip_entities}

    ips_with_noise_data = []
    ips_without_noise_data = []
    successful_entities = []
    json_results = []

    for response in results:
        ip_address = response.get("ip")
        siemplify.LOGGER.info(f"Processing result for IP: {ip_address}")

        # Use datamodel for processing
        lookup_result = QuickLookupResult(response)

        if lookup_result.is_found():
            response["noise"] = True
            ips_with_noise_data.append(ip_address)

            entity = entity_map.get(ip_address.lower())
            if entity:
                # Use datamodel for enrichment
                entity.additional_properties.update(lookup_result.get_enrichment_data())
                entity.is_enriched = True
                entity.is_suspicious = lookup_result.is_suspicious()
                successful_entities.append(entity)

                # Create Insight
                insight_html = generate_quick_ip_insight(response, ip_address)
                if insight_html:
                    siemplify.add_entity_insight(
                        entity, insight_html, triggered_by=INTEGRATION_NAME
                    )

                siemplify.LOGGER.info(f"Successfully enriched entity: {entity.identifier}")
        else:
            response["noise"] = False
            ips_without_noise_data.append(ip_address)
            siemplify.LOGGER.info(f"No noise data found for IP: {ip_address}")

        json_results.append(response)

    # Build output message
    if ips_with_noise_data:
        output_message = (
            f"Successfully processed {len(ips_with_noise_data)} IP(s) "
            f"with noise data: {', '.join(ips_with_noise_data)}."
        )
    else:
        output_message = "No IPs with noise data found."

    if ips_without_noise_data:
        output_message += f" IPs with no noise data: {', '.join(ips_without_noise_data)}."

    return output_message, successful_entities, json_results


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = QUICK_IP_LOOKUP_SCRIPT_NAME
    siemplify.LOGGER.info("----------------- Main - Param Init -----------------")

    # Configuration Parameters
    api_key = get_integration_params(siemplify)

    siemplify.LOGGER.info("----------------- Main - Started -----------------")
    status = EXECUTION_STATE_COMPLETED
    result_value = RESULT_VALUE_TRUE
    output_message = ""
    json_results = []

    try:
        greynoise_manager = APIManager(api_key, siemplify=siemplify)
        siemplify.LOGGER.info(
            f"Connection to API established, performing action {QUICK_IP_LOOKUP_SCRIPT_NAME}."
        )

        # Use utility function for getting IP entities
        ip_entities = get_ip_entities(siemplify)

        if not ip_entities:
            output_message = NO_IP_ENTITIES_ERROR
            result_value = RESULT_VALUE_TRUE
            status = EXECUTION_STATE_COMPLETED
            siemplify.LOGGER.info(output_message)
            siemplify.result.add_result_json(json.dumps(json_results))
            siemplify.end(output_message, result_value, status)
            return
        else:
            output_message, successful_entities, json_results = process_ip_lookups(
                greynoise_manager, ip_entities, siemplify
            )

            # Update entities and add JSON results
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

    except ValueError as e:
        output_message = f"Invalid parameter value: {e}."
        result_value = RESULT_VALUE_FALSE
        status = EXECUTION_STATE_FAILED
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(e)

    except Exception as e:
        output_message = COMMON_ACTION_ERROR_MESSAGE.format(QUICK_IP_LOOKUP_SCRIPT_NAME, e)
        result_value = RESULT_VALUE_FALSE
        status = EXECUTION_STATE_FAILED
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(e)

    finally:
        siemplify.result.add_result_json(json.dumps(json_results))

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(f"Status: {status}")
    siemplify.LOGGER.info(f"result_value: {result_value}")
    siemplify.LOGGER.info(f"Output Message: {output_message}")
    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()
