from __future__ import annotations
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyDataModel import EntityTypes
from soar_sdk.SiemplifyUtils import output_handler
from TIPCommon import extract_configuration_param

from ..core.constants import INTEGRATION_NAME, SCANHOST_SCRIPT_NAME
from ..core.TrendmicroDeepSecurityManager import TrendmicroManager


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = SCANHOST_SCRIPT_NAME
    siemplify.LOGGER.info("------------ Main - Param Init -----------------")
    api_root = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Api Root",
        is_mandatory=True,
        print_value=True,
    )
    api_key = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Api Secret Key",
        is_mandatory=True,
        print_value=False,
        remove_whitespaces=False,
    )
    api_version = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Api Version",
        is_mandatory=True,
        remove_whitespaces=False,
    )
    verify_ssl = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Verify SSL",
        input_type=bool,
        print_value=True,
    )

    siemplify.LOGGER.info("----------------- Main - Started -----------------")
    status = EXECUTION_STATE_COMPLETED
    result_value = True
    try:
        trendmicro_manager = TrendmicroManager(
            api_root=api_root,
            api_secret_key=api_key,
            api_version=api_version,
            verify_ssl=verify_ssl,
        )
        entities = []

        # TODO: Need to double check the development

        for entity in siemplify.target_entities:
            if entity.entity_type == EntityTypes.HOSTNAME:
                try:
                    trendmicro_manager.scan_computers_for_malware(entity.identifier)
                    entities.append(entity.identifier)
                except Exception as e:
                    # An error occurred - skip entity and continue
                    siemplify.LOGGER.error(
                        f"An error occurred on entity: {entity.identifier}.\n{str(e)}."
                    )
                    siemplify.LOGGER.exception(e)

        if entities:
            result_value = True
            output_message = (
                "Successfully request a malware scan on "
                f"{', '.join([entity for entity in entities])}"
            )
        else:
            result_value = False
            output_message = "Failed to request a malware scan."
    except Exception as error:
        siemplify.LOGGER.error(
            f"General error performing action {SCANHOST_SCRIPT_NAME}"
        )
        siemplify.LOGGER.exception(error)
        result_value = False
        status = EXECUTION_STATE_FAILED

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(f"Status: {status}")
    siemplify.LOGGER.info(f"Result: {result_value}")
    siemplify.LOGGER.info(f"Output Message: {output_message}")

    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()
