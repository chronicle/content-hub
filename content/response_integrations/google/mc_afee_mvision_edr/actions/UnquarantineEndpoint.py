from __future__ import annotations
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyDataModel import EntityTypes

from TIPCommon import extract_configuration_param

from ..core.McAfeeMvisionEDRManager import McAfeeMvisionEDRManager
from ..core.constants import PROVIDER_NAME

SCRIPT_NAME = "McAfeeMvisionEDR - Unquarantine Endpoint"


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = SCRIPT_NAME
    siemplify.LOGGER.info("----------------- Main - Param Init -----------------")

    api_root = extract_configuration_param(
        siemplify, provider_name=PROVIDER_NAME, param_name="API Root", input_type=str
    )
    login_api_root = extract_configuration_param(
        siemplify,
        provider_name=PROVIDER_NAME,
        param_name="Login API Root",
        input_type=str,
    )
    username = extract_configuration_param(
        siemplify, provider_name=PROVIDER_NAME, param_name="Username", input_type=str
    )
    password = extract_configuration_param(
        siemplify, provider_name=PROVIDER_NAME, param_name="Password", input_type=str
    )
    client_id = extract_configuration_param(
        siemplify, provider_name=PROVIDER_NAME, param_name="Client ID", input_type=str
    )
    client_secret = extract_configuration_param(
        siemplify,
        provider_name=PROVIDER_NAME,
        param_name="Client Secret",
        input_type=str,
    )
    verify_ssl = extract_configuration_param(
        siemplify,
        provider_name=PROVIDER_NAME,
        param_name="Verify SSL",
        default_value=False,
        input_type=bool,
    )

    siemplify.LOGGER.info("----------------- Main - Started -----------------")
    result_value = "true"
    output_message = ""
    status = EXECUTION_STATE_COMPLETED
    successful_entities = []
    failed_entities = []
    duplicate_entities = []

    try:
        mvision_edr_manager = McAfeeMvisionEDRManager(
            api_root,
            username,
            password,
            client_id,
            client_secret,
            verify_ssl=verify_ssl,
            login_api_root=login_api_root,
        )
        suitable_entities = [
            entity
            for entity in siemplify.target_entities
            if entity.entity_type == EntityTypes.ADDRESS
            or entity.entity_type == EntityTypes.HOSTNAME
        ]

        hosts = mvision_edr_manager.get_hosts()
        for entity in suitable_entities:
            siemplify.LOGGER.info(f"Started processing entity: {entity.identifier}")
            for host in hosts:
                if (
                    entity.identifier.lower() == host.hostname.lower()
                    or entity.identifier in [item.ip for item in host.net_interfaces]
                ):
                    if entity not in successful_entities:
                        mvision_edr_manager.quarantine_unquarantine_endpoint(
                            host.ma_guid, quarantine=False
                        )
                        successful_entities.append(entity)
                        siemplify.LOGGER.info(
                            f"Successfully created unquarantine endpoint task for the entity: {entity.identifier}"
                        )
                    elif entity not in duplicate_entities:
                        duplicate_entities.append(entity)

            if entity not in successful_entities:
                failed_entities.append(entity)
            siemplify.LOGGER.info(f"Finished processing entity: {entity.identifier}")

        if failed_entities:
            output_message += (
                "\n\nAction was not able to find matching McAfee Mvision EDR endpoints for the following entities:\n"
                + "{}".format(
                    "\n".join([entity.identifier for entity in failed_entities])
                )
            )

        if duplicate_entities:
            output_message += (
                "\n\nMultiple matches were found in McAfee Mvision EDR, taking first match for the following entities:\n"
                + "{}".format(
                    "\n".join([entity.identifier for entity in duplicate_entities])
                )
            )

        if successful_entities:
            output_message += (
                "\n\nSuccessfully created unquarantine endpoint task for the following entities:\n"
                + "{}".format(
                    "\n".join([entity.identifier for entity in successful_entities])
                )
            )
        else:
            output_message = "Task to unquarantine wasn't created on any entities."
            result_value = "false"

    except Exception as e:
        output_message = f"Error executing action {SCRIPT_NAME}. Reason: {e}"
        siemplify.LOGGER.error(f"Error executing action {SCRIPT_NAME}. Reason: {e}")
        siemplify.LOGGER.exception(e)
        status = EXECUTION_STATE_FAILED
        result_value = "false"

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(
        f"\n  status: {status}\n  result_value: {result_value}\n  output_message: {output_message}"
    )
    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()
