from __future__ import annotations

from shlex import quote

from TIPCommon.extraction import extract_job_param


def extract_feed_value(feed: dict) -> str:
    """Extracts IOC value"""
    pattern = feed.get("pattern")
    if pattern:
        return pattern.split(" = '")[1][:-2]
    return ""


def build_base_url(project_id: str, project_location: str, project_instance_id: str) -> str:
    """Generates SecOps API URL"""
    return f"https://{project_location}-chronicle.googleapis.com/v1alpha/projects/{project_id}/locations/{project_location}/instances/{project_instance_id}"


def build_taxii_data_table_payload(data_table_name: str) -> dict:
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
                "original_column": "confidence",
                "key_column": False,
                "column_type": "STRING",
            },
            {
                "column_index": 2,
                "original_column": "labels",
                "key_column": False,
                "column_type": "STRING",
            },
            {
                "column_index": 3,
                "original_column": "created",
                "key_column": False,
                "column_type": "STRING",
            },
            {
                "column_index": 4,
                "original_column": "modified",
                "key_column": False,
                "column_type": "STRING",
            },
        ],
    }


def build_taxii_indicators_payload(feeds: list[dict]) -> dict[str, list[dict]] | None:
    """
    Converts ANY.RUN IOCs to the SecOps DataTable rows

    :param feeds: ANY.RUN Indicators
    :return: DataTable rows
    """
    payload: dict[str, list[dict]] = {"requests": []}

    for feed in feeds:
        payload["requests"].append({
            "dataTableRow": {
                "values": [
                    extract_feed_value(feed),
                    str(feed.get("confidence")),
                    ",".join(labels) if (labels := feed.get("labels")) else "-",
                    feed.get("created"),
                    feed.get("modified"),
                ]
            }
        })

    return payload


def setup_job_proxy(siemplify) -> str | None:
    """Generates a proxy connection string"""
    if extract_job_param(siemplify, param_name="Enable proxy", input_type=bool):
        host = quote(extract_job_param(siemplify, param_name="Proxy host"))
        port = quote(extract_job_param(siemplify, param_name="Proxy port"))

        return f"https://{host}:{port}"

    return None
