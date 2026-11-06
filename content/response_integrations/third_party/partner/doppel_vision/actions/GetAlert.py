from __future__ import annotations

from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler

from ..core.config import create_manager_from_siemplify


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = "Get Alert Action"

    entity = siemplify.extract_action_param(param_name="Entity", default_value=None)
    alert_id = siemplify.extract_action_param(param_name="Alert_ID", default_value=None)

    status = EXECUTION_STATE_COMPLETED
    output_message = "Alert retrieved successfully."
    result_value = True

    try:
        if entity and alert_id:
            raise ValueError(
                "Only one of 'Entity' or 'Alert_ID' can be provided, not both.",
            )
        if not entity and not alert_id:
            raise ValueError("Either 'Entity' or 'Alert_ID' must be provided.")

        manager = create_manager_from_siemplify(siemplify)
        alert = manager.get_alert(entity=entity, alert_id=alert_id)
        siemplify.result.add_result_json(alert)
    except Exception as e:
        output_message = f"Failed to retrieve alert: {e!s}"
        status = EXECUTION_STATE_FAILED
        result_value = False

    siemplify.LOGGER.info(
        f"status: {status}\nresult_value: {result_value}\noutput_message: {output_message}",
    )
    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()
