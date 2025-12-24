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
    quarantine_item_ids = siemplify.extract_action_param(
        "Quarantine Item IDs",
        print_value=True,
    )
    service = siemplify.extract_action_param("Service", print_value=True)
    add_exclusion = siemplify.extract_action_param(
        "Add Exclusion in Policy",
        print_value=True,
        default_value=False,
        input_type=bool,
    )
    restore_location = siemplify.extract_action_param(
        "Location to Restore",
        print_value=True,
    )

    try:
        siemplify.LOGGER.info("Connecting to Bitdefender GravityZone Control Center.")
        mtm = BitdefenderGravityZoneManager(api_key, verify_ssl)
        siemplify.LOGGER.info("Connected successfully.")

        action_result = mtm.quarantine_item_restore(
            access_url,
            quarantine_item_ids,
            service,
            add_exclusion,
            restore_location,
        )

        status = EXECUTION_STATE_COMPLETED
        output_message = "success"
        result_value = "success"
        if not action_result:
            result_value = "failed"
            output_message = "failed"
        siemplify.LOGGER.info(
            f"\n  status: {status}\n  result_value: {result_value}\n  output_message: {output_message}",
        )
        siemplify.end(output_message, result_value, status)
    except Exception as e:
        siemplify.LOGGER.error(f"An error occurred: {e}")
        siemplify.LOGGER.exception(e)


if __name__ == "__main__":
    main()
