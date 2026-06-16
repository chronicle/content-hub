"""
Ping — mandatory SecOps integration health check action.

Tests:
  1. Connector parameters are present and non-empty.
  2. API key is valid (calls GET /services — lightest available endpoint).
  3. Base URL is reachable.

Used by SecOps to mark the integration as Healthy/Unhealthy in the UI.
"""
from __future__ import annotations

from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler

from ..core.constants import (
    DEFAULT_BASE_URL,
    DEFAULT_TIMEOUT,
    INTEGRATION_NAME,
    PARAM_API_KEY,
    PARAM_BASE_URL,
    PARAM_TIMEOUT,
    PARAM_VERIFY_SSL,
)
from ..core.CybleManager import CybleAPIError, CybleAuthError, CybleManager

SCRIPT_NAME = "Ping"
CONNECTED_MSG = (
    "Successfully connected to the Cyble Vision Alerts server with the provided "
    "connection parameters!"
)
NOT_CONNECTED_MSG = "Failed to connect to the Cyble Vision Alerts server! Error is {reason}"


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = SCRIPT_NAME

    api_key = siemplify.extract_configuration_param(
        provider_name=INTEGRATION_NAME, param_name=PARAM_API_KEY, is_mandatory=True
    )
    base_url = siemplify.extract_configuration_param(
        provider_name=INTEGRATION_NAME, param_name=PARAM_BASE_URL,
        default_value=DEFAULT_BASE_URL
    )
    verify_ssl = siemplify.extract_configuration_param(
        provider_name=INTEGRATION_NAME, param_name=PARAM_VERIFY_SSL,
        input_type=bool, default_value=True
    )
    timeout = siemplify.extract_configuration_param(
        provider_name=INTEGRATION_NAME, param_name=PARAM_TIMEOUT,
        input_type=int, default_value=DEFAULT_TIMEOUT
    )

    try:
        manager = CybleManager(
            api_key=api_key,
            base_url=base_url,
            verify_ssl=verify_ssl,
            timeout=timeout,
        )
        manager.ping()
        siemplify.LOGGER.info(f"[{SCRIPT_NAME}] {CONNECTED_MSG}")
        siemplify.end(CONNECTED_MSG, "true")

    except CybleAuthError as e:
        msg = NOT_CONNECTED_MSG.format(reason=f"Authentication failed — check your API key. ({e})")
        siemplify.LOGGER.error(f"[{SCRIPT_NAME}] {msg}")
        siemplify.end(msg, "false")

    except CybleAPIError as e:
        msg = NOT_CONNECTED_MSG.format(reason=str(e))
        siemplify.LOGGER.error(f"[{SCRIPT_NAME}] {msg}")
        siemplify.end(msg, "false")

    except Exception as e:  # noqa: BLE001
        msg = NOT_CONNECTED_MSG.format(reason=f"Unexpected error: {e}")
        siemplify.LOGGER.error(f"[{SCRIPT_NAME}] {msg}", exc_info=True)
        siemplify.end(msg, "false")


if __name__ == "__main__":
    main()
