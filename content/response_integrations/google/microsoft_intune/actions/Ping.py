from __future__ import annotations
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler

from TIPCommon import extract_configuration_param

from microsoft_intune.core.constants import (
    AZURE_AD_ENDPOINT_DEFAULT_VALUE,
    INTEGRATION_NAME,
    MICROSOFT_GRAPH_ENDPOINT_DEFAULT_VALUE,
    PING_SCRIPT_NAME,
)
from microsoft_intune.core.MicrosoftIntuneManager import MicrosoftIntuneManager


@output_handler
def main() -> None:
    siemplify = SiemplifyAction()
    siemplify.script_name = PING_SCRIPT_NAME
    siemplify.LOGGER.info("--------------- Main - Param Init ---------------")
    azure_ad_endpoint = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Azure AD endpoint",
        is_mandatory=True,
        print_value=True,
        default_value=AZURE_AD_ENDPOINT_DEFAULT_VALUE,
    )

    microsoft_graph_endpoint = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Microsoft Graph Endpoint",
        is_mandatory=True,
        print_value=True,
        default_value=MICROSOFT_GRAPH_ENDPOINT_DEFAULT_VALUE,
    )

    client_id = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Client ID",
        is_mandatory=True,
        print_value=True,
    )

    client_secret_value = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Client Secret Value",
        is_mandatory=True,
        print_value=False,
        remove_whitespaces=False,
    )

    azure_ad_id = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Azure Active Directory ID",
        is_mandatory=True,
        print_value=True,
    )

    verify_ssl = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Verify SSL",
        is_mandatory=True,
        input_type=bool,
        print_value=True,
        default_value=True,
    )

    siemplify.LOGGER.info("---------------- Main - Started ----------------")
    result_value = True
    status = EXECUTION_STATE_COMPLETED

    try:
        siemplify.LOGGER.info("Initializing manager")
        MicrosoftIntuneManager(
            azure_ad_endpoint=azure_ad_endpoint,
            microsoft_graph_endpoint=microsoft_graph_endpoint,
            client_id=client_id,
            client_secret_value=client_secret_value,
            azure_ad_id=azure_ad_id,
            verify_ssl=verify_ssl,
            logger=siemplify.LOGGER,
        )

        output_message = (
            "Successfully connected to the Microsoft Intune service with the "
            "provided connection parameters!"
        )

    except Exception as e:
        output_message = (
            f"Failed to connect to the Microsoft Intune service! Error is: {e}"
        )
        result_value = False
        status = EXECUTION_STATE_FAILED
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(e)

    siemplify.LOGGER.info("---------------- Main - Finished ----------------")
    siemplify.LOGGER.info(f"Status: {status}")
    siemplify.LOGGER.info(f"Result Value: {result_value}")
    siemplify.LOGGER.info(f"Output Message: {output_message}")
    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()
