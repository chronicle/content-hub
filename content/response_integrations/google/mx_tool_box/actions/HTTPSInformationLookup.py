from __future__ import annotations
from soar_sdk.SiemplifyUtils import output_handler
from soar_sdk.SiemplifyDataModel import EntityTypes
from soar_sdk.SiemplifyAction import SiemplifyAction
from ..core.MXToolBoxManager import MXToolBoxManager
from soar_sdk.SiemplifyUtils import construct_csv, get_domain_from_entity

MXTOOLBOX_PROVIDER = "MXToolBox"
SCRIPT_NAME = "MXToolBox_HTTPS_Lookup"
TABLE_HEADER = "HTTPS Information Lookup Result"


@output_handler
def main():
    # Configurations.
    siemplify = SiemplifyAction()
    siemplify.script_name = SCRIPT_NAME
    conf = siemplify.get_configuration(MXTOOLBOX_PROVIDER)
    verify_ssl = conf["Verify SSL"].lower() == "true"
    mx_tool_box_manager = MXToolBoxManager(
        conf["API Root"], conf["API Key"], verify_ssl
    )

    # Variables.
    errors = []
    success_entities = []
    results_list = []
    result_value = False
    certificates = []
    json_results = {}

    domain_entities = [
        entity
        for entity in siemplify.target_entities
        if entity.entity_type == EntityTypes.URL
    ]

    for domain_entity in domain_entities:
        try:
            result = mx_tool_box_manager.domain_https_lookup(
                get_domain_from_entity(domain_entity)
            )
            if result:
                json_results[domain_entity.identifier] = result
                success_entities.append(domain_entity)
                result_value = True
                results_list.append(
                    {
                        "Domain": domain_entity.identifier,
                        "List of certificate authorities": " | ".join(
                            [record.get("Name") for record in result]
                        ),
                    }
                )
                certificates.extend([record.get("Name") for record in result])

        except Exception as e:
            # An error occurred - skip entity and continue
            error_message = (
                f"An error occurred on entity: {domain_entity.identifier}.\n{str(e)}."
            )
            siemplify.LOGGER.error(error_message)
            siemplify.LOGGER.exception(e)
            errors.append(error_message)

    if results_list:
        siemplify.result.add_data_table(TABLE_HEADER, construct_csv(results_list))
    if result_value:
        output_message = f"{','.join([entity.identifier for entity in success_entities])} checked for SSL and returned: {','.join(certificates)}"
    else:
        output_message = "Not found data for target entities."

    if errors:
        output_message = "{0}  \n \n {1}".format(output_message, " \n ".join(errors))

    # add json
    siemplify.result.add_result_json(json_results)

    siemplify.end(output_message, result_value)


if __name__ == "__main__":
    main()
