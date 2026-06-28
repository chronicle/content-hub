from __future__ import annotations
from functools import partial

from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED

from TIPCommon.extraction import extract_action_param, extract_configuration_param
from core import constants
from core.utils import GraphSecurityManagerConfig, init_graph_security_manager


SPLIT_CHAR = ","


def validate_feedback(
    feedback: str,
    valid_values: list[str],
    siemplify: SiemplifyAction,
) -> None:
    """Validates the feedback values.

    Args:
        feedback (str): Feedback value.
        valid_values (list[str]): Valid values for feedback.
        siemplify (SiemplifyAction): SiemplifyAction object.
    """
    if feedback and feedback not in valid_values:
        output_message = (
            f"Feedback {feedback} is invalid. Valid values are: "
            f"{', '.join(valid_values)}. Aborting."
        )
        siemplify.LOGGER.error(output_message)
        siemplify.end(output_message, "false", EXECUTION_STATE_FAILED)


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = constants.UPDATE_ALERT_SCRIPT_NAME
    siemplify.LOGGER.info("================= Main - Param Init =================")

    client_id = extract_configuration_param(
        siemplify,
        provider_name=constants.INTEGRATION_NAME,
        param_name="Client ID",
        is_mandatory=True,
        input_type=str,
    )
    secret_id = extract_configuration_param(
        siemplify,
        provider_name=constants.INTEGRATION_NAME,
        param_name="Secret ID",
        is_mandatory=False,
        input_type=str,
    )
    certificate_path = extract_configuration_param(
        siemplify,
        provider_name=constants.INTEGRATION_NAME,
        param_name="Certificate Path",
        is_mandatory=False,
        input_type=str,
    )
    certificate_password = extract_configuration_param(
        siemplify,
        provider_name=constants.INTEGRATION_NAME,
        param_name="Certificate Password",
        is_mandatory=False,
        input_type=str,
    )
    tenant = extract_configuration_param(
        siemplify,
        provider_name=constants.INTEGRATION_NAME,
        param_name="Tenant",
        is_mandatory=True,
        input_type=str,
    )
    use_v2_api = extract_configuration_param(
        siemplify=siemplify,
        provider_name=constants.INTEGRATION_NAME,
        param_name="Use V2 API",
        input_type=bool,
        default_value=False,
        print_value=True,
    )
    verify_ssl = extract_configuration_param(
        siemplify=siemplify,
        provider_name=constants.INTEGRATION_NAME,
        param_name="Verify SSL",
        input_type=bool,
        default_value=False,
        print_value=True,
    )

    alert_id = extract_action_param(
        siemplify,
        param_name="Alert ID",
        input_type=str,
        is_mandatory=True,
        print_value=True,
    )
    assigned_to = extract_action_param(
        siemplify,
        param_name="Assigned To",
        input_type=str,
        is_mandatory=False,
        print_value=True,
    )
    closed_date_time = extract_action_param(
        siemplify,
        param_name="Closed Date Time",
        input_type=str,
        is_mandatory=False,
        print_value=True,
    )
    comments = extract_action_param(
        siemplify,
        param_name="Comments",
        input_type=str,
        is_mandatory=False,
        print_value=True,
    )
    feedback = extract_action_param(
        siemplify,
        param_name="Feedback",
        input_type=str,
        is_mandatory=False,
        print_value=True,
    )
    status = extract_action_param(
        siemplify,
        param_name="Status",
        input_type=str,
        is_mandatory=False,
        print_value=True,
    )
    tags = extract_action_param(
        siemplify,
        param_name="Tags",
        input_type=str,
        is_mandatory=False,
        print_value=True,
    )

    comments_list = []
    tags_list = []

    if comments:
        comments_list = [comment.strip() for comment in comments.split(SPLIT_CHAR)]

    if tags:
        tags_list = [tag.strip() for tag in tags.split(SPLIT_CHAR)]

    valid_values = (
        constants.CLASSIFICATION_VALUES
        if use_v2_api
        else constants.VALID_ALERT_FEEDBACKS
    )
    validate_feedback(feedback=feedback, valid_values=valid_values, siemplify=siemplify)

    if status and status not in constants.VALID_ALERT_STATUSES:
        output_message = (
            f"Status {status} is invalid. Valid values are: "
            f"{', '.join(constants.VALID_ALERT_STATUSES)}. Aborting.")
        siemplify.LOGGER.error(output_message)
        siemplify.end(output_message, "false", EXECUTION_STATE_FAILED)

    if not use_v2_api:
        valid_comments = []
        for comment in comments_list:
            if comment not in constants.VALID_ALERT_COMMENTS:
                siemplify.LOGGER.warn(
                    f"Comment \"{comment}\" is invalid. Valid values are: "
                    f"{', '.join(constants.VALID_ALERT_COMMENTS)}. Comment will be "
                    "ignored."
                )
            else:
                valid_comments.append(comment)
    else:
        valid_comments = comments

    siemplify.LOGGER.info("----------------- Main - Started -----------------")
    config = GraphSecurityManagerConfig(
        client_id=client_id,
        secret_id=secret_id,
        certificate_path=certificate_path,
        certificate_password=certificate_password,
        tenant=tenant,
        verify_ssl=verify_ssl,
        chronicle_soar=siemplify,
    )
    try:
        siemplify.LOGGER.info("Connecting to Microsoft Graph Security.")
        mtm = init_graph_security_manager(
            config=config,
            use_v2_api=use_v2_api,
        )
        siemplify.LOGGER.info("Connected successfully.")

        siemplify.LOGGER.info(f"Updating alert {alert_id}")
        update_alert_func = partial(
            mtm.update_alert,
            alert_id=alert_id,
            assigned_to=assigned_to,
            comments=valid_comments,
            status=status,
            feedback=feedback,
        )
        alert_after_update = (
            update_alert_func()
            if use_v2_api
            else update_alert_func(
                closed_date_time=closed_date_time,
                tags=tags_list,
            )
        )

        if alert_after_update:
            output_message = f"Alert {alert_id} was successfully updated."
            siemplify.LOGGER.info(output_message)
            result_value = "true"

        else:
            output_message = f"Failed to update alert {alert_id}."
            siemplify.LOGGER.info(output_message)
            result_value = "false"

        action_status = EXECUTION_STATE_COMPLETED

    except Exception as e:
        siemplify.LOGGER.error(f"Some errors occurred. Error: {e}")
        siemplify.LOGGER.exception(e)
        action_status = EXECUTION_STATE_FAILED
        result_value = "false"
        output_message = f"Some errors occurred. Error: {e}"

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(f"Status: {action_status}:")
    siemplify.LOGGER.info(f"Result Value: {result_value}")
    siemplify.LOGGER.info(f"Output Message: {output_message}")
    siemplify.end(output_message, result_value, action_status)


if __name__ == "__main__":
    main()
