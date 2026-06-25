"""
GetServicesList — returns the current list of active Cyble services.

Useful for:
  - Validating connector configuration.
  - Populating service filter inputs in playbooks dynamically.
  - Troubleshooting ("which services am I authorized for?").
"""
from __future__ import annotations

import json

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

SCRIPT_NAME = "GetServicesList"


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = SCRIPT_NAME

    api_key = siemplify.extract_configuration_param(
        provider_name=INTEGRATION_NAME, param_name=PARAM_API_KEY, is_mandatory=True
    )
    base_url = siemplify.extract_configuration_param(
        provider_name=INTEGRATION_NAME, param_name=PARAM_BASE_URL, default_value=DEFAULT_BASE_URL
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
        manager = CybleManager(api_key=api_key, base_url=base_url, verify_ssl=verify_ssl, timeout=timeout)
        services = manager.get_services()
    except CybleAuthError as e:
        siemplify.end(f"Authentication failed: {e}", "false")
        return
    except CybleAPIError as e:
        siemplify.end(f"API error: {e}", "false")
        return

    output = json.dumps({
        "total": len(services),
        "services": [
            {"name": s["name"], "displayName": s["displayName"], "allowAlerts": s["allowAlerts"]}
            for s in services
        ],
    }, indent=2)

    siemplify.result.add_result_json(output)
    siemplify.end(f"Found {len(services)} active services.", "true")


if __name__ == "__main__":
    main()
