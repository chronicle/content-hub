from __future__ import annotations
INTEGRATION_NAME = "Google Cloud Compute"

API_URL = "https://compute.googleapis.com/"
OS_CONFIG_URL = "https://osconfig.googleapis.com"
SCOPES = [
    "https://www.googleapis.com/auth/compute",
    "https://www.googleapis.com/auth/cloud-platform",
]


DEFAULT_ORDER = "creationTimestamp desc"
DEFAULT_MAX_RESULT = 50
DEFAULT_PAGE_SIZE = 50
DEFAULT_MIN_RESULT = 0

ADD_IP_TO_FIREWALL_RULE = "Add IP To Firewall Rule"
ADD_LABELS_TO_INSTANCE_SCRIPT_NAME = "Add Labels To Instance"
ADD_NETWORK_TAGS_SCRIPT_NAME = "Add Network Tags"
EXECUTE_VM_PATCH_JOB_SCRIPT_NAME = "Execute VM Patch Job"
GET_INSTANCE_IAM_POLICY_SCRIPT_NAME = "Get Instance IAM Policy"
LIST_INSTANCES_TABLE_NAME = "Google Cloud Compute Instances"
REMOVE_IP_FROM_FIREWALL_RULE = "Remove IP From Firewall Rule"
REMOVE_NETWORK_TAGS_SCRIPT_NAME = "Remove Network Tags"
SET_INSTANCE_IAM_POLICY_SCRIPT_NAME = "Set Instance IAM Policy"
UNASSIGN_EXTERNAL_IP_SCRIPT_NAME = "Remove External IP Addresses"
UPDATE_FIREWALL_RULE_SCRIPT_NAME = "Update Firewall Rule"

ENRICHMENT_CSV_TABLE_NAME = "{} Enrichment Table"

INVALID_ZONE_ERROR = "Unknown zone"
INVALID_LABELS_ERROR = "Invalid value for field 'labels'"
PROJECT_NOT_FOUND_ERROR = r"The resource 'projects/(\w|-)+' was not found"
NOT_FOUND_RESOURCE_ERROR = ["The resource", "was not found"]

COLON = ":"

# Instance Status:
RUNNING_STATUS = "RUNNING"

ENRICHMENT_PREFIX = "Google_Compute"

INSTANCE_RESOURCE_NAME = "projects/{project_id}/zones/{zone}/instances/{resource_id}"
INSTANCE_RESOURCE_NAME_PATTERN = (
    r"projects\/(\w|-)+\/zones\/(\w|-)+\/instances\/(\w|-)+"
)
FIREWALL_RESOURCE_NAME = "projects/{project_id}/global/firewalls/{firewall}"
FIREWALL_RESOURCE_NAME_PATTERN = r"projects\/(\w|-)+\/global\/firewalls\/(\w|-)+"
WILDCARD = "*"
IPV4_ONLY = "IPV4_ONLY"
GLOBAL_TIMEOUT_THRESHOLD_IN_MIN = 1
OPERATION_RUNNING_STATUSES = ["RUNNING", "PENDING"]
