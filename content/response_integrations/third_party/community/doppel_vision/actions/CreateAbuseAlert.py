from __future__ import annotations

from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler

from ..core.DoppelManager import DoppelManager


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = "Create Abuse Alert Action"

    # Extract parameters
    api_key = siemplify.extract_configuration_param(
        provider_name="Doppel",
        param_name="API_Key",
    )
    entity = siemplify.extract_action_param(param_name="Entity", is_mandatory=True)

    # Instantiate the manager
    manager = DoppelManager(api_key)

    # Initialize action result values
    status = EXECUTION_STATE_COMPLETED
    output_message = "Abuse alert created successfully."
    result_value = True

    try:
        # Perform the create_abuse_alert action
        abuse_alert = manager.create_abuse_alert(entity=entity)
        if abuse_alert:
            siemplify.result.add_result_json(
                abuse_alert,
            )  # Store abuse alert in the action result JSON
        else:
            raise Exception("Failed to create abuse alert or empty response.")
    except Exception as e:
        output_message = f"Failed to create abuse alert: {e!s}"
        status = EXECUTION_STATE_FAILED
        result_value = False

    # Log results and complete the action
    siemplify.LOGGER.info(
        f"status: {status}\nresult_value: {result_value}\noutput_message: {output_message}",
    )
    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()
