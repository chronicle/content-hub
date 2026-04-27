from __future__ import annotations
from soar_sdk.SiemplifyDataModel import EntityTypes

INTEGRATION_NAME = "CiscoThreatGrid"

# Action script names
GET_SUBMISSIONS_SCRIPT_NAME = f"{INTEGRATION_NAME} - GetSubmissions"

WAITING_STATE = "wait"
TO_PROCESS = "to_process"
NO_RESULTS = "no_results"
FAILED = "failed"

ENTITY_TERM_MAPPER = {
    EntityTypes.HOSTNAME: "domain",
    EntityTypes.PROCESS: "process",
    EntityTypes.URL: "url",
    EntityTypes.FILENAME: "path",
}
DEFAULT_THREAT_SCORE_THRESHOLD = 50
DEFAULT_MAX_RESULTS = 10
MAX_LIMIT_VALUE = 100
MIN_LIMIT_VALUE = 1
