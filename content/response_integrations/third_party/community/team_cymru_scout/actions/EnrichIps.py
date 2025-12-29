from __future__ import annotations

from datetime import datetime

from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyDataModel import EntityTypes
from soar_sdk.SiemplifyUtils import (
    add_prefix_to_dict,
    convert_unixtime_to_datetime,
    output_handler,
    unix_now,
)

from ..core.ApiManager import ApiManager
from ..core.constants import (
    ALREADY_ENRICHED_MSG,
    ENRICH_IPS_SCRIPT_NAME,
    INTEGRATION_NAME,
)
from ..core.EnrichIPs import EnrichIPs
from ..core.TeamCymruScoutException import TeamCymruScoutException
from ..core.utils import get_integration_params


def is_entity_already_enriched(entity, logger):
    """Check if an entity was already enriched in the last 24 hours.

    :param entity: The entity to check
    :return: True if the entity was already enriched, False otherwise
    """
    last_enrichment_time = entity.additional_properties.get("TCS_last_enriched")
    if last_enrichment_time:
        try:
            last_enrichment_time = datetime.strptime(
                last_enrichment_time,
                "%Y-%m-%d %H:%M:%S.%f%z",
            )
        except ValueError:
            logger.info(
                f"The value of 'TCS_last_enriched' field: {last_enrichment_time} is not in expected format: '%Y-%m-%d %H:%M:%S.%f%z'. Hence, enriching the entity: {entity.identifier} again...",
            )
            return False

        current_time = convert_unixtime_to_datetime(unix_now())
        delta = current_time - last_enrichment_time

        # Entity already enriched
        if delta.total_seconds() < 24 * 60 * 60:
            return True

    return False


@output_handler
def main():
    """Enrich IPs action is used to enrich the IP Address Entities from the information available in Team Cymru Scout platform."""
    siemplify = SiemplifyAction()
    is_success = False

    try:
        auth_type, api_key, username, password, verify_ssl = get_integration_params(
            siemplify,
        )
        successful_entities, failed_entities = [], []
        output_message = ""
        status = EXECUTION_STATE_COMPLETED

        # Collect all the IP Addresses from the target entities
        address_entities = [
            entity.identifier
            for entity in siemplify.target_entities
            if entity.entity_type == EntityTypes.ADDRESS
        ]

        if not address_entities:
            is_success = True
            output_message = "No IP Addresses entities were found."
            siemplify.result.add_result_json({})
        else:
            # Use list IP summary for multiple ips insights and prepare dict
            enrich_ips = EnrichIPs(siemplify, address_entities)

            api_manager = ApiManager(
                auth_type,
                api_key,
                username,
                password,
                siemplify.LOGGER,
                verify_ssl,
            )
            is_success = enrich_ips.get_ips_summary(api_manager)

            # Raise error if all the API calls fail
            if not is_success:
                raise TeamCymruScoutException(enrich_ips.error)

            # loop over the all the address entities and enrich them using the previous dict
            for entity in siemplify.target_entities:
                try:
                    if entity.entity_type == EntityTypes.ADDRESS:
                        # Check if the entity was already enriched in the last 24 hrs
                        if is_entity_already_enriched(entity, siemplify.LOGGER):
                            siemplify.LOGGER.info(
                                ALREADY_ENRICHED_MSG.format(entity.identifier),
                            )
                            output_message += (
                                ALREADY_ENRICHED_MSG.format(entity.identifier) + "\n"
                            )
                            continue

                        enrichment_data = enrich_ips.get_enrichment_data(
                            entity.identifier,
                        )
                        rating = enrichment_data["rating"]
                        entity.is_suspicious = rating in {"malicious", "suspicious"}

                        enrichment_data = add_prefix_to_dict(enrichment_data, "TCS")
                        entity.additional_properties.update(enrichment_data)
                        entity.is_enriched = True

                        successful_entities.append(entity)
                        siemplify.LOGGER.info(
                            f"Finished processing entity {entity.identifier}",
                        )

                except Exception as e:
                    siemplify.LOGGER.error(
                        f"An error occurred on entity {entity.identifier}\nResponse: {e!s}",
                    )
                    siemplify.LOGGER.exception(e)
                    failed_entities.append(entity)

            if successful_entities:
                entities_names = [entity.identifier for entity in successful_entities]
                output_message += "Successfully processed entities: \n{}\n".format(
                    "\n".join(entities_names),
                )

                siemplify.update_entities(successful_entities)

            if enrich_ips.error:
                output_message += f"Could not fetch data from {INTEGRATION_NAME}: \n{enrich_ips.error}\n"

            if failed_entities:
                output_message += "Failed processing entities: \n{}\n".format(
                    "\n".join([entity.identifier for entity in failed_entities]),
                )

            siemplify.result.add_result_json(enrich_ips.summary)

    except Exception as e:
        is_success = False
        response = str(e)
        siemplify.LOGGER.error(
            f"General error performing action {ENRICH_IPS_SCRIPT_NAME}.",
        )
        siemplify.LOGGER.exception(response)

        status = EXECUTION_STATE_FAILED
        output_message = f"Failed to enrich Address Entities!\nError: {response}"

    result_value = bool(is_success)

    siemplify.LOGGER.info(f"Status: {status}")
    siemplify.LOGGER.info(f"Result: {result_value}")
    siemplify.LOGGER.info(f"Output Message: {output_message}")

    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()
