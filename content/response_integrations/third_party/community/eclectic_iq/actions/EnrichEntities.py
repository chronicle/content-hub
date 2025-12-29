from __future__ import annotations

from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import convert_dict_to_json_result_dict, output_handler
from TIPCommon import construct_csv

from ..core.EclecticIQManager import EclecticIQManager

INTEGRATION_NAME = "EclecticIQ"
SCRIPT_NAME = "Enrich Entities"


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.LOGGER.info("================= Main - Param Init =================")

    configs = siemplify.get_configuration(INTEGRATION_NAME)

    eiq_url = configs["EclecticIQ URL"]
    api_token = configs["API Token"]
    verify_ssl = configs["Verify SSL"]

    siemplify.LOGGER.info("----------------- Main - Started -----------------")

    status = EXECUTION_STATE_COMPLETED
    output_message = ""
    result_value = None
    failed_entities = []
    results = []
    missing_entities = []
    json_results = {}
    enriched_entities = []

    try:
        eiq_manager = EclecticIQManager(eiq_url, api_token, verify_ssl)
        result = eiq_manager.enrich([entity for entity in siemplify.target_entities])
        siemplify.result.add_result_json(
            convert_dict_to_json_result_dict(result.parse_as_enrichment()),
        )

        for identifier, link in result.parse_as_link():
            siemplify.result.add_entity_link(
                f"EclecticIQ Platform Link - {identifier}",
                link,
            )
        for identifier, csv_dict in result.parse_as_csv().items():
            siemplify.result.add_entity_table(identifier, construct_csv(csv_dict))

        enriched_entites = result.parse_as_entity()
        siemplify.update_entities(enriched_entites)
        result_value = len(enriched_entites)

        missing_entities = result.missing_entities()
        if missing_entities:
            output_message += (
                "The following Entities were not found in EclecticIQ: \n"
                + "{}".format("\n".join(missing_entities))
            )

    except Exception as e:
        siemplify.LOGGER.error(f"General error performing action {SCRIPT_NAME}")
        siemplify.LOGGER.exception(e)
        status = EXECUTION_STATE_FAILED
        result_value = "Failed"
        output_message += "\n unknown failure"

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(
        f"\n  status: {status}\n  result_value: {result_value}\n  output_message: {output_message}",
    )
    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()
