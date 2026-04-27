from __future__ import annotations
import json
import urllib.parse

from slackblocks import SectionBlock, ActionsBlock
from slackblocks.elements import Button

from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler
from ..core.SlackManager import BaseURLException
from TIPCommon import (
    extract_action_param,
    extract_configuration_param,
    convert_comma_separated_to_list,
)
from ..core.consts import PROVIDER_NAME
from ..core import utils


SCRIPT_NAME = f"{PROVIDER_NAME} - BuildBlock"


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = SCRIPT_NAME
    siemplify.LOGGER.info("----------------- Main - Param Init -----------------")

    webhook_base_url = extract_configuration_param(
        siemplify,
        provider_name=PROVIDER_NAME,
        param_name="WebhookBaseURL",
        input_type=str,
        print_value=True,
    )

    question = extract_action_param(
        siemplify,
        param_name="Question",
        is_mandatory=True,
        print_value=True,
        input_type=str,
    )

    answers_buttons = extract_action_param(
        siemplify,
        param_name="Answers Buttons",
        is_mandatory=True,
        print_value=True,
        input_type=str,
    )

    siemplify_base_url = extract_action_param(
        siemplify,
        param_name="Siemplify Base URL",
        is_mandatory=True,
        print_value=True,
        input_type=str,
    )

    case_id = extract_action_param(
        siemplify,
        param_name="Case ID",
        is_mandatory=True,
        print_value=True,
        input_type=str,
    )

    token_uuid = extract_action_param(
        siemplify,
        param_name="Webhook Token UUID",
        is_mandatory=True,
        print_value=True,
        input_type=str,
    )

    siemplify.LOGGER.info("----------------- Main - Started -----------------")

    result = "false"
    status = EXECUTION_STATE_FAILED

    try:
        if not webhook_base_url:
            raise BaseURLException(
                f"Failed to execute action, "
                f"please specify the “Webhook Base URL” integration parameter."
            )

        if webhook_base_url[-1] != "/":
            webhook_base_url += "/"

        answers = convert_comma_separated_to_list(answers_buttons)
        try:
            buttons = []
            for answer in answers:
                encoded_answer = urllib.parse.quote(answer)
                answer_url = f"{webhook_base_url}{token_uuid}?Answer={encoded_answer}"
                button = Button(answer, f"{answer}", answer_url)
                buttons.append(button)

            view_case_text = "View Case in Google secops"
            secops_mode = utils.get_secops_mode()

            if secops_mode == "Disabled":
                view_case_url = f"{siemplify_base_url}/#/cases/{case_id}"
            else:
                view_case_url = f"{siemplify_base_url}/cases/{case_id}"

            view_case_button = Button(view_case_text, view_case_text, view_case_url)
            buttons.append(view_case_button)

            block_question = SectionBlock(question)
            blocks_actions = ActionsBlock(elements=buttons)
            blocks = [block_question, blocks_actions]

            json_blocks = [json.dumps(block._resolve()) for block in blocks]

            json_result = ",".join(json_blocks)
            json_result = f"[{json_result}]"

            # Validate JSON
            loaded_python_data = json.loads(json_result)
            assert len(loaded_python_data) == 2
            assert len(loaded_python_data[1]["elements"]) == len(answers) + 1

            # Set the execution results and add json result
            siemplify.result.add_result_json({"result": json_result})
            output_message = "Slack block was created successfully."
            result = "true"
        except Exception as e:
            output_message = (
                f"Failed to create a block because of the occurred error: {e}"
            )
        status = EXECUTION_STATE_COMPLETED
    except BaseURLException as e:
        output_message = f"{e}"
    except Exception as e:
        output_message = f"Failed to execute “Build Block” action! Error is {e}"

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(f"Status: {status}")
    siemplify.LOGGER.info(f"Result: {result}")
    siemplify.LOGGER.info(f"Output Message: {output_message}")
    siemplify.end(output_message, result, status)


if __name__ == "__main__":
    main()
