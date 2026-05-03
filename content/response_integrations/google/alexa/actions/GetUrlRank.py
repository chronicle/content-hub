from __future__ import annotations
from soar_sdk.SiemplifyUtils import output_handler
from soar_sdk.SiemplifyDataModel import EntityTypes
from ..core.AlexaManager import AlexaManager
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import convert_dict_to_json_result_dict


@output_handler
def main():
    siemplify = SiemplifyAction()
    conf = siemplify.get_configuration("Alexa")
    access_key_id = conf["Access key id"]
    secret_access_key = conf["Secret access key"]
    alexa = AlexaManager(access_key_id, secret_access_key)

    urls_to_enrich = []
    urls_rank = {}
    json_result = {}
    result_value = "false"

    for entity in siemplify.target_entities:
        if entity.entity_type == EntityTypes.URL:
            res = alexa.get_url_info(entity.identifier, "Rank")
            json_result[entity.identifier] = res
        else:
            continue
        if res:
            if res["TrafficData"][0]["Rank"][0].get("text"):
                rank = res["TrafficData"][0]["Rank"][0]["text"]

            else:
                rank = "None"

            urls_rank.update({entity.identifier: rank})
            entity.additional_properties["Alexa_Rank"] = rank
            urls_to_enrich.append(entity)
            entity.is_enriched = True
            if int(siemplify.parameters["Threshold"]) < rank:
                entity.is_suspicious = True
                result_value = "true"
                siemplify.add_entity_insight(entity, "Found as suspicious by Alexa.")

    if urls_to_enrich:
        message = "Following domains were enriched by Alexa.\n"
        for identifier, rank in list(urls_rank.items()):
            message += f"{identifier}: Rank: {rank}\n"
        output_message = message
        siemplify.update_entities(urls_to_enrich)
    else:
        output_message = "No entities were enriched."

    siemplify.result.add_result_json(convert_dict_to_json_result_dict(json_result))
    siemplify.end(output_message, result_value)


if __name__ == "__main__":
    main()
