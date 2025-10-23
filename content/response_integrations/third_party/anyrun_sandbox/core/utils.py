from __future__ import annotations

from shlex import quote

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
        "opt_timeout": quote(extract_action_param(siemplify, param_name="Opt Timeout In Seconds")),
        "opt_network_connect": quote(
            extract_action_param(siemplify, param_name="Opt Network Connect")
        ),
        "opt_network_fakenet": quote(
            extract_action_param(siemplify, param_name="Opt Network Fakenet")
        ),
        "opt_network_tor": quote(extract_action_param(siemplify, param_name="Opt Network Tor")),
        "opt_network_geo": quote(extract_action_param(siemplify, param_name="Opt Network Geo")),
        "opt_network_mitm": quote(extract_action_param(siemplify, param_name="Opt Network Mitm")),
        "opt_network_residential_proxy": quote(
            extract_action_param(siemplify, param_name="Opt Network Residential Proxy")
        ),
        "opt_network_residential_proxy_geo": quote(
            extract_action_param(siemplify, param_name="Opt Network Residential Proxy Geo")
        ),
        "opt_privacy_type": quote(extract_action_param(siemplify, param_name="Opt Privacy Type")),
        "env_locale": quote(extract_action_param(siemplify, param_name="Env Locale")),
        "user_tags": quote(extract_action_param(siemplify, param_name="User Tags")),
    }


def build_base_url(project_id: str, project_location: str, project_instance_id: str) -> str:
    """Generates SecOps API URL"""
    return f"https://{project_location}-chronicle.googleapis.com/v1alpha/projects/{project_id}/locations/{project_location}/instances/{project_instance_id}"


def build_sandbox_data_table_payload(data_table_name: str) -> dict:
    """
    Generates DataTable schema

    :param data_table_name: DataTable name
    :return: DataTable payload
    """
    return {
        "name": data_table_name,
        "display_name": data_table_name,
        "description": data_table_name,
        "column_info": [
            {
                "column_index": 0,
                "original_column": "value",
                "key_column": True,
                "column_type": "STRING",
            },
            {
                "column_index": 1,
                "original_column": "type",
                "key_column": True,
                "column_type": "STRING",
            },
            {
                "column_index": 2,
                "original_column": "confidence",
                "key_column": False,
                "column_type": "STRING",
            },
            {
                "column_index": 3,
                "original_column": "anyrun_task_url",
                "key_column": False,
                "column_type": "STRING",
            },
        ],
    }


def build_sandbox_indicators_payload(
    feeds: list[dict], task_uuid: str
) -> dict[str, list[dict]] | None:
    """
    Converts ANY.RUN IOCs to the SecOps DataTable rows

    :param feeds: ANY.RUN Indicators
    :param task_uuid: ANY.RUN Sandbox analysis UUID
    :return: DataTable rows
    """
    payload: dict[str, list[dict]] = {"requests": []}

    for feed in feeds:
        if feed.get("reputation") in (1, 2):
            payload["requests"].append({
                "dataTableRow": {
                    "values": [
                        feed.get("ioc"),
                        feed.get("type"),
                        {1: "Suspiciuos", 2: "Malicious"}.get(feed.get("reputation", 2)),
                        f"https://app.any.run/tasks/{task_uuid}",
                    ]
                }
            })

    return payload


def setup_action_proxy(siemplify) -> str | None:
    """Generates a proxy connection string"""
    if extract_configuration_param(
        siemplify, Config.INTEGRATION_NAME, param_name="Enable proxy", input_type=bool
    ):
        host = quote(
            extract_configuration_param(siemplify, Config.INTEGRATION_NAME, param_name="Proxy host")
        )
        port = quote(
            extract_configuration_param(siemplify, Config.INTEGRATION_NAME, param_name="Proxy port")
        )

        return f"https://{host}:{port}"

    return None
