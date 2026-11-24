from __future__ import annotations
from soar_sdk.SiemplifyUtils import output_handler
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from TIPCommon.extraction import extract_configuration_param, extract_action_param
from sentinel_one_v2.core.constants import INTEGRATION_NAME, RESOLVE_THREAT_SCRIPT_NAME, PRODUCT_NAME
from sentinel_one_v2.core.utils import string_to_multi_value
from sentinel_one_v2.core.SentinelOneV2Factory import SentinelOneV2ManagerFactory


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = RESOLVE_THREAT_SCRIPT_NAME

    siemplify.LOGGER.info("----------------- Main - Param Init -----------------")

    api_root = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Api Root",
        is_mandatory=True,
    )
    api_token = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="API Token",
        is_mandatory=True,
    )
    verify_ssl = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Verify SSL",
        default_value=False,
        input_type=bool,
    )

    siemplify.LOGGER.info("----------------- Main - Started -----------------")

    threat_ids = string_to_multi_value(
        extract_action_param(
            siemplify, param_name="Threat IDs", is_mandatory=True, print_value=True
        )
    )
    annotation = extract_action_param(
        siemplify, param_name="Annotation", print_value=True
    )

    status = EXECUTION_STATE_COMPLETED
    resolved_threats, failed_threats, json_results = [], [], []
    result_value = True

    try:
        manager = SentinelOneV2ManagerFactory().get_manager(
            api_root=api_root,
            api_token=api_token,
            verify_ssl=verify_ssl,
            force_check_connectivity=True,
        )
        for threat_id in threat_ids:
            try:
                manager.resolve_threat([threat_id], annotation)
                threat = manager.get_threat_or_raise(threat_id)
                (resolved_threats if threat.resolved else failed_threats).append(
                    threat_id
                )
                json_results.append(threat.to_resolve_json())
            except Exception as e:
                siemplify.LOGGER.error(f"Failed to resolve Threat ID {threat_id}")
                siemplify.LOGGER.exception(e)
                failed_threats.append(threat_id)

        if resolved_threats:
            output_message = (
                f"Successfully resolved the following threats in {PRODUCT_NAME}:\n"
                f"{', '.join(resolved_threats)}\n"
            )
            if failed_threats:
                output_message += (
                    "Action wasn't able to resolve the following threats in"
                    f"{PRODUCT_NAME}:\n{', '.join(failed_threats)}\n"
                )
        else:
            result_value = False
            output_message = "No threats were resolved"

        if json_results:
            siemplify.result.add_result_json(json_results)

    except Exception as e:
        output_message = (
            f"Error executing action '{RESOLVE_THREAT_SCRIPT_NAME}'. Reason: {e}"
        )
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(e)
        status = EXECUTION_STATE_FAILED
        result_value = False

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(
        f"\n  status: {status}\n  result_value: {result_value}\n  output_message: {output_message}"
    )
    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()
