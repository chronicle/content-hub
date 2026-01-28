from urllib.parse import urlparse

import requests
from ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from SiemplifyUtils import output_handler
from soar_sdk.SiemplifyAction import SiemplifyAction

from ..core.constants import INTEGRATION_NAME, SCREENSHOT_URL_SCRIPT_NAME
from ..core.silent_push_manager import SilentPushManager


@output_handler
def main():
    siemplify = SiemplifyAction()

    siemplify.script_name = SCREENSHOT_URL_SCRIPT_NAME

    # Extract Integration config
    server_url = siemplify.extract_configuration_param(INTEGRATION_NAME, "Silent Push Server")
    api_key = siemplify.extract_configuration_param(INTEGRATION_NAME, "API Key")

    url = siemplify.extract_action_param("url", print_value=True)

    try:
        sp_manager = SilentPushManager(server_url, api_key, logger=siemplify.LOGGER)
        result = sp_manager.screenshot_url(url)
        siemplify.LOGGER.info(result)
        if result.get("error"):
            raise ValueError(result.get("error"))

        if not result.get("screenshot_url"):
            raise ValueError("screenshot_url is missing from API response.")

        screenshot_url = result["screenshot_url"]
        parsed_url = urlparse(screenshot_url)

        if not parsed_url.scheme or not parsed_url.netloc:
            raise ValueError(f"Invalid screenshot URL format: {screenshot_url}")

        server_url = f"{parsed_url.scheme}://{parsed_url.netloc}"
        url_suffix = parsed_url.path
        if parsed_url.query:
            url_suffix += f"?{parsed_url.query}"

        full_url = server_url + url_suffix
        image_response = requests.get(full_url, stream=True)

        if not image_response or image_response.status_code != 200:
            error_message = (
                f"Failed to download screenshot image: "
                f"HTTP {getattr(image_response, 'status_code', 'No response')}"
            )
            siemplify.LOGGER.error(error_message)
            status = EXECUTION_STATE_FAILED
            siemplify.end(error_message, "false", status)

        output_message = f"screenshot_url : {result.get('screenshot_url')}"
        status = EXECUTION_STATE_COMPLETED
        result_value = True
        siemplify.result.add_result_json({
            "url": url,
            "screenshot_url": result.get("screenshot_url"),
        })
    except Exception as error:
        result_value = False
        status = EXECUTION_STATE_FAILED
        output_message = f"Failed to retrieve data  for {INTEGRATION_NAME} server! Error: {error}"
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(error)

    for entity in siemplify.target_entities:
        print(entity.identifier)

    siemplify.LOGGER.info(
        "\n  status: {}\n  result_value: {}\n  output_message: {}".format(
            status, result_value, output_message
        )
    )
    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()
