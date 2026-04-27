from __future__ import annotations
from soar_sdk.SiemplifyUtils import output_handler
from soar_sdk.SiemplifyDataModel import EntityTypes
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import (
    dict_to_flat,
    flat_dict_to_csv,
    add_prefix_to_dict_keys,
    convert_dict_to_json_result_dict,
)
from ..core.ThreatCrowdManager import (
    ThreatCrowdManager,
    ADDRESS_TYPE,
    DOMAIN_TYPE,
    MALICIOUS_VOTE,
)

SCRIPT_NAME = "ThreatCrowd - EnrichEntities"


def enrich_entity(report, web_link, entity, siemplify):
    # Enrich target entity with ThreatCrowd info and add web link with full details to entity
    flat_report = dict_to_flat(report)
    siemplify.result.add_entity_table(
        entity.identifier,
        flat_dict_to_csv(flat_report)
    )
    flat_report = add_prefix_to_dict_keys(flat_report, "ThreatCrowd")
    siemplify.result.add_entity_link(entity.identifier, web_link)
    entity.additional_properties.update(flat_report)
    if report.get("votes") == MALICIOUS_VOTE:
        entity.is_suspicious = True
    entity.is_enriched = True
    return True


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = SCRIPT_NAME

    conf = siemplify.get_configuration("ThreatCrowd")
    use_ssl = conf["Use SSL"].lower() == "true"
    threat_crowd_manager = ThreatCrowdManager(use_ssl)

    enriched_entities = []
    json_results = {}

    for entity in siemplify.target_entities:
        try:
            scan_report = {}
            if entity.entity_type == EntityTypes.ADDRESS:
                scan_report = threat_crowd_manager.get_report(
                    entity.identifier.lower(), ADDRESS_TYPE
                )

            if entity.entity_type == EntityTypes.HOSTNAME:
                scan_report = threat_crowd_manager.get_report(
                    entity.identifier.lower(), DOMAIN_TYPE
                )

            if scan_report:
                json_results[entity.identifier] = scan_report
                link = scan_report.get("permalink", "No Link")
                enrich_entity(scan_report, link, entity, siemplify)
                enriched_entities.append(entity)
        except Exception as e:
            # An error occurred - skip entity and continue
            siemplify.LOGGER.error(
                f"An error occurred on entity: {entity.identifier}.\n{str(e)}."
            )
            siemplify.LOGGER._log.exception(e)

    if enriched_entities:
        output_message = (
            f"Following entities were enriched by ThreatCrowd. \n{enriched_entities}"
        )
        result_value = "true"
        siemplify.update_entities(enriched_entities)
    else:
        output_message = "No entities were enriched."
        result_value = "false"

    # add json
    siemplify.result.add_result_json(
        convert_dict_to_json_result_dict(json_results)
    )
    siemplify.end(output_message, result_value)


if __name__ == "__main__":
    main()
