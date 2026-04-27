from __future__ import annotations
from soar_sdk.SiemplifyUtils import output_handler
from soar_sdk.SiemplifyDataModel import EntityTypes
from soar_sdk.SiemplifyUtils import convert_dict_to_json_result_dict
from soar_sdk.SiemplifyAction import SiemplifyAction
from ..core.SSLLabsManager import SSLLabsManager
from TIPCommon import extract_configuration_param

INTEGRATION_NAME = "SSLLabs"


@output_handler
def main():
    siemplify = SiemplifyAction()
    conf = siemplify.get_configuration("SSLLabs")
    warning_threshold = conf["Warning Threshold"]
    verify_ssl = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Verify SSL",
        input_type=bool,
        default_value=False,
    )

    ssl_labs_manager = SSLLabsManager(verify_ssl)

    enriched_entities = []
    json_results = {}

    for entity in siemplify.target_entities:
        if (
            entity.entity_type == EntityTypes.URL
            or entity.entity_type == EntityTypes.HOSTNAME
        ):
            results = ssl_labs_manager.analyze_url(entity.identifier)

            if results:
                json_results[entity.identifier] = results

                lowest_grade = "A"

                for endpoint in results["endpoints"]:
                    # In python 'A' < 'B', but in SSL Labs 'B' is worse than 'A'.
                    lowest_grade = max(lowest_grade, endpoint["grade"])

                    # Enrich the entity with the endpoint's grade
                    entity.additional_properties.update(
                        {
                            f'SSL_Labs_{endpoint["ipAddress"]}_Grade': endpoint[
                                "grade"
                            ],
                            f'SSL_Labs_{endpoint["ipAddress"]}_Grade_Trust_Ignored': endpoint[
                                "gradeTrustIgnored"
                            ],
                        }
                    )

                if lowest_grade > warning_threshold:
                    entity.is_suspicious = True

                enriched_entities.append(entity)

    if enriched_entities:
        entities_names = [entity.identifier for entity in enriched_entities]
        output_message = (
            "The following entities were enriched by SSL Labs:\n"
            + "\n".join(entities_names)
        )

        siemplify.update_entities(enriched_entities)

    else:
        output_message = "No entities were enriched."

    siemplify.result.add_result_json(convert_dict_to_json_result_dict(json_results))
    siemplify.end(output_message, "true")


if __name__ == "__main__":
    main()
