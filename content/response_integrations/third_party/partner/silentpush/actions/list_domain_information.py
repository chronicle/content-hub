from typing import Any, Dict

from ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from SiemplifyUtils import output_handler
from soar_sdk.SiemplifyAction import SiemplifyAction

from ..core.constants import INTEGRATION_NAME, LIST_DOMAIN_INFORMATION_SCRIPT_NAME
from ..core.silent_push_manager import SilentPushManager


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = LIST_DOMAIN_INFORMATION_SCRIPT_NAME

    # Extract Integration config
    server_url = siemplify.extract_configuration_param(INTEGRATION_NAME, "Silent Push Server")
    api_key = siemplify.extract_configuration_param(INTEGRATION_NAME, "API Key")

    domain = siemplify.extract_action_param("Domains", print_value=True)
    domains: list = domain.split(",")
    fetch_risk_score = siemplify.extract_action_param("Fetch Risk Score", print_value=True)
    fetch_whois_info = siemplify.extract_action_param("Fetch Whois Info", print_value=True)

    if fetch_risk_score == "false":
        fetch_risk_score: bool = False
    else:
        fetch_risk_score: bool = True

    try:
        sp_manager = SilentPushManager(server_url, api_key, logger=siemplify.LOGGER)
        response = sp_manager.list_domain_information(domains, fetch_risk_score, fetch_whois_info)

        records = response.get("domains", [])
        markdown_response = format_domain_information(response, fetch_risk_score, fetch_whois_info)
        json_response = format_domain_information_json(response, fetch_risk_score, fetch_whois_info)
        if not records:
            error_message = f"No domain info found for {domains}"
            siemplify.LOGGER.error(error_message)
            status = EXECUTION_STATE_FAILED
            siemplify.end(error_message, "false", status)

        output_message = f"Result: {markdown_response}"
        siemplify.result.add_result_json({"domain_information_results": json_response})
        status = EXECUTION_STATE_COMPLETED
        result_value = True
    except Exception as error:
        result_value = False
        status = EXECUTION_STATE_FAILED
        output_message = (
            f"Failed to domain info for {domains} for {INTEGRATION_NAME} server! Error: {error}"
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


def format_domain_information(
    response: Dict[str, Any], fetch_risk_score: bool, fetch_whois_info: bool
) -> str:
    """
    Format the response data into markdown-style text for Google SecOps.

    Args:
        response (Dict[str, Any]): API response data
        fetch_risk_score (bool): Whether to include risk score data
        fetch_whois_info (bool): Whether to include WHOIS data

    Returns:
        str: Markdown-formatted response
    """
    markdown = ["# Domain Information Results\n"]

    for domain_data in response.get("domains", []):
        domain = domain_data.get("domain", "N/A")
        markdown.append(f"## Domain: {domain}")

        # Domain Information
        markdown.append("### Domain Information")
        for key, value in domain_data.items():
            if isinstance(value, dict):
                continue  # handled later
            markdown.append(f"- **{key}**: {value}")

        # Risk Score Information
        if fetch_risk_score:
            markdown.append("\n### Risk Assessment")
            risk_score = domain_data.get("risk_score", "N/A")
            risk_expl = domain_data.get("risk_score_explanation", "N/A")
            markdown.append(f"- **Risk Score**: {risk_score}")
            markdown.append(f"- **Explanation**: {risk_expl}")

        # WHOIS Information
        if fetch_whois_info:
            whois_info = domain_data.get("whois_info", {})
            markdown.append("\n### WHOIS Information")
            if whois_info and isinstance(whois_info, dict):
                if "error" in whois_info:
                    markdown.append(f"- WHOIS Error: {whois_info['error']}")
                else:
                    for k, v in whois_info.items():
                        markdown.append(f"- **{k}**: {v}")
            else:
                markdown.append("- No WHOIS information available")

        markdown.append("\n---\n")

    return "\n".join(markdown)


def format_domain_information_json(
    response: Dict[str, Any], fetch_risk_score: bool, fetch_whois_info: bool
):
    """
    Format the response data into JSON format for Google SecOps action.

    Args:
        response (Dict[str, Any]): API response data
        fetch_risk_score (bool): Whether to include risk score data
        fetch_whois_info (bool): Whether to include WHOIS data

    Returns:
        Dict[str, Any]: JSON-formatted response
    """
    results = []

    for domain_data in response.get("domains", []):
        domain_result = {
            "domain": domain_data.get("domain", "N/A"),
            "domain_information": {k: v for k, v in domain_data.items() if not isinstance(v, dict)},
        }

        # Risk score
        if fetch_risk_score:
            domain_result["risk_assessment"] = {
                "risk_score": domain_data.get("risk_score", "N/A"),
                "risk_score_explanation": domain_data.get("risk_score_explanation", "N/A"),
            }

        # WHOIS info
        if fetch_whois_info:
            whois_info = domain_data.get("whois_info", {})
            if whois_info and isinstance(whois_info, dict):
                if "error" in whois_info:
                    domain_result["whois_info"] = {"error": whois_info["error"]}
                else:
                    domain_result["whois_info"] = whois_info
            else:
                domain_result["whois_info"] = {"message": "No WHOIS information available"}

        results.append(domain_result)

    return results


if __name__ == "__main__":
    main()
