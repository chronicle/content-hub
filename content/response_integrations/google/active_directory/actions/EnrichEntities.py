from __future__ import annotations
import json
import sys

from TIPCommon import extract_configuration_param, extract_action_param, construct_csv

from ..core.ActiveDirectoryManager import (
    ActiveDirectoryManager,
    ActiveDirectoryNotExistPropertyError,
    ActiveDirectoryTimeoutError,
)
from soar_sdk.ScriptResult import (
    EXECUTION_STATE_COMPLETED,
    EXECUTION_STATE_FAILED,
    EXECUTION_STATE_INPROGRESS,
)
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyDataModel import EntityTypes
from soar_sdk.SiemplifyUtils import (
    output_handler,
    unix_now,
    convert_unixtime_to_datetime,
    convert_dict_to_json_result_dict,
)
from ..core.utils import (
    load_csv_to_list,
    get_existing_fields_to_enrich,
    filter_nested_dictionary,
    is_action_approaching_timeout,
    is_action_approaching_iteration_run_timeout,
)

# =====================================
#             CONSTANTS               #
# =====================================
INTEGRATION_NAME = "ActiveDirectory"
SCRIPT_NAME = "ActiveDirectory - EnrichEntities"

SUPPORTED_ENTITY_TYPES = [EntityTypes.USER, EntityTypes.HOSTNAME]
CUSTOM_FIELD_VALIDATION_ERROR = (
    "Failed to run search query with the given custom fields. Run query without."
)

TABLE_HEADER = "Report for: {}"


def get_entity_by_entity_identifier(siemplify, entity_identifier, entity_type):
    """
    Get entity by entity identifier
    :param siemplify: SiemplifyAction object.
    :param entity_identifier: {str} Entity Identifier
    :param entity_type: {str} Entity Type
    :return: Siemplify target Entity if found. None otherwise
    """
    for entity in siemplify.target_entities:
        if entity.identifier == entity_identifier and entity.entity_type == entity_type:
            return entity


