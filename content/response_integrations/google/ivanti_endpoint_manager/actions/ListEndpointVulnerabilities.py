from __future__ import annotations
from soar_sdk.SiemplifyUtils import output_handler, convert_dict_to_json_result_dict
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyAction import SiemplifyAction
from TIPCommon import extract_configuration_param, extract_action_param
from ..core.IvantiEndpointManagerManager import IvantiEndpointManagerManager
from ..core.constants import (
    INTEGRATION_NAME,
    INTEGRATION_DISPLAY_NAME,
    LIST_ENDPOINT_VULNERABILITIES_SCRIPT_NAME,
    SEVERITY_CODES,
)
from soar_sdk.SiemplifyDataModel import EntityTypes
from ..core.UtilsManager import convert_comma_separated_to_list


# Fix misalignment of MAC entity type
EntityTypes.MACADDRESS = EntityTypes.MACADDRESS.upper()
SUPPORTED_ENTITY_TYPES = [
    EntityTypes.ADDRESS,
    EntityTypes.HOSTNAME,
    EntityTypes.MACADDRESS,
]


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
    username = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Username",
        is_mandatory=True,
        print_value=True,
    )
    password = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Password",
        is_mandatory=True,
    )
    verify_ssl = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Verify SSL",
        is_mandatory=True,
        input_type=bool,
        print_value=True,
    )

    # Action parameters
    severity_filter = extract_action_param(
        siemplify, param_name="Severity Filter", print_value=True
    )
    limit = extract_action_param(
        siemplify,
        param_name="Max Vulnerabilities To Return",
        input_type=int,
        print_value=True,
    )

    severities = convert_comma_separated_to_list(severity_filter)

    siemplify.LOGGER.info("----------------- Main - Started -----------------")

    result = True
    status = EXECUTION_STATE_COMPLETED
    output_message = ""
    json_results = {}
    successful_entities = []
    failed_entities = []
    not_found_entities = []
    suitable_entities = [
        entity
        for entity in siemplify.target_entities
        if entity.entity_type in SUPPORTED_ENTITY_TYPES
    ]

    try:
        if limit is not None and limit < 1:
            raise Exception('"Max Vulnerabilities To Return" must be greater than 0.')

        if not all(severity in list(SEVERITY_CODES.keys()) for severity in severities):
            raise Exception(
                f'Invalid value provided in the "Severity Filter" parameter. Possible values: '
                f"{', '.join(list(SEVERITY_CODES.keys()))}"
            )

        severities = [SEVERITY_CODES.get(severity) for severity in severities]

        manager = IvantiEndpointManagerManager(
            api_root=api_root,
            username=username,
            password=password,
            verify_ssl=verify_ssl,
            siemplify_logger=siemplify.LOGGER,
        )

        machines = manager.get_machines(suitable_entities)

        for entity in suitable_entities:
            siemplify.LOGGER.info(f"\nStarted processing entity: {entity.identifier}")

            guid = next(
                (
                    machine.guid
                    for machine in machines
                    if entity.identifier
                    in [machine.device_name, machine.ip_address, machine.mac_address]
                ),
                None,
            )

            if not guid:
                not_found_entities.append(entity)
            else:
                try:
                    vulnerabilities = manager.get_vulnerabilities(
                        guid, severities, limit
                    )

                    if vulnerabilities:
                        successful_entities.append(entity)
                        json_results[entity.identifier] = [
                            vulnerability.to_json() for vulnerability in vulnerabilities
                        ]
                    else:
                        failed_entities.append(entity)
                except Exception as e:
                    siemplify.LOGGER.error(
                        f"Failed processing entities: {entity.identifier}: Error is: {e}"
                    )
                    failed_entities.append(entity)

            siemplify.LOGGER.info(f"Finished processing entity {entity.identifier}\n")

        if successful_entities:
            siemplify.result.add_result_json(
                convert_dict_to_json_result_dict(json_results)
            )
            output_message += "Successfully found vulnerabilities on the following entities in {}: \n{}".format(
                INTEGRATION_DISPLAY_NAME,
                "\n".join([entity.identifier for entity in successful_entities]),
            )

        if failed_entities:
            output_message += "\nNo vulnerabilities were found on the following entities in {}: \n{}".format(
                INTEGRATION_DISPLAY_NAME,
                "\n".join([entity.identifier for entity in failed_entities]),
            )

        if not_found_entities:
            output_message += (
                "\nThe following entities were not found in {}: \n{}".format(
                    INTEGRATION_DISPLAY_NAME,
                    "\n".join([entity.identifier for entity in not_found_entities]),
                )
            )

        if len(not_found_entities) == len(suitable_entities):
            result = False
            output_message = f"None of the provided entities were found in {INTEGRATION_DISPLAY_NAME}."
        elif not successful_entities:
            result = False
            output_message = f"No vulnerabilities were found on the provided entities in {INTEGRATION_DISPLAY_NAME}"

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
