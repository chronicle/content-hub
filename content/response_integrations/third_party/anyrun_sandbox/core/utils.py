from __future__ import annotations

from TIPCommon.extraction import (
    extract_action_param,
    extract_configuration_param,
)

from ..core.config import Config


def prepare_report_comment(results: list[dict]) -> str:
    """
    Generates a comment using Suspicious and Malicious IOCs data

    :param results: ANY.RUN Sandbox analysis results
    :return: Complete comment
    """
    raws = ""

    for feed in results:
        if feed.get("reputation") in (1, 2):
            verdict = {1: "Suspiciuos", 2: "Malicious"}.get(feed.get("reputation", 2))
            raws += f"Type: {feed.get('type')} Value: {feed.get('ioc')} Verdict: {verdict}\n"

    return (
        "ANY.RUN Sandbox Indicators summary:\n" + raws
        if raws
        else "Suspiciuos or Malicious indicators not found"
    )


def prepare_base_params(siemplify) -> dict[str, str]:
    """Extracts analysis options"""
    return {
        "opt_timeout": extract_action_param(siemplify, param_name="Timeout In Seconds"),
        "opt_network_connect": extract_action_param(siemplify, param_name="Network Connect"),
        "opt_network_fakenet": extract_action_param(siemplify, param_name="Network Fakenet"),
        "opt_network_tor": extract_action_param(siemplify, param_name="Network Tor"),
        "opt_network_geo": extract_action_param(siemplify, param_name="Network Geo"),
        "opt_network_mitm": extract_action_param(siemplify, param_name="Network Mitm"),
        "opt_network_residential_proxy": extract_action_param(
            siemplify, param_name="Network Residential Proxy"
        ),
        "opt_network_residential_proxy_geo": extract_action_param(
            siemplify, param_name="Network Residential Proxy Geo"
        ),
        "opt_privacy_type": extract_action_param(siemplify, param_name="Analysis Privacy Type"),
        "env_locale": extract_action_param(siemplify, param_name="System's language"),
        "user_tags": extract_action_param(siemplify, param_name="User Tags"),
    }


def setup_action_proxy(siemplify) -> str | None:
    """Generates a proxy connection string"""
    if extract_configuration_param(
        siemplify, Config.INTEGRATION_NAME, param_name="Enable proxy", input_type=bool
    ):
        host = extract_configuration_param(
            siemplify, Config.INTEGRATION_NAME, param_name="Proxy host"
        )
        port = extract_configuration_param(
            siemplify, Config.INTEGRATION_NAME, param_name="Proxy port"
        )

        return f"https://{host}:{port}"

    return None
