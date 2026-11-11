from __future__ import annotations
from enum import Enum, auto

ANALYZE_URL = "https://analyze.intezer.com"
BASE_URL = f"{ANALYZE_URL}/api/"
API_VERSION = "v2-0"
API_URL = f"{BASE_URL}{API_VERSION}"
INTEGRATION_NAME = "Intezer"
INTEGRATION_DISPLAY_NAME = "Intezer"

# ACTION NAMES
PING_SCRIPT_NAME = f"{INTEGRATION_NAME} - Ping"
DETONATE_URL_SCRIPT_NAME = f"{INTEGRATION_NAME} - Detonate URL"
DETONATE_HASH_SCRIPT_NAME = f"{INTEGRATION_NAME} - Detonate Hash"
DETONATE_FILE_SCRIPT_NAME = f"{INTEGRATION_NAME} - Detonate File"
INDEX_FILE_SCRIPT_NAME = f"{INTEGRATION_NAME} - Index File"
UNSET_INDEX_FILE_SCRIPT_NAME = f"{INTEGRATION_NAME} - Unset Index File"
GET_ALERT_SCRIPT_NAME = f"{INTEGRATION_NAME} - Get Alert"
SUBMIT_ALERT_SCRIPT_NAME = f"{INTEGRATION_NAME} - Submit Alert"
GET_URL_REPORT_SCRIPT_NAME = f"{INTEGRATION_NAME} - Get URL Report"
GET_FILE_REPORT_SCRIPT_NAME = f"{INTEGRATION_NAME} - Get File Report"
SUBMIT_SUSPICIOUS_EMAIL = f"{INTEGRATION_DISPLAY_NAME} - Submit Suspicious Email"

# EndPoints
ENDPOINTS = {
    "get_access_token": "get-access-token",
    "test_connectivity": "is-available",
    "detonate_url": "url",
    "detonate_hash": "analyze-by-hash",
    "detonate_file": "analyze",
    "index_file_by_id": "files/index/{index_id}",
    "index_file_by_hash": "files/{sha256}/index",
    "unset_index_file_by_hash": "files/{sha256}/index",
    "get_alert": "alerts/get-by-id",
    "submit_alert": "alerts/ingest",
    "get_url_report": "url/{analysis_id}",
    "submit_email": "alerts/ingest/binary",
    "get_file_report_analysis_id": "analyses/{analysis_id}",
    "get_file_report_file_hash": "files/{hash_value}",
    "get_iocs": "analyses/{analysis_id}/iocs",
    "get_dynamic_ttps": "analyses/{analysis_id}/dynamic-ttps",
    "get_sub_analyses_ids": "analyses/{analysis_id}/sub-analyses",
    "get_code_reuse": (
        "analyses/{analysis_id}/sub-analyses/{sub_analysis_id}/code-reuse"
    ),
    "get_file_metadata": (
        "analyses/{analysis_id}/sub-analyses/{sub_analysis_id}/metadata"
    ),
}

# EndPoints Constant
GET_ACCESS_TOKEN = "get_access_token"
TEST_CONNECTIVITY = "test_connectivity"
DETONATE_URL = "detonate_url"
DETONATE_HASH = "detonate_hash"
DETONATE_FILE = "detonate_file"
GET_URL_REPORT = "get_url_report"
INDEX_FILE_BY_ID = "index_file_by_id"
INDEX_FILE_BY_HASH = "index_file_by_hash"
UNSET_INDEX_FILE_BY_HASH = "unset_index_file_by_hash"
GET_ALERT = "get_alert"
SUBMIT_ALERT = "submit_alert"
SUBMIT_EMAIL = "submit_email"
GET_FILE_REPORT_BY_ANALYSIS_ID = "get_file_report_analysis_id"
GET_FILE_REPORT_BY_FILE_HASH = "get_file_report_file_hash"
GET_IOCS = "get_iocs"
GET_DYNAMIC_TTPS = "get_dynamic_ttps"
GET_SUB_ANALYSES_IDS = "get_sub_analyses_ids"
GET_CODE_REUSE = "get_code_reuse"
GET_FILE_METADATA = "get_file_metadata"


REQUESTER = "chronicle_soar"

API_LIMIT_ERROR = 429
API_BAD_REQUEST = 400
API_NOT_FOUND = 404
API_USER_INPUT_ERROR = range(400, 500)

FILE_HASH = "FILEHASH"
URL = "URL"
DESTINATION_URL = "DestinationURL"

INDEX_AS_TYPE = ["trusted", "malicious"]

MD5_LENGTH = 32
SHA1_LENGTH = 40
SHA256_LENGTH = 64

CREATED_STATUS = "created"
SUCCESS_STATUS = "succeeded"
IN_PROGRESS_STATUS = "in_progress"
QUEUED_STATUS = "queued"
PENDING_ITEM_STATUS = "pending_item"
FAILED_STATUS = "failed"
EXPIRED_STATUS = "expired"

ZERO = 0

FAILED_STATUS_CODE = (400, 403, 404)
SUCCESS_STATUS_CODE = (200, 201)
SOURCE_MAX_LENGTH = 20

STATUS_MAP = {
    "in_progress": "in_progress",
    "queued": "queued",
    "failed": "failed",
    "succeeded": "succeeded",
}
STATUS_MAP_GET = {
    "in_progress": "pending_item",
    "queued": "pending_item",
    "failed": "failed",
    "succeeded": "succeeded",
}

GLOBAL_TIMEOUT_THRESHOLD_IN_MIN = 1
DEFAULT_TIMEOUT = 300


class AutoName(Enum):
    @staticmethod
    def _generate_next_value_(name, start, count, last_values):
        return name.lower()


class IndexType(AutoName):
    TRUSTED = auto()
    MALICIOUS = auto()

    @staticmethod
    def from_str(label: str):
        """Get the string value

        Args:
            label: Index as value for indexing
        """
        if label in ("TRUSTED", "trusted"):
            return IndexType.TRUSTED

        if label in ("MALICIOUS", "malicious"):
            return IndexType.MALICIOUS

        raise NotImplementedError


class IndexStatusCode(Enum):
    CREATED = "created"
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    SUCCESS = "succeeded"
    QUEUED = "queued"
    FAILED = "failed"


class FileAnalysisType(Enum):
    ANALYSIS_ID = "analysis id"
    FILE_HASH = "file hash"


class FileAnalysisInput(Enum):
    ANALYSIS_ID = "analysis_id"
    FILE_HASH = "file_hash"
    PRIVATE_ONLY = "private_only"


class FileAnalysisStatus(Enum):
    STATUS = "status"
    PENDING = "pending"
    SUCCESS = "succeeded"
    IN_PROGRESS = "in_progress"
    QUEUED = "queued"
    FAILED = "failed"
    EXPIRED = "expired"


class UrlAnalysisStatus(Enum):
    STATUS = "status"
    PENDING = "pending"
    SUCCESS = "succeeded"
    IN_PROGRESS = "in_progress"
    QUEUED = "queued"
    FAILED = "failed"
    EXPIRED = "expired"
