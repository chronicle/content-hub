from __future__ import annotations
from soar_sdk.SiemplifyUtils import (
    output_handler,
    unix_now,
    convert_unixtime_to_datetime,
    convert_dict_to_json_result_dict,
)
from soar_sdk.SiemplifyDataModel import EntityTypes
from soar_sdk.SiemplifyAction import SiemplifyAction
from TIPCommon import extract_configuration_param
from soar_sdk.ScriptResult import (
    EXECUTION_STATE_COMPLETED,
    EXECUTION_STATE_FAILED,
    EXECUTION_STATE_TIMEDOUT,
)
from ..core.ActiveDirectoryManager import ActiveDirectoryManager

# =====================================
#             CONSTANTS               #
# =====================================
INTEGRATION_NAME = "ActiveDirectory"
SCRIPT_NAME = "ActiveDirectory - GetManagerContactDetails"
CONTACT_FIELD = "telephoneNumber"
SUPPORTED_ENTITY_TYPES = [EntityTypes.USER]
TABLE_HEADER = "Manager Contact: {}"


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = SCRIPT_NAME
    output_message = ""
    result_value = False
    successful_entities = []
    failed_entities = []
    successful_entities_without_manager = []
    missing_entities = []
    status = EXECUTION_STATE_COMPLETED

    siemplify.LOGGER.info("----------------- Main - Param Init -----------------")

    # INIT INTEGRATION CONFIGURATIONS:
    server = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        is_mandatory=True,
        param_name="Server",
        input_type=str,
    )
    username = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        is_mandatory=True,
        param_name="Username",
        input_type=str,
    )
    password = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        is_mandatory=True,
        param_name="Password",
        input_type=str,
    )
    domain = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        is_mandatory=True,
        param_name="Domain",
        input_type=str,
    )
    use_ssl = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        is_mandatory=True,
        param_name="Use SSL",
        input_type=bool,
    )
    custom_query_fields = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Custom Query Fields",
        input_type=str,
    )
    ca_certificate = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="CA Certificate File - parsed into Base64 String",
    )

    siemplify.LOGGER.info("----------------- Main - Started -----------------")
    try:
        manager = ActiveDirectoryManager(
            server,
            domain,
            username,
            password,
            use_ssl,
            custom_query_fields,
            ca_certificate,
            siemplify.LOGGER,
        )
        target_entities = [
            entity
            for entity in siemplify.target_entities
            if entity.entity_type in SUPPORTED_ENTITY_TYPES
        ]
        json_results = {}
        if target_entities:
            for entity in target_entities:
                siemplify.LOGGER.info(f"Started processing entity: {entity.identifier}")
                if unix_now() >= siemplify.execution_deadline_unix_time_ms:
                    siemplify.LOGGER.error(
                        f"Timed out. execution deadline ({convert_unixtime_to_datetime(siemplify.execution_deadline_unix_time_ms)}) has passed"
                    )
                    status = EXECUTION_STATE_TIMEDOUT
                    break
                try:
                    entity_exists, entry_report = manager.enrich_manager_details(
                        entity.identifier
                    )
                    if not entity_exists:
                        siemplify.LOGGER.info(
                            f"Entity {entity.identifier} was not found in AD"
                        )
                        missing_entities.append(entity)
                        continue
                    if not entry_report:
                        siemplify.LOGGER.info(
                            f"No manager found for entity {entity.identifier}"
                        )
                        successful_entities_without_manager.append(entity)

                        continue
                    json_results[entity.identifier] = entry_report.to_json()
                    entity.additional_properties["AD_Manager_Name"] = entry_report.name
                    entity.additional_properties["AD_Manager_phone"] = (
                        entry_report.telephone_num
                    )

                    siemplify.result.add_entity_table(
                        TABLE_HEADER.format(entity.identifier), entry_report.to_csv()
                    )
                    successful_entities.append(entity)
                    siemplify.LOGGER.info(
                        f"Finished processing entity {entity.identifier}"
                    )
                except Exception as e:
                    failed_entities.append(entity)
                    siemplify.LOGGER.error(
                        f"An error occurred on entity {entity.identifier}"
                    )
                    siemplify.LOGGER.exception(e)

        else:
            output_message = "No suitable entities found.\n"
            siemplify.LOGGER.info("No suitable entities found.\n")
    except Exception as e:
        siemplify.LOGGER.error(
            f"General error performing action {SCRIPT_NAME}. Error: {e}"
        )
        siemplify.LOGGER.exception(e)
        status = EXECUTION_STATE_FAILED
        result_value = False
        output_message = f"General error performing action {SCRIPT_NAME}. Error: {e}"

    if successful_entities:
        output_message += "\nSuccessfully processed entities:\n   {}".format(
            "\n   ".join([entity.identifier for entity in successful_entities])
        )
        result_value = True
        siemplify.result.add_result_json(convert_dict_to_json_result_dict(json_results))

    if successful_entities_without_manager:
        output_message += (
            "\nSuccessfully processed entities but no managers found:\n   {}".format(
                "\n   ".join(
                    [
                        entity.identifier
                        for entity in successful_entities_without_manager
                    ]
                )
            )
        )

    if failed_entities and len(failed_entities) != len(target_entities):
        output_message += "\nFailed processing entities:\n   {}".format(
            "\n   ".join([entity.identifier for entity in failed_entities])
        )

    if missing_entities:
        output_message += "\nThe following entities were not found in Active Directory:\n   {}".format(
            "\n   ".join([entity.identifier for entity in missing_entities])
        )

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(
        f"\n  status: {status}\n  result_value: {result_value}\n  output_message: {output_message}"
    )
    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()
