from __future__ import annotations
INTEGRATION_NAME = "VMRay"
INTEGRATION_DISPLAY_NAME = "VMRay"

# Actions
PING_SCRIPT_NAME = f"{INTEGRATION_DISPLAY_NAME} - Ping"
ADD_TAG_TO_SUBMISSION_SCRIPT_NAME = (
    f"{INTEGRATION_DISPLAY_NAME} - Add Tag to Submission"
)
SCAN_HASH_SCRIPT_NAME = f"{INTEGRATION_DISPLAY_NAME} - Scan Hash"
SCAN_URL_SCRIPT_NAME = f"{INTEGRATION_DISPLAY_NAME} - Scan URL"
UPLOAD_FILE_SCRIPT_NAME = f"{INTEGRATION_DISPLAY_NAME} - Upload File"

API_ENDPOINTS = {
    "analysis_limit": "{0}/rest/analysis?_limit=1",
    "sample": "/rest/sample/",
    "submission": "/rest/submission/",
    "sample_md5": "/rest/sample/md5/",
    "sample_sha1": "/rest/sample/sha1/",
    "sample_sha256": "/rest/sample/sha256/",
    "sample_submit": "/rest/sample/submit",
    "sample_iocs": "{}/rest/sample/{}/iocs",
    "sample_thread_indicators": "{}/rest/sample/{}/threat_indicators",
    "analysis_archive_logs": "{}/rest/analysis/{}/archive/logs%2fsummary.json",
    "analysis_archive": "{}/rest/analysis/{}/archive",
    "analysis_sample": "{}/rest/analysis/sample/{}",
    "submission_add_tag": "{}/rest/submission/{}/tag/{}",
    "get_job": "{}/rest/job/{}",
}

MD5 = "md5"
SHA1 = "sha1"
SHA256 = "sha256"
SUSPICIOUS_STATUSES = ["malicious", "suspicious"]
ALREADY_EXIST_URL_ERROR = "not stored"
TIMEOUT_THRESHOLD = 0.9
DEFAULT_THREAT_INDICATOR_SCORE_THRESHOLD = 3
MAX_THREAT_INDICATOR_SCORE_THRESHOLD = 5
DEFAULT_LIMIT = 10
IOC_TYPE_DEFAULT_VALUES = ["ips", "files", "emails", "urls", "domains"]
IOC_TYPE_POSSIBLE_VALUES = [
    "ips",
    "files",
    "emails",
    "urls",
    "domains",
    "mutexes",
    "processes",
    "registry",
]
URL_IOC_TYPE_DEFAULT_VALUES = ["ips", "urls", "domains"]
URL_IOC_TYPE_POSSIBLE_VALUES = ["ips", "urls", "domains"]
IOC_VERDICT_DEFAULT_VALUES = ["Malicious", "Suspicious"]
IOC_VERDICT_INSIGHT_COLORS = {
    "malicious": "#ff0000",
    "suspicious": "#ff0000",
    "clean": "#339966",
    "none": "",
}
IOC_TYPE_MAPPING = {
    "domains": "domains",
    "emails": "emails",
    "files": "files",
    "ips": "ips",
    "mutexes": "mutexes",
    "processes": "processes",
    "registry": "registry",
    "urls": "urls",
}

IOC_VERDICT_MAPPING = {
    "malicious": "malicious",
    "suspicious": "suspicious",
    "clean": "clean",
    None: "none",
}

ENRICHMENT_PREFIX = "VMRay"
DEFAULT_SCORE: int = 0
