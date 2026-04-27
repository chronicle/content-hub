from __future__ import annotations
from soar_sdk.SiemplifyUtils import output_handler, convert_dict_to_json_result_dict
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyDataModel import EntityTypes
from soar_sdk.ScriptResult import (
    EXECUTION_STATE_INPROGRESS,
    EXECUTION_STATE_FAILED,
    EXECUTION_STATE_COMPLETED,
)
from ..core.AutoFocusManager import AutoFocusManager, COOKIE, NOT_COMPLETED
from TIPCommon import (
    extract_configuration_param,
    dict_to_flat,
    add_prefix_to_dict_keys,
    construct_csv,
)
import base64
import sys
import json

INTEGRATION_NAME = "AutoFocus"
SCRIPT_NAME = "HuntFile"
SUPPORTED_ENTITIES = [EntityTypes.FILENAME, EntityTypes.FILEHASH]


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = f"{INTEGRATION_NAME} - {SCRIPT_NAME}"
    siemplify.LOGGER.info("================= Main - Param Init =================")

    # INIT INTEGRATION CONFIGURATION:
    api_key = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Api Key",
        is_mandatory=True,
        input_type=str,
    )

    siemplify.LOGGER.info("----------------- Main - Started -----------------")

    successful_entities = []
    hunts = {}
    failed_entities = []
    status = EXECUTION_STATE_COMPLETED
    output_message = ""

    try:
        autofocus_manager = AutoFocusManager(api_key)

        for entity in siemplify.target_entities:
            try:
                if entity.entity_type not in SUPPORTED_ENTITIES:
                    siemplify.LOGGER.info(
                        f"Entity {entity.identifier} is of unsupported type. Skipping."
                    )
                    continue

                siemplify.LOGGER.info(f"Started processing entity: {entity.identifier}")

                if entity.entity_type == EntityTypes.FILEHASH:
                    af_cookie, af_status = hunt_hash(
                        autofocus_manager, entity.identifier
                    )

                else:
                    # Entity is a FILENAME
                    af_cookie, af_status = autofocus_manager.hunt_file_filename(
                        entity.identifier
                    )

                siemplify.LOGGER.info(
                    f"Successfully started hunt for {entity.identifier}. AF Cookie: {af_cookie}."
                )

                hunts[entity.identifier] = {COOKIE: af_cookie, "completed": False}

                successful_entities.append(entity.identifier)

            except Exception as e:
                failed_entities.append(entity.identifier)
                siemplify.LOGGER.error(
                    f"An error occurred on entity {entity.identifier}"
                )
                siemplify.LOGGER.exception(e)

        if successful_entities:
            output_message += (
                "Successfully initiated hunt for the following entities:\n   {}".format(
                    "\n   ".join([entity for entity in successful_entities])
                )
            )
            status = EXECUTION_STATE_INPROGRESS

        else:
            output_message = "No entities were enriched."

        if failed_entities:
            output_message += "\n\nError occurred while initiating hunt for the following entities:\n   {}".format(
                "\n   ".join([entity for entity in failed_entities])
            )

        if successful_entities:
            output_message += "\n\nWaiting for hunts to complete."

        result_value = json.dumps(
            {
                "hunts": hunts,
                "successful_entities": successful_entities,
                "failed_entities": failed_entities,
            }
        )

    except Exception as e:
        siemplify.LOGGER.error(f"Action didn't complete due to error: {e}")
        siemplify.LOGGER.exception(e)
        status = EXECUTION_STATE_FAILED
        result_value = "false"
        output_message = f"Action didn't complete due to error: {e}"

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(f"Status: {status}:")
    siemplify.LOGGER.info(f"Result Value: {result_value}")
    siemplify.LOGGER.info(f"Output Message: {output_message}")
    siemplify.end(output_message, result_value, status)


