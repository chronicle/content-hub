from __future__ import annotations
from soar_sdk.SiemplifyUtils import output_handler
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from TIPCommon.extraction import extract_configuration_param, extract_action_param
from sentinel_one_v2.core.utils import string_to_multi_value
from sentinel_one_v2.core.constants import (
    INTEGRATION_NAME,
    PRODUCT_NAME,
    MITIGATE_THREAT_SCRIPT_NAME,
    MITIGATION_MAPPING,
    QUARANTINE,
)
from sentinel_one_v2.core.SentinelOneV2Factory import SentinelOneV2ManagerFactory


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = MITIGATE_THREAT_SCRIPT_NAME

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

    mitigation_action = extract_action_param(
        siemplify,
        param_name="Mitigation action",
        is_mandatory=True,
        default_value=MITIGATION_MAPPING[QUARANTINE],
        print_value=True,
    ).lower()
    threat_ids = string_to_multi_value(
        extract_action_param(
            siemplify, param_name="Threat IDs", is_mandatory=True, print_value=True
        )
    )

    result_value = True
    status = EXECUTION_STATE_COMPLETED
    output_message = ""
    success_threats, failed_threats, mitigated_threats, json_results = [], [], [], []

    try:
        manager = SentinelOneV2ManagerFactory().get_manager(
            api_root=api_root,
            api_token=api_token,
            verify_ssl=verify_ssl,
            force_check_connectivity=True,
        )
        for threat_id in threat_ids:
            try:
                threat = manager.get_threat_or_raise(threat_id)
                for mitigation_status in threat.mitigation_statuses:
                    if mitigation_status.has_action(mitigation_action):
                        mitigated_threats.append(threat_id)
                        break
                else:
                    affected_count = manager.mitigate_threat(
                        mitigation_action, [threat_id]
                    )
                    if not affected_count:
                        raise
                    success_threats.append(threat_id)
                json_results.append(threat.to_mitigate_json(mitigation_action))
            except Exception as e:
                siemplify.LOGGER.error(f"Failed to mitigate Threat ID {threat_id}")
                siemplify.LOGGER.exception(e)
                failed_threats.append(threat_id)

        if success_threats:
            output_message += (
                "Successfully mitigated the following threats in"
                f"{PRODUCT_NAME}:\n{', '.join(success_threats)}\n"
            )

        if failed_threats:
            output_message += (
                "Action wasn't able to mitigate the following threats in"
                f"{PRODUCT_NAME}:\n{', '.join(failed_threats)}\n"
            )

        if mitigated_threats:
            output_message += (
                f"The {mitigation_action} action was already applied to the following"
                f"threats in {PRODUCT_NAME}:\n{', '.join(mitigated_threats)}."
                "Note: those action can still be pending.\n"
            )

        elif not success_threats:
            result_value = False
            output_message = "No threats were mitigated."

        if json_results:
            siemplify.result.add_result_json(json_results)

    except Exception as e:
        output_message = (
            f"Error executing action '{MITIGATE_THREAT_SCRIPT_NAME}'. Reason: {e}"
        )
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(e)
        status = EXECUTION_STATE_FAILED
        result_value = False

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(
        f"\n  status: {status}\n  result_value: {result_value}\n"
        f"output_message: {output_message}"
    )
    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()
