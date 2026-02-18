from typing import Any, Dict

from ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from SiemplifyUtils import output_handler
from soar_sdk.SiemplifyAction import SiemplifyAction

from ..core.constants import INTEGRATION_NAME, LIVE_URL_SCAN_SCRIPT_NAME
from ..core.silent_push_manager import SilentPushManager


@output_handler
def main():
    siemplify = SiemplifyAction()

    siemplify.script_name = LIVE_URL_SCAN_SCRIPT_NAME

    # Extract Integration config
    server_url = siemplify.extract_configuration_param(INTEGRATION_NAME, "Silent Push Server")
    api_key = siemplify.extract_configuration_param(INTEGRATION_NAME, "API Key")

    url = siemplify.extract_action_param("URL", print_value=True)
    platform: str = siemplify.extract_action_param("Platform", print_value=True)
    browser: str = siemplify.extract_action_param("Browser", print_value=True)
    os: str = siemplify.extract_action_param("Os", print_value=True)
    region: str = siemplify.extract_action_param("Region", print_value=True)

    try:
        # Validate platform, os, browser, and region
        validation_errors = validate_parameters(platform, os, browser, region)
        if validation_errors:
            raise ValueError(validation_errors)

        sp_manager = SilentPushManager(server_url, api_key, logger=siemplify.LOGGER)
        raw_response = sp_manager.live_url_scan(url, platform, os, browser, region)
        scan_results = raw_response.get("response", {}).get("scan", {})

        readable_output = format_scan_results(scan_results, url)
        siemplify.result.add_result_json({
            "message": readable_output.get("message"),
            "url": readable_output.get("url"),
            "scan_results": readable_output.get("scan_results"),
        })
        if not scan_results:
            error_message = f"No Scan data found for URL {url}."
            siemplify.LOGGER.error(error_message)
            status = EXECUTION_STATE_FAILED
            siemplify.end(error_message, "false", status)

        output_message = f"url: {url}, scan_results: {scan_results}"
        status = EXECUTION_STATE_COMPLETED
        result_value = True
    except Exception as error:
        result_value = False
        status = EXECUTION_STATE_FAILED
        output_message = (
            f"Failed to retrieve scan data found for URL {url} "
            f"for {INTEGRATION_NAME} server! Error: {error}"
        )
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


def validate_parameters(platform: str, os: str, browser: str, region: str) -> str:
    """Validate the platform, os, browser, and region values."""
    valid_platforms = ["Desktop", "Mobile", "Crawler"]
    valid_os = ["Windows", "Linux", "MacOS", "iOS", "Android"]
    valid_browsers = ["Firefox", "Chrome", "Edge", "Safari"]
    valid_regions = ["US", "EU", "AS", "TOR"]

    errors = []
    if platform and platform not in valid_platforms:
        errors.append(f"Invalid platform. Must be one of: {', '.join(valid_platforms)}")
    if os and os not in valid_os:
        errors.append(f"Invalid OS. Must be one of: {', '.join(valid_os)}")
    if browser and browser not in valid_browsers:
        errors.append(f"Invalid browser. Must be one of: {', '.join(valid_browsers)}")
    if region and region not in valid_regions:
        errors.append(f"Invalid region. Must be one of: {', '.join(valid_regions)}")

    return "\n".join(errors)


def format_scan_results(scan_results: Dict[str, Any], url: str) -> Dict[str, Any]:
    """
    Format the scan results for Google SecOps integration.

    Args:
        scan_results (dict): API response data from a URL scan
        url (str): The scanned URL

    Returns:
        dict: JSON object with human-readable message and raw results
    """
    if not isinstance(scan_results, dict):
        return {
            "message": f"Unexpected response format for URL scan. Response: {scan_results}",
            "raw_results": scan_results,
            "url": url,
        }

    if not scan_results:
        return {
            "message": f"No scan results found for URL: {url}",
            "raw_results": scan_results,
            "url": url,
        }

    # Instead of tableToMarkdown, just return results as JSON
    return {
        "message": f"URL Scan Results for {url}",
        "scan_results": scan_results,
        "url": url,
    }


if __name__ == "__main__":
    main()
