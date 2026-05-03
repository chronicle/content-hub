from __future__ import annotations
from soar_sdk.SiemplifyUtils import output_handler
from soar_sdk.SiemplifyAction import SiemplifyAction
from ..core.ElasticaCloudSOCManager import ElasticaCloudSOCManager
from soar_sdk.SiemplifyUtils import dict_to_flat, construct_csv, convert_dict_to_json_result_dict
from soar_sdk.SiemplifyDataModel import EntityTypes
import arrow

ELASTICA_PROVIDER = "ElasticaCloudSOC"
ACTION_SCRIPT_NAME = "ElasticaCloudSOC_Get_User_Activity"


@output_handler
def main():
    # Configurations.
    siemplify = SiemplifyAction()
    conf = siemplify.get_configuration(ELASTICA_PROVIDER)
    verify_ssl = conf.get("Verify SSL", "false").lower() == "true"
    elastica_manager = ElasticaCloudSOCManager(
        conf["API Root"], conf["Key ID"], conf["Key Secret"], verify_ssl
    )
    siemplify.script_name = ACTION_SCRIPT_NAME

    # Parameters.
    minutes_back = int(siemplify.parameters.get("Minutes Back", 60))

    # Variables.
    errors = []
    succeeded_entities = []
    results_json = {}
    result_value = False

    # Time to fetch from.
    time_to_fetch_from = arrow.now().shift(minutes=-minutes_back)

    target_users = [
        entity
        for entity in siemplify.target_entities
        if entity.entity_type == EntityTypes.USER
    ]

    for user in target_users:
        try:
            # The user_name is case sensitive - therefor the usage of OriginalIdentifier
            result = elastica_manager.get_user_investigation_logs_since_time(
                user_name=user.additional_properties.get("OriginalIdentifier"),
                creation_arrow_timestamp=time_to_fetch_from,
            )
            if result:
                results_json[entity.identifier] = result
                flat_results = list(map(dict_to_flat, result))
                csv_result = construct_csv(flat_results)
                siemplify.result.add_entity_table(user.identifier, csv_result)
                succeeded_entities.append(user)
                result_value = True

        except Exception as err:
            error_message = (
                f'Error fetching logs for user "{user.identifier}", ERROR: {str(err)}'
            )
            errors.append(error_message)
            siemplify.LOGGER.error(error_message)
            siemplify.LOGGER.exception(err)

    if result_value:
        output_message = f'Found activities for: {" , ".join([entity.identifier for entity in succeeded_entities])}'
    else:
        output_message = "Not found activities for target entities."

    if errors:
        output_message += "\n\nErrors:\n{0}".format("\n".join(errors))

    siemplify.result.add_result_json(convert_dict_to_json_result_dict(results_json))
    siemplify.end(output_message, result_value)


if __name__ == "__main__":
    main()
