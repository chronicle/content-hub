from __future__ import annotations
from soar_sdk.SiemplifyUtils import output_handler
from soar_sdk.SiemplifyDataModel import EntityTypes
from soar_sdk.SiemplifyAction import SiemplifyAction
from ..core.TenableManager import TenableSecurityCenterManager
from soar_sdk.SiemplifyUtils import convert_dict_to_json_result_dict

SCRIPT_NAME = "TenableSecurityCenter - EnrichIP"


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = SCRIPT_NAME
    conf = siemplify.get_configuration("TenableSecurityCenter")
    server_address = conf["Server Address"]
    username = conf.get("Username")
    password = conf.get("Password")
    access_key = conf.get("Access Key")
    secret_key = conf.get("Secret Key")
    use_ssl = conf["Use SSL"].lower() == "true"
    repo_name = siemplify.parameters["Repository Name"]

    tenable_manager = TenableSecurityCenterManager(
        server_address,
        username,
        password,
        access_key,
        secret_key,
        use_ssl,
    )

    affected_entities = []
    json_results = {}

    for entity in siemplify.target_entities:
        try:
            if entity.entity_type == EntityTypes.ADDRESS:
                assets = tenable_manager.get_ip_related_assets(
                    entity.identifier, repo_name
                )
                json_results[entity.identifier] = assets

                csv_output = tenable_manager.construct_csv(assets)
                siemplify.result.add_data_table(entity.identifier, csv_output)

                affected_entities.append(entity)

        except Exception as e:
            # An error occurred - skip entity and continue
            siemplify.LOGGER.error(
                f"An error occurred on entity: {entity.identifier}.\n{str(e)}."
            )
            siemplify.LOGGER._log.exception(e)

    if affected_entities:
        entities_names = [entity.identifier for entity in affected_entities]
        output_message = (
            "Tenable: Assets were found for the following entities:\n"
            + "\n".join(entities_names)
        )
        siemplify.update_entities(affected_entities)

    else:
        output_message = "Tenable: No assets were found."

    siemplify.result.add_result_json(convert_dict_to_json_result_dict(json_results))
    siemplify.end(output_message, "true")


if __name__ == "__main__":
    main()
