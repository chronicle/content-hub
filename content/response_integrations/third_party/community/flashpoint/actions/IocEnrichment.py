from __future__ import annotations

import json

from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import (
    add_prefix_to_dict,
    convert_dict_to_json_result_dict,
    output_handler,
)

from ..core.FlashpointManager import FlashpointManager, dict_to_flat

SCRIPT_NAME = "Flashpoint - IOC Enrichment"

# The sorting can be 'des' for descending and 'asc' ascending
SORT_RESULTS_TIMESTAMP = "desc"


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = SCRIPT_NAME

    conf = siemplify.get_configuration("Flashpoint")
    api_key = conf["API Key"]

    results_limit = siemplify.extract_action_param("Limit")

    flashpoint_manager = FlashpointManager(api_key)

    enriched_entities = []
    output_message = ""
    json_results = {}
    not_found_entities = []
    ioc_info_flat = {}
    result_value = False

    for entity in siemplify.target_entities:
        try:
            report = flashpoint_manager.IOC_Enrichment(
                entity.identifier,
                results_limit,
                SORT_RESULTS_TIMESTAMP,
            )
            if report:
                # Attach report
                siemplify.result.add_entity_json(
                    f"The entity {entity.identifier} was enriched",
                    json.dumps(report),
                )
                ioc_info_flat = dict_to_flat(report[0])

                # adding the FlashPoint prefix to each entity detail to enable the analysis of the entity data
                ioc_info_flat = add_prefix_to_dict(ioc_info_flat, "FlashPoint")
                entity.additional_properties.update(ioc_info_flat)
                entity.is_enriched = True

                # Add Insight and mark as suspicious if risk score exceed threshold
                entity.is_suspicious = True
                result_value = True
                insight_msg = f"Flashpoint - {entity.identifier} marked as suspicious"
                siemplify.add_entity_insight(
                    entity,
                    insight_msg,
                    triggered_by="Flashpoint",
                )
                json_results[entity.identifier] = report
                enriched_entities.append(entity)

            else:
                not_found_entities.append(entity.identifier)

        except Exception as e:
            # An error occurred - skip entity and continue
            siemplify.LOGGER.error(
                f"An error occurred on entity: {entity.identifier}.\n{e!s}.",
            )
            siemplify.LOGGER.exception(e)

    if not_found_entities:
        output_message += (
            "The following entities were not found in Flashpoint: {0}.".format(
                "\n".join(not_found_entities),
            )
        )

    siemplify.result.add_result_json(convert_dict_to_json_result_dict(json_results))
    siemplify.end(output_message, result_value)


if __name__ == "__main__":
    main()
