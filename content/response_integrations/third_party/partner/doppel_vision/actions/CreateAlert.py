from __future__ import annotations

from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler

from ..core.config import create_manager_from_siemplify


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = "Create Alert Action"

    entity = siemplify.extract_action_param(param_name="Entity", default_value=None)

    status = EXECUTION_STATE_COMPLETED
    output_message = "Alert created successfully."
    result_value = True

    try:
        manager = create_manager_from_siemplify(siemplify)
        alert_response = manager.create_alert(entity)
        siemplify.result.add_result_json(alert_response)
    except Exception as e:
        output_message = f"Failed to create alert: {e!s}"
        status = EXECUTION_STATE_FAILED
        result_value = False

    siemplify.LOGGER.info(
        f"status: {status}\nresult_value: {result_value}\noutput_message: {output_message}",
    )
    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()
