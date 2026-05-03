from __future__ import annotations
from soar_sdk.SiemplifyUtils import output_handler
from soar_sdk.SiemplifyDataModel import EntityTypes
from soar_sdk.SiemplifyAction import SiemplifyAction
from ..core.MXToolBoxManager import MXToolBoxManager
from soar_sdk.SiemplifyUtils import (
    construct_csv,
    get_domain_from_entity,
    convert_dict_to_json_result_dict,
)

MXTOOLBOX_PROVIDER = "MXToolBox"
SCRIPT_NAME = "MXToolBox_Ping_Lookup"
SUCCESS_STRING = "Success"
TABLE_HEADER = "Ping Results"


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
    ping_results = []
    result_value = False
    results_list = []
    json_results = {}

    target_entities = [
        entity
        for entity in siemplify.target_entities
        if entity.entity_type == EntityTypes.ADDRESS
        or entity.entity_type == EntityTypes.URL
        or entity.entity_type == EntityTypes.USER
        or entity.entity_type == EntityTypes.HOSTNAME
    ]

    for entity in target_entities:
        try:
            if not entity.entity_type == EntityTypes.ADDRESS:
                result = mx_tool_box_manager.entity_ping_lookup(
                    get_domain_from_entity(entity)
                )
            else:
                result = mx_tool_box_manager.entity_ping_lookup(entity.identifier)
            if result:
                json_results[entity.identifier] = result
                # Count success pings.
                pings_amount = len(result)
                success_pings_amount = len(
                    [ping for ping in result if ping.get("Reply") == SUCCESS_STRING]
                )
                results_list.append(
                    {
                        "Domain/IP": entity.identifier,
                        "Packets Sent": pings_amount,
                        "Packets Received": success_pings_amount,
                    }
                )
                ping_results.append(success_pings_amount)
                success_entities.append(entity)
                result_value = True

        except Exception as e:
            # An error occurred - skip entity and continue
            error_message = (
                f"An error occurred on entity: {entity.identifier}.\n{str(e)}."
            )
            siemplify.LOGGER.error(error_message)
            siemplify.LOGGER.exception(e)
            errors.append(error_message)

    if results_list:
        siemplify.result.add_data_table(TABLE_HEADER, construct_csv(results_list))
    if result_value:
        output_message = f"Ping sent successfully to the following entities: {', '.join([entity.identifier for entity in success_entities])}"
    else:
        output_message = "Not found data for target entities."

    if errors:
        output_message = "{0}  \n \n {1}".format(output_message, " \n ".join(errors))

    # add json
    siemplify.result.add_result_json(convert_dict_to_json_result_dict(json_results))

    siemplify.end(output_message, ",".join(map(str, ping_results)))


if __name__ == "__main__":
    main()
