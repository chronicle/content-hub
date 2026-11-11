from __future__ import annotations
SUCCESS_STATUSES = [200]
VULNERABILITY_CLASS = "VULNERABILITY"
DEFAULT_FALLBACK_SEVERITY = "MEDIUM"
CONNECTOR_SUB_NAME_FORMAT = "soar_connector_{identifier}_sub"
CONNECTOR_TOPIC_NAME_FORMAT = "soar_connector_{identifier}_topic"
CONNECTOR_NOTIFICATIONS_CONFIG_FORMAT = (
    "soar_connector_{identifier}_notifications_config"
)
CONNECTOR_TOXIC_NOTIFICATIONS_CONFIG_FORMAT = (
    "soar_connector_{identifier}_toxic_notifications_config"
)

JOB_SUB_NAME_FORMAT = "soar_job_{identifier}_sub"
JOB_TOPIC_NAME_FORMAT = "soar_job_{identifier}_topic"
JOB_NOTIFICATIONS_CONFIG_FORMAT = "soar_job_{identifier}_notifications_config"
JOB_QUERY_FILTER = (
    'external_systems.chronicle_soar.status="Opened" AND '
    'external_systems.chronicle_soar.caseUri:"{platform_uri}"'
)
JOB_ACK_DEADLINE = 600

MAX_ALERTS_TO_FETCH = 50
MAX_ALERTS_TO_PROCESS = 50
PUB_SUB_PULL_TIMEOUT = 45
DEFAULT_CLOUD_PROVIDER = "GCP"
STORED_IDS_LIMIT = 10_000
MINUTE_IN_MS = 60_000
URGENT_POSTURE_RULE_GENERATOR = "SCC: Urgent Posture Findings"
URGENT_POSTURE_DEFAULT_CASE_ID = "NO_CASE"
URGENT_POSTURE_DEFAULT_DEVICE_PRODUCT = "Google Security Command Center"
EXTERNAL_SYSTEMS_KEY = "chronicle_soar"
OPEN_CASES_KEY = "open_cases"

ENDPOINTS = {
    "ping": (
        "v2/organizations/{id}/sources/-/locations/{location_id}/findings?pageSize=1"
    ),
    "get_finding_details": (
        "v2/organizations/{id}/sources/-/locations/{location_id}/findings?pageSize=100"
        '&filter=name="{finding_name}"&orderBy=eventTime'
    ),
    "list_findings": "v2/organizations/{id}/sources/-/locations/{location_id}/findings",
    "list_sources": "v2/organizations/{id}/sources",
    "update_finding_external_systems": "v2/{external_system_name}",
    "create_notifications_config": (
        "v2/organizations/{id}/locations/{location_id}/notificationConfigs"
    ),
    "get_notifications_config": (
        "v2/organizations/{id}/locations/{location_id}/notificationConfigs/"
        "{notifications_config_id}"
    ),
    "patch_notifications_config": "v2/{notification_config_name}",
    # This request is used solely for cleanup purposes
    "delete_legacy_notifications_config": (
        "v1/organizations/{id}/notificationConfigs/{notifications_config_id}"
    ),
}

STATE_MAPPING = {"Active": "ACTIVE", "Inactive": "INACTIVE", "Select One": None}

SEVERITY_MAPPING = {
    "CRITICAL": 100,
    "HIGH": 80,
    "MEDIUM": 60,
    "LOW": 40,
    "SEVERITY_UNSPECIFIED": -1,
}

ALERT_SEVERITY_MAPPING = {
    "CRITICAL": "Critical",
    "HIGH": "High",
    "MEDIUM": "Medium",
    "LOW": "Low",
    "SEVERITY_UNSPECIFIED": "Informative",
}

FINDING_SEVERITY_FILTERS_MAPPING = {
    "low": "LOW",
    "medium": "MEDIUM",
    "high": "HIGH",
    "critical": "CRITICAL",
    "unspecified": "SEVERITY_UNSPECIFIED",
}

MUTED = "MUTED"

ALL_FINDING_CLOSED_COMMENT = (
    "All findings related to the case have been set as Inactive by Security "
    "Command Center."
)
CLOSED_FINDING_COMMENT = (
    "Finding with ID {id} was set to inactive by the Security Command Center. "
    "Resolved for asset: {resource_name}"
)
REOPENED_FINDING_COMMENT = (
    "Finding with ID {id} was reactivated by the Security Command Center. "
    "Affected asset: {resource_name}"
)
MUTED_FINDING_COMMENT = (
    "Finding with ID {id} was set to muted by the Security Command Center. "
    "Relevant asset: {resource_name}"
)
UNMUTED_FINDING_COMMENT = (
    "Finding with ID {id} was set to unmuted by the Security Command Center. "
    "Relevant asset: {resource_name}"
)
TC_COUNT_INCREASED_COMMENT = (
    "Toxic Combination count increased to {number}. Affected Finding: {id}."
)
TC_COUNT_DECREASED_COMMENT = (
    "Toxic Combination count decreased to {number}. Affected Finding: {id}."
)

SCOPES = ["https://www.googleapis.com/auth/cloud-platform"]
ORIGIN_HEADERS = {"SCC-Client-Context": "SOAR"}
API_ROOT_REGEX = (
    r"https://(staging-)?securitycenter(\.((\w|-)*)\.rep)?(\.sandbox)?"
    r"\.googleapis\.com"
)

POSSIBLE_SEVERITIES = ["LOW", "MEDIUM", "HIGH", "CRITICAL"]

# TODO: Check if regex applies to actual finding IDs and resource names
# language=regexp
CLOSED_FINDING_COMMENT_REGEX = (
    r"Finding with ID [\w\/]+ (?:was set to inactive|was reactivated) "
    r"by the Security Command Center\. (?:Resolved for|Affected) "
    r"asset: [\w\/.-]+$"
)

MAX_APS_SCORE_KEY = "MAX_APS_SCORE"
APS_SCORE_COMMENT = (
    "Security Command Center sent an update regarding Attack Exposure Score. "
    "The highest Attack Exposure Score among active findings is {max_aps_score}."
)
CAI_AWS_RESOURCE_TEMPLATE = (
    "//cloudasset.googleapis.com/organizations/{organization_id}/"
    "otherCloudConnections/aws/{resource_arn}"
)
CAI_AZURE_RESOURCE_TEMPLATE = (
    "//cloudasset.googleapis.com/organizations/{organization_id}/"
    "otherCloudConnections/azure/{resource_arn}"
)
LIST_FINDINGS_BATCH = 100

# language=regexp
GROUP_MEMBERSHIPS_KEY = r"groupMemberships_\d+_groupType"
TOXIC_COMBINATION_GROUP = "GROUP_TYPE_TOXIC_COMBINATION"

# Toxic combinations
TOXIC_COMBINATION_FILTER = (
    '((finding_class="TOXIC_COMBINATION" AND NOT mute="MUTED") OR '
    '(finding_class="VULNERABILITY" OR finding_class="MISCONFIGURATION" AND '
    'groupMemberships:"Toxic_Combination")) AND state="ACTIVE"'
)

TOXIC_COMBINATION_SOURCE_NAME = "Risk Engine"
TOXIC_COMBINATION_CONFIG_KEY = "toxic_notifications_config"
TOXIC_COMBINATION_CLASS = "TOXIC_COMBINATION"
TC_SOURCE_CONTEXT = "tc_source_name"
