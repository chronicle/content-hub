from __future__ import annotations
from soar_sdk.SiemplifyUtils import output_handler
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyAction import SiemplifyAction
from TIPCommon import extract_configuration_param

from ..core.IronScalesManager import IronScalesManager
from ..core.IronScalesConstants import PROVIDER_NAME, PING_SCRIPT_NAME


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = PING_SCRIPT_NAME
    siemplify.LOGGER.info("=" * 20 + " Main - Params Init " + "=" * 20)

    api_root = extract_configuration_param(
        siemplify,
        provider_name=PROVIDER_NAME,
        param_name="API Root",
        is_mandatory=True,
        print_value=True,
    )

    api_token = extract_configuration_param(
        siemplify,
        provider_name=PROVIDER_NAME,
        param_name="API Token",
        is_mandatory=True,
        print_value=False,
    )

    company_id = extract_configuration_param(
        siemplify,
        provider_name=PROVIDER_NAME,
        param_name="Company ID",
        is_mandatory=True,
        print_value=True,
    )

    verify_ssl = extract_configuration_param(
        siemplify,
        provider_name=PROVIDER_NAME,
        param_name="Verify SSL",
        input_type=bool,
        is_mandatory=True,
        print_value=True,
    )

    is_partner = extract_configuration_param(
        siemplify,
        provider_name=PROVIDER_NAME,
        param_name="Is Partner",
        input_type=bool,
        is_mandatory=True,
        print_value=True,
    )

    siemplify.LOGGER.info("=" * 20 + " Main - Started " + "=" * 20)

    try:
        manager = IronScalesManager(
            api_root=api_root,
            api_token=api_token,
            company_id=company_id,
            is_partner=is_partner,
            verify_ssl=verify_ssl,
            siemplify_logger=siemplify.LOGGER,
        )

        manager.test_connectivity()
        output_message = (
            "Successfully connected to the IronScales server with the provided "
            "connection parameters!"
        )
        result = True
        status = EXECUTION_STATE_COMPLETED

    except Exception as e:
        output_message = f"Failed to connect to the IronScales server! Error is {e}"
        result = False
        status = EXECUTION_STATE_FAILED
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(e)

    siemplify.LOGGER.info("=" * 20 + " Main - Finished " + "=" * 20)
    siemplify.LOGGER.info(f"Status: {status}")
    siemplify.LOGGER.info(f"Result: {result}")
    siemplify.LOGGER.info(f"Output Message: {output_message}")

    siemplify.end(output_message, result, status)


if __name__ == "__main__":
    main()
