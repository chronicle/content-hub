from __future__ import annotations
from soar_sdk.SiemplifyAction import SiemplifyAction
from ..core.RecordedFutureManager import RecordedFutureManager
from soar_sdk.SiemplifyUtils import output_handler
from TIPCommon import extract_configuration_param, extract_action_param
from ..core.constants import PROVIDER_NAME, GET_ALERT_DETAILS_SCRIPT_NAME
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from ..core.exceptions import RecordedFutureNotFoundError, RecordedFutureUnauthorizedError


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = GET_ALERT_DETAILS_SCRIPT_NAME
    siemplify.LOGGER.info("----------------- Main - Param Init -----------------")

    api_url = extract_configuration_param(
        siemplify, provider_name=PROVIDER_NAME, param_name="ApiUrl"
    )
    api_key = extract_configuration_param(
        siemplify, provider_name=PROVIDER_NAME, param_name="ApiKey"
    )
    verify_ssl = extract_configuration_param(
        siemplify,
        provider_name=PROVIDER_NAME,
        param_name="Verify SSL",
        default_value=False,
        input_type=bool,
    )

    alert_id = extract_action_param(siemplify, param_name="Alert ID", is_mandatory=True)

    siemplify.LOGGER.info("----------------- Main - Started -----------------")
    is_success = False
    status = EXECUTION_STATE_FAILED

    try:
        recorded_future_manager = RecordedFutureManager(
            api_url, api_key, verify_ssl=verify_ssl
        )
        alert_object = recorded_future_manager.get_information_about_alert(alert_id)
        siemplify.result.add_result_json(alert_object.to_json())
        siemplify.result.add_link("Web Report Link:", alert_object.alert_url)

        is_success = True
        status = EXECUTION_STATE_COMPLETED
        output_message = f"Successfully fetched the following Alert ID details from Recorded Future: \n{alert_id}"

    except RecordedFutureUnauthorizedError as e:
        output_message = (
            f"Unauthorized - please check your API token and try again. {e}"
        )
    except RecordedFutureNotFoundError as e:
        output_message = (
            "Requested Alert ID wasn't found in Recorded Future, or something went wrong in executing "
            "action {}. Reason: {}".format(GET_ALERT_DETAILS_SCRIPT_NAME, e)
        )
    except Exception as e:
        output_message = (
            f"Error executing action {GET_ALERT_DETAILS_SCRIPT_NAME}. Reason: {e}"
        )

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(f"Output Message: {output_message}")
    siemplify.LOGGER.info(f"Result: {is_success}")
    siemplify.LOGGER.info(f"Status: {status}")

    siemplify.end(output_message, is_success, status)


if __name__ == "__main__":
    main()
