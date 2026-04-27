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

ADDRESS = EntityTypes.ADDRESS
SCRIPT_NAME = "IBM XForce - Get IP Info"


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

    enriched_entities = []
    csv_results = []
    entities_with_score = {}
    output_message = ""
    is_risk = "false"
    json_results = {}

    not_found_entities = []
    access_denied = []
    not_enriched_entities = []

    for entity in siemplify.target_entities:
        if entity.entity_type == ADDRESS and not entity.is_internal:
            try:
                report = xf_manager.get_ip_info(entity.identifier)
                if report:
                    json_results[entity.identifier] = report
                    risk_score = report.get("score") or 0
                    categories_list = (
                        list(report.get("categoryDescriptions").keys()) or []
                    )
                    categories = "| ".join(
                        str(category) for category in categories_list
                    )
                    country = report.get("geo", {}).get("country") or ""

                    # Attach report
                    siemplify.result.add_entity_json(
                        entity.identifier, json.dumps(report)
                    )

                    # Build summary csv table (IP - Score - Categories(| separated) - Country)
                    csv_results.append(
                        {
                            "IP": entity.identifier,
                            "Score": float(risk_score),
                            "Categories": categories,
                            "Country": country,
                        }
                    )

                    # Build entity table (history) IP - Created - Country - Score)
                    entity_csv = []
                    for history in report.get("history"):
                        entity_csv.append(
                            {
                                "IP": history.get("ip") or "",
                                "Created": history.get("created") or "",
                                "Country": history.get("geo", {}).get("country") or "",
                                "Score": history.get("score") or 0,
                            }
                        )

                    # Add entity csv table
                    siemplify.result.add_entity_table(
                        entity.identifier, construct_csv(entity_csv)
                    )

                    # Enrich - Country, Score and Categories (comma separated)
                    flat_report = add_prefix_to_dict_keys(
                        {
                            "Score": float(risk_score),
                            "Categories": categories,
                            "Country": country,
                        },
                        "IBM_XForce",
                    )
                    entity.additional_properties.update(flat_report)
                    entity.is_enriched = True

                    # Add Insight and mark as suspicious if risk score exceed threshold
                    if int(threshold) < risk_score:
                        entity.is_suspicious = True
                        is_risk = "true"
                        insight_msg = (
                            f"IBM XForce - {entity.identifier} marked as suspicious"
                        )
                        siemplify.add_entity_insight(
                            entity, insight_msg, triggered_by="XForce"
                        )

                    entities_with_score.update({entity.identifier: risk_score})
                    enriched_entities.append(entity)

            except XForceNotFoundError as e:
                siemplify.LOGGER.error(
                    f"An error occurred on entity: {entity.identifier}.\n{str(e)}."
                )
                siemplify.LOGGER.exception(e)
                not_found_entities.append(entity.identifier)

            except XForceAccessDeniedError as e:
                siemplify.LOGGER.error(
                    f"An error occurred on entity: {entity.identifier}.\n{str(e)}."
                )
                siemplify.LOGGER.exception(e)
                access_denied.append(entity.identifier)

            except Exception as e:
                # An error occurred - skip entity and continue
                siemplify.LOGGER.error(
                    f"An error occurred on entity: {entity.identifier}.\n{str(e)}."
                )
                siemplify.LOGGER.exception(e)
                not_enriched_entities.append(entity.identifier)

    if csv_results:
        # Add csv table
        siemplify.result.add_data_table("Summary", construct_csv(csv_results))

    if entities_with_score:
        output_message = "The following entities were enriched \n"
        for ip, score in list(entities_with_score.items()):
            output_message = f"{output_message} {ip} returned risk score: {score} \n"
        siemplify.update_entities(enriched_entities)

    if not_found_entities:
        output_message += "The following entities were not found in IBM X-Force: {0} \nCheck logs for more details.".format(
            "\n".join(not_found_entities)
        )

    if access_denied:
        output_message += "The following entities were not enriched - Access was denied: {0} \nCheck logs for more details.".format(
            "\n".join(access_denied)
        )

    if not_enriched_entities:
        output_message += "Errors occurred. The following entities were not enriched: {0} \nCheck logs for more details.".format(
            "\n".join(not_enriched_entities)
        )

    # add json
    siemplify.result.add_result_json(convert_dict_to_json_result_dict(json_results))
    siemplify.end(output_message, is_risk)


if __name__ == "__main__":
    main()