@output_handler
def main(is_first_run):
    siemplify = SiemplifyAction()
    action_start_time = unix_now()
    siemplify.script_name = SCRIPT_NAME

    mode = "Main" if is_first_run else "Pending Entities"
    siemplify.LOGGER.info(f"----------------- {mode} - Param Init -----------------")

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

    mark_entities_as_internal = extract_action_param(
        siemplify,
        param_name="Mark entities as internal",
        default_value=False,
        input_type=bool,
    )

    attribute_names_to_enrich_with_str = extract_action_param(
        siemplify,
        param_name="Specific Attribute Names To Enrich With",
        default_value=False,
        is_mandatory=False,
        print_value=True,
    )

    should_json_filtered = extract_action_param(
        siemplify,
        param_name="Should JSON result be filtered by the specified Attributes?",
        default_value=False,
        is_mandatory=False,
        print_value=True,
        input_type=bool,
    )

    should_case_wall_table_filtered = extract_action_param(
        siemplify,
        param_name="Should Case Wall Table be filtered by the specified Attributes?",
        default_value=False,
        is_mandatory=False,
        print_value=True,
        input_type=bool,
    )

    siemplify.LOGGER.info(f"----------------- {mode} - Started -----------------")

    status = EXECUTION_STATE_COMPLETED
    output_message = ""

    result_value = {
        "pending": {},
        "failed": [],
        "successful": [],
        "missing_fields": set(),
        "json_results": {},
        "csv_entity_table": [],
        "attribute_names_to_enrich_with": [],
    }

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
        if is_first_run:
            result_value["pending"] = [
                [entity.identifier, entity.entity_type]
                for entity in siemplify.target_entities
                if entity.entity_type in SUPPORTED_ENTITY_TYPES
            ]
            found_supported_entities = True if result_value["pending"] else False
            result_value["attribute_names_to_enrich_with"] = (
                load_csv_to_list(attribute_names_to_enrich_with_str, "Fields to Enrich")
                if attribute_names_to_enrich_with_str
                else None
            )

            result_value["missing_fields"] = (
                set(result_value["attribute_names_to_enrich_with"])
                if result_value["attribute_names_to_enrich_with"]
                else set()
            )
        else:
            result_value = json.loads(
                extract_action_param(siemplify=siemplify, param_name="additional_data")
            )
            found_supported_entities = True
            result_value["missing_fields"] = set(result_value["missing_fields"])

        entities_to_update = []
        is_timeout_approached = False

        if found_supported_entities:
            for entity_identifier, entity_type in result_value["pending"].copy():
                entity = get_entity_by_entity_identifier(
                    siemplify, entity_identifier, entity_type
                )

                # Check if approach total action deadline timeout
                if is_action_approaching_timeout(
                    siemplify.execution_deadline_unix_time_ms
                ):
                    siemplify.LOGGER.error(
                        f"Timed out. Execution deadline ({convert_unixtime_to_datetime(siemplify.execution_deadline_unix_time_ms)}) was approached"
                    )
                    is_timeout_approached = True
                    break

                # Check if approached platform limitation of single action run
                if is_action_approaching_iteration_run_timeout(action_start_time):
                    pending_entities = [
                        entity_identifier
                        for entity_identifier, _ in result_value["pending"]
                    ]
                    result_value["missing_fields"] = list(
                        result_value["missing_fields"]
                    )
                    result_value = json.dumps(result_value)
                    status = EXECUTION_STATE_INPROGRESS
                    output_message = f'Pending entities: {", ".join(pending_entities)}'
                    break

                try:
                    siemplify.LOGGER.info(
                        f"Started processing entity: {entity.identifier}"
                    )
                    entity_report = None
                    if entity.entity_type == EntityTypes.USER:
                        try:
                            entity_report = manager.enrich_user(entity.identifier)
                        except Exception as e:
                            siemplify.LOGGER.exception(e)
                            siemplify.LOGGER.error(CUSTOM_FIELD_VALIDATION_ERROR)
                    else:
                        try:
                            entity_report = manager.enrich_host(entity.identifier)
                        except Exception as e:
                            siemplify.LOGGER.info(CUSTOM_FIELD_VALIDATION_ERROR)
                            siemplify.LOGGER.exception(e)

                    result_value["pending"].remove([entity_identifier, entity_type])

                    if not entity_report:
                        siemplify.LOGGER.info(
                            f"Unable to enrich entity {entity.identifier}"
                        )
                        result_value["failed"].append(entity.identifier)
                        continue

                    enrichment_data = entity_report.to_enrichment_data(prefix="AD")
                    if result_value["attribute_names_to_enrich_with"]:
                        fields_to_enrich, existing_attributes = (
                            get_existing_fields_to_enrich(
                                result_value["attribute_names_to_enrich_with"],
                                enrichment_data.keys(),
                            )
                        )
                        result_value["missing_fields"] = (
                            result_value["missing_fields"] - existing_attributes
                        )
                        filtered_enrichment_data = {
                            key: enrichment_data[key] for key in fields_to_enrich
                        }
                        enrichment_data = filtered_enrichment_data

                    if enrichment_data:
                        entity.additional_properties.update(enrichment_data)
                        entity.is_enriched = True
                        result_value["successful"].append(entity.identifier)
                        entities_to_update.append(entity)
                    else:
                        result_value["failed"].append(entity.identifier)

                    if mark_entities_as_internal:
                        entity.is_internal = True

                    if enrichment_data:
                        if (
                            should_case_wall_table_filtered
                            and result_value["attribute_names_to_enrich_with"]
                        ):
                            csv_table = (
                                entity_report.to_table()[0]
                                if entity_report.to_table()[0]
                                else {}
                            )

                            if csv_table:
                                filtered_csv_table = {
                                    key: value
                                    for key, value in csv_table.items()
                                    if any(
                                        word in key.split("_")
                                        for word in result_value[
                                            "attribute_names_to_enrich_with"
                                        ]
                                    )
                                }

                                result_value["csv_entity_table"].append(
                                    [
                                        TABLE_HEADER.format(entity.identifier),
                                        construct_csv([filtered_csv_table]),
                                    ]
                                )

                        else:
                            result_value["csv_entity_table"].append(
                                [
                                    TABLE_HEADER.format(entity.identifier),
                                    construct_csv(entity_report.to_table()),
                                ]
                            )

                        if (
                            should_json_filtered
                            and result_value["attribute_names_to_enrich_with"]
                        ):
                            json_entity_result = entity_report.to_json()
                            result_value["json_results"][entity.identifier] = (
                                filter_nested_dictionary(
                                    json_entity_result,
                                    result_value["attribute_names_to_enrich_with"],
                                )
                            )

                        else:
                            result_value["json_results"][
                                entity.identifier
                            ] = entity_report.to_json()

                    siemplify.LOGGER.info(
                        f"Finished processing entity {entity.identifier}"
                    )

                except ActiveDirectoryNotExistPropertyError as e:
                    result_value["failed"].append(entity_identifier)
                    siemplify.LOGGER.error(
                        f"An error occurred on entity {entity.identifier}"
                    )
                    siemplify.LOGGER.exception(e)

            if is_timeout_approached and result_value["pending"]:
                raise ActiveDirectoryTimeoutError(
                    "Unable to process the following entities due to timeout:\n   {}\n Please increase time for execution in the IDE".format(
                        "\n   ".join(
                            [
                                entity_identifier
                                for entity_identifier, _ in result_value["pending"]
                            ]
                        )
                    )
                )

            if entities_to_update:
                siemplify.update_entities(entities_to_update)

            result = result_value
            if status != EXECUTION_STATE_INPROGRESS and isinstance(result, dict):
                result_value = False
                if result["successful"]:
                    siemplify.result.add_result_json(
                        convert_dict_to_json_result_dict(result["json_results"])
                    )
                    for csv_entity_table in result["csv_entity_table"]:
                        table_title, data_table = csv_entity_table
                        siemplify.result.add_entity_table(table_title, data_table)
                    output_message += "Active Directory - Successfully enriched following entities:\n   {}\n".format(
                        "\n   ".join(result["successful"])
                    )
                    result_value = True
                else:
                    output_message += "No entities were processed.\n"

                if result["missing_fields"]:
                    output_message += (
                        "Following attributes could not be found in any of the entities: {}. Please make "
                        "sure the attribute names are correct, and they exist on the provided entities, and "
                        "try again.".format(", ".join(result["missing_fields"]))
                    )

                if result["failed"]:
                    output_message += "\nFailed processing entities:\n   {}".format(
                        "\n   ".join(result["failed"])
                    )
        else:
            result_value = False
            output_message = "No suitable entities found.\n"
    except Exception as e:
        siemplify.LOGGER.error(
            f"General error performing action {SCRIPT_NAME}. Error: {e}"
        )
        siemplify.LOGGER.exception(e)
        status = EXECUTION_STATE_FAILED
        result_value = False
        output_message = f"General error performing action {SCRIPT_NAME}. Error: {e}"

    siemplify.LOGGER.info(f"----------------- {mode} - Finished -----------------")
    siemplify.LOGGER.info(f"\n  status: {status}\n  output_message: {output_message}")
    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    is_first_run = len(sys.argv) < 3 or sys.argv[2] == "True"
    main(is_first_run)
