from __future__ import annotations
import json

from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED

from ..core.constants import (
    DEFAULT_FLARE_API_URL,
    INTEGRATION_NAME,
    SYNC_REMEDIATION_SCRIPT_NAME,
    VENDOR_NAME,
)
from ..core.FlareManager import FlareManager
from ..core.Remediator import SoarRemediator
from ..core.utils import format_user_facing_error, parse_tenant_id


@output_handler
def main():
    """
    One-shot remediation sync: closed SOAR Flare cases → Flare remediate.
    Uses SOAR SDK only — no Google service account.
    Lookup window comes from last_successful_check_timestamp in remediation state.
    """
    siemplify = SiemplifyAction()
    siemplify.script_name = SYNC_REMEDIATION_SCRIPT_NAME
    siemplify.LOGGER.info("=============== Main - Param Init ===============")

    flare_api_key = siemplify.extract_configuration_param(
        INTEGRATION_NAME, "Flare API Key"
    )
    flare_tenant_id = siemplify.extract_configuration_param(
        INTEGRATION_NAME, "Flare Tenant ID"
    )

    state_json = siemplify.extract_action_param(
        param_name="Remediation State JSON",
        is_mandatory=False,
        print_value=False,
        default_value="{}",
    )

    siemplify.LOGGER.info("=============== Main - Started ===============")
    status = EXECUTION_STATE_COMPLETED
    result_value = True

    try:
        if not flare_api_key:
            raise Exception(
                "Flare API Key is required. Enter your API key and try again."
            )

        tenant_id = parse_tenant_id(flare_tenant_id)

        try:
            state = json.loads(state_json or "{}")
            if not isinstance(state, dict):
                state = {}
        except json.JSONDecodeError:
            state = {}

        flare = FlareManager(
            api_key=flare_api_key,
            tenant_id=tenant_id,
            api_url=DEFAULT_FLARE_API_URL,
            logger_instance=siemplify.LOGGER,
        )
        remediator = SoarRemediator(
            flare_manager=flare,
            siemplify=siemplify,
            rule_generator=VENDOR_NAME,
            state=state,
            logger_instance=siemplify.LOGGER,
        )
        result = remediator.run_once()
        output_message = result.get("message") or "Remediation sync finished."
        if result.get("errors"):
            status = EXECUTION_STATE_FAILED
            result_value = False
            friendly_errors = [
                format_user_facing_error(Exception(err)) for err in result["errors"]
            ]
            result["errors"] = friendly_errors
            output_message = (
                f"{output_message} Errors: {'; '.join(friendly_errors)}"
            )

        siemplify.result.add_result_json(result)
        siemplify.result.add_json(
            "RemediationState",
            json.dumps(result.get("state") or state),
        )

    except Exception as error:
        result_value = False
        status = EXECUTION_STATE_FAILED
        friendly = format_user_facing_error(error)
        output_message = f"Remediation sync failed: {friendly}"
        siemplify.LOGGER.error(output_message)

    siemplify.LOGGER.info("=============== Main - Finished ===============")
    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()
