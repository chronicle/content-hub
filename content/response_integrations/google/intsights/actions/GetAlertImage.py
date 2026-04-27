from __future__ import annotations
from soar_sdk.SiemplifyUtils import output_handler
from soar_sdk.SiemplifyAction import SiemplifyAction
from ..core.IntsightsManager import IntsightsManager
from TIPCommon import extract_configuration_param, extract_action_param
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from ..core.consts import INTEGRATION_NAME, GET_ALERT_IMAGE_ACTION
import base64
from soar_sdk.SiemplifyDataModel import InsightSeverity, InsightType
from ..core.utils import string_to_multi_value


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = GET_ALERT_IMAGE_ACTION
    siemplify.LOGGER.info("----------------- Main - Param Init -----------------")

    api_root = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Api Root",
        is_mandatory=True,
        print_value=True,
    )
    account_id = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Account ID",
        is_mandatory=True,
        print_value=True,
    )
    api_key = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Api Key",
        is_mandatory=True,
        print_value=False,
    )
    verify_ssl = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Verify SSL",
        default_value=False,
        input_type=bool,
        is_mandatory=True,
        print_value=True,
    )

    alert_image_ids = string_to_multi_value(
        extract_action_param(
            siemplify, param_name="Alert Image IDs", is_mandatory=True, print_value=True
        )
    )

    siemplify.LOGGER.info("----------------- Main - Started -----------------")

    output_message = ""
    status = EXECUTION_STATE_COMPLETED
    result_value = True
    successfully_processed_ids, failed_processed_ids, list_of_images = [], [], []

    try:
        intsight_manager = IntsightsManager(
            server_address=api_root,
            account_id=account_id,
            api_key=api_key,
            api_login=False,
            verify_ssl=verify_ssl,
            force_check_connectivity=True,
        )
        for alert_image_id in alert_image_ids:
            try:
                image_raw = intsight_manager.get_alert_image(
                    alert_image_id=alert_image_id
                )
                successfully_processed_ids.append(alert_image_id)
                list_of_images.append(base64.b64encode(image_raw))
            except Exception as e:
                failed_processed_ids.append(alert_image_id)
                siemplify.LOGGER.error(
                    f"An error occurred on Alert Image ID {alert_image_id}"
                )
                siemplify.LOGGER.exception(e)

        if len(failed_processed_ids) == len(alert_image_ids):
            output_message = "No images were retrieved"
            siemplify.LOGGER.info(output_message)

        else:
            if successfully_processed_ids:
                output_message += (
                    f"Successfully retrieved images from the following IDs in Intsights:"
                    f" {', '.join([processed_id for processed_id in successfully_processed_ids])}."
                )
                siemplify.LOGGER.info(
                    f"Successfully retrieved images from the following IDs in Intsights:"
                    f" {', '.join([processed_id for processed_id in successfully_processed_ids])}."
                )

                insight_content = ""
                json_result = []
                for image in list_of_images:
                    insight_content += f'<img src="data:image/jpeg;base64,{image.decode("utf-8")}"><br></br>'
                    json_result.append(
                        {
                            "image_name": successfully_processed_ids[
                                list_of_images.index(image)
                            ],
                            "image_base64_content": image.decode("utf-8"),
                        }
                    )

                siemplify.create_case_insight(
                    triggered_by=INTEGRATION_NAME,
                    title="Retrieved Images",
                    content=insight_content,
                    entity_identifier="",
                    severity=InsightSeverity.INFO,
                    insight_type=InsightType.General,
                )

                siemplify.result.add_result_json(json_result)

            if failed_processed_ids:
                output_message += (
                    f"\nAction wasn't able to successfully retrieve images from the following IDs in "
                    f"Intsights: {', '.join([processed_id for processed_id in failed_processed_ids])}."
                )
                siemplify.LOGGER.info(
                    f"Action wasn't able to successfully retrieve images from the following IDs in "
                    f"Intsights: {', '.join([processed_id for processed_id in failed_processed_ids])}."
                )
    except Exception as e:
        output_message = f"Error executing action {GET_ALERT_IMAGE_ACTION}. Reason: {e}"
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
