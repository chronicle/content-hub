from __future__ import annotations

from soar_sdk.SiemplifyUtils import output_handler, convert_dict_to_json_result_dict
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyAction import SiemplifyAction
from TIPCommon import extract_configuration_param, extract_action_param, construct_csv
from tenable_io.core.TenableIOManager import TenableIOManager
from tenable_io.core.constants import (
    INTEGRATION_NAME,
    INTEGRATION_DISPLAY_NAME,
    LIST_ENDPOINT_VULNERABILITIES_SCRIPT_NAME,
    DEFAULT_VULNERABILITIES_LIMIT,
    MAX_VULNERABILITIES_LIMIT,
    SEVERITIES,
)
from soar_sdk.SiemplifyDataModel import EntityTypes
from tenable_io.core.TenableIOExceptions import TenableIOException, AssetExportException
from tenable_io.core.UtilsManager import build_identifier_to_asset_map


SUPPORTED_ENTITY_TYPES = [EntityTypes.ADDRESS, EntityTypes.HOSTNAME]


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = LIST_ENDPOINT_VULNERABILITIES_SCRIPT_NAME
    siemplify.LOGGER.info("----------------- Main - Param Init -----------------")

    api_root = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="API Root",
        is_mandatory=True,
        print_value=True,
    )
    secret_key = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Secret Key",
        is_mandatory=True,
    )
    access_key = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Access Key",
        is_mandatory=True,
    )
    verify_ssl = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Verify SSL",
        input_type=bool,
        is_mandatory=True,
        print_value=True,
    )

    # Action parameters
    lowest_severity = extract_action_param(
        siemplify, param_name="Lowest Severity To Fetch", print_value=True
    )
    limit = extract_action_param(
        siemplify,
        param_name="Max Vulnerabilities To Return",
        input_type=int,
        default_value=DEFAULT_VULNERABILITIES_LIMIT,
        print_value=True,
    )

    siemplify.LOGGER.info("----------------- Main - Started -----------------")

    result = True
    status = EXECUTION_STATE_COMPLETED
    output_message = ""
    successful_entities = []
    failed_entities = []
    json_results = {}
    not_found_entities = []

    suitable_entities = [
        entity
        for entity in siemplify.target_entities
        if entity.entity_type in SUPPORTED_ENTITY_TYPES
    ]

    if not suitable_entities:
        output_message = "No suitable entities were provided."
        siemplify.LOGGER.info("----------------- Main - Finished -----------------")
        siemplify.LOGGER.info(f"Status: {status}")
        siemplify.LOGGER.info(f"Result: {False}")
        siemplify.LOGGER.info(f"Output Message: {output_message}")
        siemplify.end(output_message, False, status)

    try:
        if limit < 1:
            raise Exception('"Max Vulnerabilities To Return" must be greater than 0.')
        elif limit > MAX_VULNERABILITIES_LIMIT:
            siemplify.LOGGER.info(
                f'"Max Vulnerabilities To Return" exceeded the maximum limit of '
                f"{MAX_VULNERABILITIES_LIMIT}. The default value {DEFAULT_VULNERABILITIES_LIMIT} "
                f"will be used"
            )
            limit = DEFAULT_VULNERABILITIES_LIMIT

        manager = TenableIOManager(
            api_root=api_root,
            secret_key=secret_key,
            access_key=access_key,
            verify_ssl=verify_ssl,
            siemplify_logger=siemplify.LOGGER,
        )

        siemplify.LOGGER.info(
            "Found suitable entities. Starting asset export from Tenable.IO."
        )
        all_assets = manager.get_all_assets()
        asset_map = build_identifier_to_asset_map(all_assets)
        siemplify.LOGGER.info(
            f"Successfully built a map for {len(all_assets)} assets."
        )

        for entity in suitable_entities:
            siemplify.LOGGER.info(
                f"\nStarted processing entity: {entity.identifier}"
            )
            normalized_entity = entity.identifier.lower()
            matching_asset = asset_map.get(normalized_entity)

            if not matching_asset and entity.entity_type == EntityTypes.HOSTNAME:
                short_name = normalized_entity.split(".")[0]
                matching_asset = asset_map.get(short_name)

            if not matching_asset:
                siemplify.LOGGER.info(
                    f"Entity {entity.identifier} not found in Tenable.IO assets."
                )
                not_found_entities.append(entity)
                continue

            siemplify.LOGGER.info(
                f"Found matching asset with ID: {matching_asset.id}"
            )

            try:
                vulnerabilities = manager.get_endpoint_vulnerabilities(
                    asset_id=matching_asset.id,
                    severities=(
                        SEVERITIES[SEVERITIES.index(lowest_severity.lower()):]
                        if lowest_severity
                        else []
                    ),
                    limit=limit,
                )

                if vulnerabilities:
                    successful_entities.append(entity)
                    json_results[entity.identifier] = [
                        vuln.to_json() for vuln in vulnerabilities
                    ]
                    siemplify.result.add_entity_table(
                        entity.identifier,
                        construct_csv(
                            [vuln.to_table() for vuln in vulnerabilities]
                        ),
                    )
                    siemplify.LOGGER.info(
                        f"Successfully found {len(vulnerabilities)} vulnerabilities"
                        f" for {entity.identifier}."
                    )
                else:
                    failed_entities.append(entity)
                    siemplify.LOGGER.info(
                        f"No vulnerabilities found for {entity.identifier}."
                    )

            except TenableIOException as e:
                siemplify.LOGGER.error(
                    "Failed to get vulnerabilities for entity: "
                    f"{entity.identifier}. Error: {e}"
                )
                failed_entities.append(entity)

            siemplify.LOGGER.info(
                f"Finished processing entity {entity.identifier}\n"
            )

        if successful_entities:
            siemplify.result.add_result_json(
                convert_dict_to_json_result_dict(json_results)
            )
            output_message += "Successfully listed vulnerabilities related to the following endpoints in {}: \n{}".format(
                INTEGRATION_DISPLAY_NAME,
                "\n".join([entity.identifier for entity in successful_entities]),
            )

        if not_found_entities:
            output_message += "\nAction wasn't able to find the following endpoints in {}: \n{}".format(
                INTEGRATION_DISPLAY_NAME,
                "\n".join([entity.identifier for entity in not_found_entities]),
            )

        if failed_entities:
            output_message += "\nNo vulnerabilities were found for the following endpoints: \n{}".format(
                "\n".join([entity.identifier for entity in failed_entities])
            )

        if not successful_entities and not failed_entities:
            result = False
            output_message = "No endpoints were found in Tenable.IO for the provided entities."

    except AssetExportException as e:
        result = False
        status = EXECUTION_STATE_FAILED
        output_message = f"Error during asset export process: {e}"
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(e)

    except Exception as e:
        siemplify.LOGGER.error(
            f"General error performing action {LIST_ENDPOINT_VULNERABILITIES_SCRIPT_NAME}"
        )
        siemplify.LOGGER.exception(e)
        result = False
        status = EXECUTION_STATE_FAILED
        output_message = f'Error executing action "{LIST_ENDPOINT_VULNERABILITIES_SCRIPT_NAME}". Reason: {e}'

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(f"Status: {status}")
    siemplify.LOGGER.info(f"Result: {result}")
    siemplify.LOGGER.info(f"Output Message: {output_message}")

    siemplify.end(output_message, result, status)


if __name__ == "__main__":
    main()
