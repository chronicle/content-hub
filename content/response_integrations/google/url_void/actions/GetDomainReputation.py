from __future__ import annotations
from soar_sdk.SiemplifyUtils import output_handler
from soar_sdk.SiemplifyDataModel import EntityTypes
from soar_sdk.SiemplifyAction import SiemplifyAction
from ..core.URLVoidManager import URLVoidManager
from soar_sdk.ScriptResult import EXECUTION_STATE_FAILED, EXECUTION_STATE_COMPLETED
from soar_sdk.SiemplifyUtils import (
    construct_csv,
    create_entity_json_result_object,
    add_prefix_to_dict,
    get_domain_from_entity,
    dict_to_flat,
)
import copy

TRIGGER = "URLVoid"
SCRIPT_NAME = "URLVoid - Get domain Reputation"
INSIGHT_MSG = "Country: {0}"


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = SCRIPT_NAME
    conf = siemplify.get_configuration("URLVoid")
    api_root = conf["ApiUrl"]
    api_key = conf["ApiKey"]
    verify_ssl = conf.get("Verify SSL", "False").lower() == "true"

    threshold = siemplify.parameters.get("Threshold", 0)

    urlvoid_manager = URLVoidManager(api_root, api_key, verify_ssl=verify_ssl)

    enriched_entities = []
    missing_entities = []
    failed_entities = []
    json_results = []
    output_message = ""
    action_state = EXECUTION_STATE_COMPLETED

    for entity in siemplify.target_entities:
        domain = None

        if entity.entity_type == EntityTypes.HOSTNAME:
            domain = entity.identifier

        elif entity.entity_type == EntityTypes.URL:
            domain = get_domain_from_entity(entity)

        if domain:
            try:
                reputation = urlvoid_manager.get_domain_reputation(domain)

                if reputation:
                    blacklist_report = (
                        urlvoid_manager.create_blacklist_report_from_raw_data(
                            reputation
                        )
                    )

                    enrichment_data = copy.deepcopy(reputation)
                    enrichment_data.pop("blacklists")
                    server_info = enrichment_data.pop("server")
                    enrichment_data.update(server_info)
                    enrichment_data = dict_to_flat(enrichment_data)

                    siemplify.result.add_entity_table(
                        entity.identifier, construct_csv(blacklist_report)
                    )

                    if enrichment_data.get("country_code"):
                        siemplify.add_entity_insight(
                            entity,
                            INSIGHT_MSG.format(enrichment_data.get("country_code")),
                            triggered_by=TRIGGER,
                        )

                    reputation["blacklists"]["engines"] = blacklist_report

                    enrichment_data = add_prefix_to_dict(enrichment_data, "URLVoid")
                    entity.additional_properties.update(enrichment_data)

                    json_results.append(
                        create_entity_json_result_object(entity.identifier, reputation)
                    )

                    if int(reputation.get("blacklists", {}).get("detections")) > int(
                        threshold
                    ):
                        entity.is_suspicious = True

                    entity.is_enriched = True
                    enriched_entities.append(entity)

                else:
                    missing_entities.append(entity)

            except Exception as e:
                failed_entities.append(entity)
                # An error occurred - skip entity and continue
                siemplify.LOGGER.error(
                    f"An error occurred on entity: {entity.identifier}.\n{str(e)}."
                )
                siemplify.LOGGER.exception(e)

    if enriched_entities:
        entities_names = [entity.identifier for entity in enriched_entities]

        output_message += (
            "URLVoid: Fetched reputation for the following entities:\n{}\n".format(
                "\n".join(entities_names)
            )
        )

        siemplify.update_entities(enriched_entities)

    if failed_entities:
        output_message += "An error occurred on the following entities:\n{}\n".format(
            "\n".join([entity.identifier for entity in failed_entities])
        )
        action_state = EXECUTION_STATE_FAILED

    if missing_entities:
        output_message += "No reputation found for the following entities:\n{}".format(
            "\n".join([entity.identifier for entity in missing_entities])
        )

    if not missing_entities and not failed_entities and not enriched_entities:
        output_message = "URLVoid: No entities were enriched."

    siemplify.result.add_result_json(json_results)
    siemplify.end(output_message, "true", action_state)


if __name__ == "__main__":
    main()
