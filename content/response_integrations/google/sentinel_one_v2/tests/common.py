from __future__ import annotations
import json
from integration_testing.common import get_def_file_content
import pathlib
import copy

from TIPCommon.types import SingleJson

from integration_testing.requests.response import MockResponse
from integration_testing.common import get_def_file_content

MOCK_DATA_FILE_PATH: pathlib.Path = pathlib.Path(__file__).parent / "mock_data.json"
MOCK_DATA: SingleJson = get_def_file_content(MOCK_DATA_FILE_PATH)

MOCK_AGENT: SingleJson = MOCK_DATA["MOCK_AGENT"]
MOCK_THREAT: SingleJson = MOCK_DATA["MOCK_THREAT"]
MOCK_THREAT_FULL: SingleJson = MOCK_DATA["MOCK_THREAT_FULL"]
MOCK_AGENT_2: SingleJson = MOCK_DATA["MOCK_AGENT_2"]
MOCK_AGENT_3: SingleJson = MOCK_DATA["MOCK_AGENT_3"]
MOCK_SITE_DATA: SingleJson = MOCK_DATA["MOCK_SITE_DATA"]

MOCK_INIT_QUERY: SingleJson = {
    "data": {
        "queryId": "0",
        "queryModeInfo": {
            "lastActivatedAt": "2022-07-19T21:19:31+00:00",
            "mode": "scalyr",
        },
    }
}

MOCK_QUERY_STATUS: SingleJson = {
    "data": {
        "progressStatus": 100,
        "queryModeInfo": {
            "lastActivatedAt": "2022-07-19T21:19:31+00:00",
            "mode": "scalyr",
        },
        "responseState": "FINISHED",
        "warnings": None,
    }
}

MOCK_FINAL_RESPONSE = {
    "data": [
        {
            "accountId": "0",
        },
    ]
}

MOCK_CLOUD_ALERT: SingleJson = {
            "agentDetectionInfo": {
                "accountId": "172783928968",
                "machineType": "server",
                "name": "instance-2",
                "osFamily": "linux",
                "osName": "Linux",
                "osRevision": "Debian GNU/11 (bullseye) 5.10.0-33-cloud-amd64",
                "siteId": "172783928968",
                "uuid": "2128989181-37d4-1023-e372-b0a4f71d403d",
                "version": "23.3.2.12"
            },
            "agentRealtimeInfo": {
                "id": "21430916260028895463",
                "infected": "true",
                "isActive": "true",
                "isDecommissioned": "false",
                "machineType": "server",
                "name": "instance-2",
                "os": "linux"
            },
            "alertInfo": {
                "alertId": "2228723729329392",
                "analystVerdict": "Suspicious",
                "createdAt": "2025-06-02T13:49:34.963000Z",
                "dvEventId": "01JWREEZCSKV7TR6WP623YFNNY_5",
                "eventType": "PROCESSCREATION",
                "hitType": "Events",
                "incidentStatus": "Unresolved"
            }}

TEST_ALERT_ID: str = "1234567890"

def get_endpoint_list(request_history: list[MockResponse]) -> list[str]:
    """Return a list of all endpoints that the session has sent requests to."""
    endpoints: list[str] = []
    for request in request_history:
        endpoints.append(request.request.url.path)
    return endpoints


def generate_init_query_json(query_id: str) -> SingleJson:
    """Generates the init query json with specific query id"""
    init_query_json = copy.deepcopy(MOCK_INIT_QUERY)
    init_query_json["data"]["queryId"] = query_id
    return init_query_json


def generate_final_response_json(account_id: str) -> SingleJson:
    """Generates the final response json with specific account id"""
    final_response_json: SingleJson = copy.deepcopy(MOCK_FINAL_RESPONSE)
    final_response_json["data"][0]["accountId"] = account_id
    return final_response_json
INTEGRATION_PATH: pathlib.Path = pathlib.Path(__file__).parent.parent
CONFIG_PATH: pathlib.Path = pathlib.Path(__file__).parent / 'config.json'
CONFIG: dict = get_def_file_content(CONFIG_PATH) if CONFIG_PATH.exists() else {}
