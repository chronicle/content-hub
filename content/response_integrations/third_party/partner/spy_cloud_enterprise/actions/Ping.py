"""
SpyCloud Enterprise - Ping

Connectivity-only action for Google SecOps SOAR.

This action intentionally performs only a lightweight authenticated request to
SpyCloud's breach catalog get endpoint. It does not fetch Watchlist records,
Compass records, breach data, alerts, or checkpoints.

Publishing note: mark this action as disabled by default in the integration
metadata/UI. It is intended for manual connectivity validation, not playbook use.
"""
from __future__ import annotations

from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler

try:
    from TIPCommon.extraction import extract_configuration_param
except Exception:  # pragma: no cover - fallback for environments without TIPCommon
    extract_configuration_param = None

from ..core.Constants import (
    ENDPOINT_PING,
    INTEGRATION_DISPLAY_NAME,
    INTEGRATION_NAME,
    PING_SCRIPT_NAME,
)
from ..core.SpyCloudSDK import SpyCloudSDK

SPYCLOUD_API_KEY_PARAM = "SPYCLOUD_API_KEY"
API_ROOT_PARAM = "API Root"
VERIFY_SSL_PARAM = "Verify SSL"
SCRIPT_NAME = PING_SCRIPT_NAME


def _extract_api_key(siemplify: SiemplifyAction) -> str | None:
    """Extract the SpyCloud API key from integration configuration."""
    if extract_configuration_param:
        return extract_configuration_param(
            siemplify,
            provider_name=INTEGRATION_NAME,
            param_name=SPYCLOUD_API_KEY_PARAM,
            is_mandatory=True,
            print_value=False,
        )

    return siemplify.extract_configuration_param(
        provider_name=INTEGRATION_NAME,
        param_name=SPYCLOUD_API_KEY_PARAM,
        is_mandatory=True,
        print_value=False,
    )


def _extract_api_root(siemplify: SiemplifyAction) -> str | None:
    """Extract the SpyCloud API Root from integration configuration."""
    if extract_configuration_param:
        return extract_configuration_param(
            siemplify,
            provider_name=INTEGRATION_NAME,
            param_name=API_ROOT_PARAM,
            is_mandatory=True,
            input_type=str,
            print_value=True,
        )

    return siemplify.extract_configuration_param(
        provider_name=INTEGRATION_NAME,
        param_name=API_ROOT_PARAM,
        is_mandatory=True,
        input_type=str,
        print_value=True,
    )


def _extract_verify_ssl(siemplify: SiemplifyAction) -> bool:
    """Extract the Verify SSL flag from integration configuration."""
    if extract_configuration_param:
        return extract_configuration_param(
            siemplify,
            provider_name=INTEGRATION_NAME,
            param_name=VERIFY_SSL_PARAM,
            is_mandatory=False,
            input_type=bool,
            default_value=True,
            print_value=True,
        )

    return siemplify.extract_configuration_param(
        provider_name=INTEGRATION_NAME,
        param_name=VERIFY_SSL_PARAM,
        is_mandatory=False,
        input_type=bool,
        default_value=True,
        print_value=True,
    )


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = SCRIPT_NAME

    status = EXECUTION_STATE_FAILED
    result_value = "false"
    output_message = ""

    siemplify.LOGGER.info("================= Main - Param Init =================")

    try:
        api_key = _extract_api_key(siemplify)
        api_root = _extract_api_root(siemplify)
        verify_ssl = _extract_verify_ssl(siemplify)

        siemplify.LOGGER.info("----------------- Main - Started -----------------")
        siemplify.LOGGER.info(
            "Pinging SpyCloud breach catalog endpoint for connectivity check: "
            f"{ENDPOINT_PING} (verify_ssl={verify_ssl})"
        )

        with SpyCloudSDK(api_key, base_url=api_root, verify_ssl=verify_ssl) as sdk:
            sdk.breach_catalog.ping()

        status = EXECUTION_STATE_COMPLETED
        result_value = "true"
        output_message = (
            f"Successfully connected to the {INTEGRATION_DISPLAY_NAME} server with "
            "the provided connection parameters!"
        )

        try:
            siemplify.result.add_result_json({
                "success": True,
                "connected": True,
                "integration": INTEGRATION_DISPLAY_NAME,
                "endpoint": ENDPOINT_PING,
            })
        except Exception as json_error:
            siemplify.LOGGER.info(
                f"Connectivity succeeded, but failed to attach JSON result: {json_error}"
            )

    except Exception as error:
        siemplify.LOGGER.error(
            f"Failed to connect to the {INTEGRATION_DISPLAY_NAME} server! "
            f"Error is {error}"
        )
        siemplify.LOGGER.exception(error)
        status = EXECUTION_STATE_FAILED
        result_value = "false"
        output_message = (
            f"Failed to connect to the {INTEGRATION_DISPLAY_NAME} server! "
            f"Error is {error}"
        )

        try:
            siemplify.result.add_result_json({
                "success": False,
                "connected": False,
                "integration": INTEGRATION_DISPLAY_NAME,
                "endpoint": ENDPOINT_PING,
                "error": str(error),
            })
        except Exception:
            pass

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(f"Status: {status}")
    siemplify.LOGGER.info(f"Result Value: {result_value}")
    siemplify.LOGGER.info(f"Output Message: {output_message}")

    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()
