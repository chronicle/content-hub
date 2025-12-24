from __future__ import annotations

from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler

from ..core.DoppelManager import DoppelManager


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = "Update Alert Action"

    # Extract parameters
    api_key = siemplify.extract_configuration_param(
        provider_name="Doppel",
        param_name="API_Key",
    )
    entity = siemplify.extract_action_param(param_name="Entity", default_value=None)
    alert_id = siemplify.extract_action_param(param_name="Alert_ID", default_value=None)
    queue_state = siemplify.extract_action_param(
        param_name="Queue_State",
        is_mandatory=True,
    )
    entity_state = siemplify.extract_action_param(
        param_name="Entity_State",
        is_mandatory=True,
    )

    # Instantiate the manager
    manager = DoppelManager(api_key)

    # Initialize action result values
    status = EXECUTION_STATE_COMPLETED
    output_message = "Alert updated successfully."
    result_value = True

    try:
        # Validate parameters
        if entity and alert_id:
            raise ValueError(
                "Only one of 'Entity' or 'Alert_ID' can be provided, not both.",
            )
        if not entity and not alert_id:
            raise ValueError("Either 'Entity' or 'Alert_ID' must be provided.")

        # Perform the update_alert action
        updated_alert = manager.update_alert(
            queue_state=queue_state,
            entity_state=entity_state,
            entity=entity,
            alert_id=alert_id,
        )
        if updated_alert:
            siemplify.result.add_result_json(
                updated_alert,
            )  # Store updated alert in the action result JSON
        else:
            raise Exception("Empty response or update failed.")
    except Exception as e:
        output_message = f"Failed to update alert: {e!s}"
        status = EXECUTION_STATE_FAILED
        result_value = False

    # Log results and complete the action
    siemplify.LOGGER.info(
        f"status: {status}\nresult_value: {result_value}\noutput_message: {output_message}",
    )
    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()
