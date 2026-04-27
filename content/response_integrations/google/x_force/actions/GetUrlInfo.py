from __future__ import annotations
from soar_sdk.SiemplifyUtils import output_handler
from soar_sdk.SiemplifyDataModel import EntityTypes
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import (
    add_prefix_to_dict_keys,
    construct_csv,
    convert_dict_to_json_result_dict,
)
from ..core.XForceManager import XForceManager, XForceNotFoundError, XForceAccessDeniedError
import json

URL = EntityTypes.URL
SCRIPT_NAME = "IBM XForce - Get Url Info"


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = SCRIPT_NAME

    conf = siemplify.get_configuration("XForce")
    address = conf["Address"]
    api_key = conf["Api Key"]
    api_password = conf["Api Password"]
    verify_ssl = conf["Verify SSL"].lower() == "true"

    xf_manager = XForceManager(api_key, api_password, address, verify_ssl=verify_ssl)
    threshold = (
        int(siemplify.parameters.get("Threshold"))
        if siemplify.parameters.get("Threshold")
        else 1
    )

    risk_score = 0
    enriched_entities = []
    csv_results = []
    entities_with_score = {}
    output_message = ""
    is_risk = "false"
    json_results = {}
    encoding_format = "utf-8"

    not_found_entities = []
    access_denied = []
    not_enriched_entities = []

    for entity in siemplify.target_entities:
        if entity.entity_type == URL:
            try:
                entity_encoded_id = entity.identifier.encode(encoding_format)
                report = xf_manager.get_url_info(entity_encoded_id)
                if report:
                    json_results[entity_encoded_id] = report
                    risk_score = report.get("result").get("score") or 0
                    categories_list = (
                        list(
                            report.get("result", {})
                            .get("categoryDescriptions", {})
                            .keys()
                        )
                        or []
                    )
                    categories = "| ".join(
                        str(category) for category in categories_list
                    )

                    # Attach report
                    siemplify.result.add_entity_json(
                        entity_encoded_id, json.dumps(report)
                    )

                    # Build csv table (URL - Score - Categories(comma separated))
                    csv_results.append(
                        {
                            "URL": entity_encoded_id,
                            "Score": float(risk_score),
                            "Categories": categories,
                        }
                    )

                    # Enrich - Score and Categories (comma separated)
                    flat_report = add_prefix_to_dict_keys(
                        {"Score": float(risk_score), "Categories": categories},
                        "IBM_XForce",
                    )
                    entity.additional_properties.update(flat_report)
                    entity.is_enriched = True

                    # Add Insight and mark as suspicious if risk score exceed threshold
                    if int(threshold) < risk_score:
                        entity.is_suspicious = True
                        is_risk = True
                        insight_msg = (
                            f"IBM XForce - {entity_encoded_id} marked as suspicious"
                        )
                        siemplify.add_entity_insight(
                            entity, insight_msg, triggered_by="XForce"
                        )

                    entities_with_score.update({entity_encoded_id: risk_score})
                    enriched_entities.append(entity)

            except XForceNotFoundError as e:
                siemplify.LOGGER.error(
                    f"An error occurred on entity: {entity_encoded_id}.\n{str(e)}."
                )
                siemplify.LOGGER.exception(e)
                not_found_entities.append(entity_encoded_id)

            except XForceAccessDeniedError as e:
                siemplify.LOGGER.error(
                    f"An error occurred on entity: {entity_encoded_id}.\n{str(e)}."
                )
                siemplify.LOGGER.exception(e)
                access_denied.append(entity_encoded_id)

            except Exception as e:
                # An error occurred - skip entity and continue
                siemplify.LOGGER.error(
                    f"An error occurred on entity: {entity_encoded_id}.\n{str(e)}."
                )
                siemplify.LOGGER.exception(e)
                not_enriched_entities.append(entity_encoded_id)

    if csv_results:
        # Add csv table
        siemplify.result.add_data_table("Report", construct_csv(csv_results))

    if entities_with_score:
        output_message = "The following entities were enriched \n"
        for url, score in list(entities_with_score.items()):
            output_message = f"{output_message} {url} returned risk score: {score} \n"
        siemplify.update_entities(enriched_entities)

    if not_found_entities:
        output_message += (
            "The following entities were not found in IBM X-Force: {0} \n".format(
                "\n".join(not_found_entities)
            )
        )

    if access_denied:
        output_message += "The following entities were not enriched - Access was denied: {0} \n".format(
            "\n".join(access_denied)
        )

    if not_enriched_entities:
        output_message += (
            "The following entities were not enriched - API error: {0} \n".format(
                "\n".join(not_enriched_entities)
            )
        )

    siemplify.result.add_result_json(convert_dict_to_json_result_dict(json_results))
    siemplify.end(output_message, is_risk)


if __name__ == "__main__":
    main()
