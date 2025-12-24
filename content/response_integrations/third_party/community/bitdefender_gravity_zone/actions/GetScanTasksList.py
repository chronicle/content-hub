from __future__ import annotations

from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler

from ..core.BitdefenderGravityZoneManager import BitdefenderGravityZoneManager


@output_handler
def main():
    siemplify = SiemplifyAction()

    api_key = siemplify.extract_configuration_param("Integration", "API Key")
    access_url = siemplify.extract_configuration_param("Integration", "Access URL")
    verify_ssl = siemplify.extract_configuration_param(
        "Integration",
        "Verify SSL",
        input_type=bool,
    )
    task_name = siemplify.extract_action_param("Use JSON Filter", print_value=True)
    task_status = siemplify.extract_action_param("Filter", print_value=True)

    try:
        siemplify.LOGGER.info("Connecting to Bitdefender GravityZone Control Center.")
        mtm = BitdefenderGravityZoneManager(api_key, verify_ssl)
        siemplify.LOGGER.info("Connected successfully.")

        tasks_data = mtm.task_scan_list(access_url, task_name, task_status)

        status = EXECUTION_STATE_COMPLETED
        output_message = "success"
        result_value = "success"
        siemplify.result.add_result_json(tasks_data)
        siemplify.LOGGER.info(
            f"\n  status: {status}\n  result_value: {result_value}\n  output_message: {output_message}",
        )
        siemplify.end(output_message, result_value, status)
    except Exception as e:
        siemplify.LOGGER.error(f"An error occurred: {e}")
        siemplify.LOGGER.exception(e)


if __name__ == "__main__":
    main()
