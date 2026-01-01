from __future__ import annotations

import requests
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_INPROGRESS
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler

SCRIPT_NAME = "WaitUntilWebResourceIsUp"


def is_web_resource_up(url, should_include_content=None):
    resp = requests.get(url, timeout=5.0)

    if resp.ok and not should_include_content:
        return True

    if (
        resp.ok
        and should_include_content
        and should_include_content.lower() in resp.text.lower()
    ):
        return True


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = SCRIPT_NAME

    result_value = False

    url = siemplify.extract_action_param(param_name="URL")

    siemplify.LOGGER.info("----------------- Main - Started -----------------")
    try:
        result_value = is_web_resource_up(url)
    except Exception as ex:
        siemplify.LOGGER.error(f"General error performing action {SCRIPT_NAME}")
        siemplify.LOGGER.exception(ex)

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")

    status = EXECUTION_STATE_COMPLETED if result_value else EXECUTION_STATE_INPROGRESS
    output_message = f"Web resource {url} is {'up' if result_value else 'down'}"
    siemplify.LOGGER.info(
        f"\n  status: {status}\n  result_value: {result_value}\n  output_message: {output_message}",
    )
    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()