def async_action():
    siemplify = SiemplifyAction()
    siemplify.script_name = f"{INTEGRATION_NAME} - {SCRIPT_NAME}"

    siemplify.LOGGER.info("================= Async - Param Init =================")

    api_key = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Api Key",
        is_mandatory=True,
        input_type=str,
    )

    results_limit = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Results Limit",
        is_mandatory=False,
        input_type=int,
        default_value=None,
    )

    siemplify.LOGGER.info("----------------- Async - Started -----------------")

    error_entities = []
    successful_entities = []
    no_results_entities = []
    json_results = {}
    result_value = "true"
    status = EXECUTION_STATE_COMPLETED

    action_details = json.loads(siemplify.parameters["additional_data"])
    hunts = action_details["hunts"]
    init_failed_entities = action_details["failed_entities"]
    init_success_entities = action_details["successful_entities"]
    current_status_report = ""
    all_completed = True

    try:
        autofocus_manager = AutoFocusManager(api_key)

        # Check if tasks have all completed
        for entity_identifier, hunt in list(hunts.items()):
            try:
                if hunt.get("completed"):
                    siemplify.LOGGER.info(
                        f"Hunt for {entity_identifier} already completed."
                    )
                    current_status_report += f"   {entity_identifier}: {100}%\n"

                else:
                    siemplify.LOGGER.info(
                        f"Checking status of the hunt for {entity_identifier}"
                    )
                    entity = convert_identifier_to_entity(siemplify, entity_identifier)

                    if entity.entity_type == EntityTypes.FILEHASH:
                        results, af_status = hunt_hash(
                            autofocus_manager, entity.identifier, hunt[COOKIE]
                        )

                    else:
                        # Entity is a FILENAME
                        results, af_status = autofocus_manager.hunt_file_filename(
                            entity.identifier, hunt[COOKIE]
                        )

                    if af_status == NOT_COMPLETED:
                        siemplify.LOGGER.info(
                            f"Hunt haven't completed yet. Completed percentage: {results}"
                        )

                        current_status_report += f"   {entity_identifier}: {results}%\n"
                        all_completed = False

                    else:
                        # Hunt for entity has completed - percentage is 100
                        siemplify.LOGGER.info("Hunt completed.")
                        hunt["results"] = results
                        hunt["completed"] = True
                        current_status_report += f"   {entity_identifier}: {100}%\n"

            except Exception as e:
                siemplify.LOGGER.info(
                    f"Failed to check status of hunt for {entity_identifier}"
                )
                siemplify.LOGGER.exception(e)
                output_message = f"An error occurred while running action. Failed to check status of hunt for {entity_identifier}"
                status = EXECUTION_STATE_FAILED
                siemplify.end(output_message, "false", status)

        if not all_completed:
            siemplify.LOGGER.info(
                f"Hunts have not completed yet. Waiting. Current status:\n\n{current_status_report}"
            )
            output_message = f"Hunts have not completed yet. Waiting. Current status:\n\n{current_status_report}"
            result_value = json.dumps(
                {
                    "hunts": hunts,
                    "successful_entities": init_success_entities,
                    "failed_entities": init_failed_entities,
                }
            )
            status = EXECUTION_STATE_INPROGRESS
            siemplify.end(output_message, result_value, status)

        siemplify.LOGGER.info("All hunts have completed.")

        for entity_identifier, hunt in list(hunts.items()):
            try:
                hunt_result = hunt.get("results", [])
                json_results[entity_identifier] = hunt_result

                if hunt_result:
                    siemplify.LOGGER.info(
                        f"Found {len(hunt_result)} hits for {entity_identifier}"
                    )

                    entity = convert_identifier_to_entity(siemplify, entity_identifier)

                    # Get hits and enrich the entity
                    count = 1

                    # Flatten the first hits (up to limit) and append a count
                    # prefix to identify info with its hit number
                    trimmed_hunt_results = (
                        hunt_result[:results_limit] if results_limit else hunt_result
                    )

                    siemplify.LOGGER.info(f"Enriching entity {entity_identifier}")

                    for hit in trimmed_hunt_results:
                        flat_result = dict_to_flat(hit)
                        flat_result = add_prefix_to_dict_keys(flat_result, str(count))
                        flat_result = add_prefix_to_dict_keys(flat_result, "AutoFocus")
                        entity.additional_properties.update(flat_result)
                        count += 1

                    # Attach all hits as csv
                    siemplify.LOGGER.info(
                        f"Attaching table to entity {entity_identifier}"
                    )
                    csv_output = construct_csv(trimmed_hunt_results)
                    siemplify.result.add_entity_table(entity.identifier, csv_output)

                    # Attach report
                    siemplify.LOGGER.info(
                        f"Attaching json report for {entity_identifier}"
                    )
                    base64_report = base64.b64encode(
                        json.dumps(hunt_result, indent=4, sort_keys=True).encode("utf-8")
                    )

                    siemplify.result.add_entity_attachment(
                        entity.identifier, "AutoFocus Report", base64_report
                    )

                    entity.is_enriched = True

                    siemplify.LOGGER.info(f"Marking {entity_identifier} as suspicious.")
                    entity.is_suspicious = True

                    siemplify.LOGGER.info(f"Adding insight for {entity_identifier}")
                    insight_msg = f"{len(hunt_result)} hits were found in AutoFocus"
                    siemplify.add_entity_insight(
                        entity, insight_msg, triggered_by="AutoFocus"
                    )

                    successful_entities.append(entity)

                else:
                    siemplify.LOGGER.info(f"No hits were found for {entity_identifier}")
                    no_results_entities.append(entity_identifier)

            except Exception as e:
                error_entities.append(entity_identifier)
                siemplify.LOGGER.error(
                    f"An error occurred on entity {entity_identifier}"
                )
                siemplify.LOGGER.exception(e)

        if successful_entities:
            output_message = (
                "The following entities were enriched by AutoFocus:\n   {}".format(
                    "\n   ".join([entity.identifier for entity in successful_entities])
                )
            )
            siemplify.update_entities(successful_entities)

        else:
            output_message = "No entities were enriched."

        if no_results_entities:
            output_message += (
                "\n\nNo hits were found for the following entities:\n   {}".format(
                    "\n   ".join([entity for entity in no_results_entities])
                )
            )

        if init_failed_entities:
            output_message += "\n\nError occurred while initiating hunt for the following entities:\n   {}".format(
                "\n   ".join([entity for entity in init_failed_entities])
            )

        if error_entities:
            output_message += "\n\nError occurred while running hunt for the following entities:\n   {}".format(
                "\n   ".join([entity for entity in error_entities])
            )

        siemplify.result.add_result_json(convert_dict_to_json_result_dict(json_results))

    except Exception as e:
        siemplify.LOGGER.error(f"Action didn't complete due to error: {e}")
        siemplify.LOGGER.exception(e)
        status = EXECUTION_STATE_FAILED
        result_value = "false"
        output_message = f"Action didn't complete due to error: {e}"

    siemplify.LOGGER.info("----------------- Async - Finished -----------------")
    siemplify.LOGGER.info(f"Status: {status}:")
    siemplify.LOGGER.info(f"Result Value: {result_value}")
    siemplify.LOGGER.info(f"Output Message: {output_message}")
    siemplify.end(output_message, result_value, status)


def convert_identifier_to_entity(siemplify, entity_identifier):
    for entity in siemplify.target_entities:
        if entity_identifier == entity.identifier:
            return entity

    raise Exception(f"Entity {entity_identifier} was not found in current scope")


def hunt_hash(autofocus_manager, file_hash, af_cookie=None):
    if len(file_hash) == 40:
        # Try to hunt by sha1
        return autofocus_manager.hunt_file_sha1(file_hash, af_cookie)

    elif len(file_hash) == 32:
        # Try to hunt by md5
        return autofocus_manager.hunt_file_md5(file_hash, af_cookie)

    elif len(file_hash) == 64:
        # Try to hunt by sha256
        return autofocus_manager.hunt_file_sha256(file_hash, af_cookie)

    raise Exception(f"Hash {file_hash} is of unknown type (not SHA1, MD5, SHA256).")


if __name__ == "__main__":
    if len(sys.argv) < 3 or sys.argv[2] == "True":
        main()
    else:
        async_action()
