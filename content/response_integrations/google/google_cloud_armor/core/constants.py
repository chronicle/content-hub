from __future__ import annotations
API_URL = "https://compute.googleapis.com/compute/v1/"
SCOPES = ["https://www.googleapis.com/auth/compute"]
PROVIDER_NAME = "Google Cloud Armor"
INTEGRATION_NAME = "GoogleCloudArmor"

# ACTION NAMES
PING_SCRIPT_NAME = f"{INTEGRATION_NAME} - Ping"
CREATE_SECURITY_POLICY_SCRIPT_NAME = f"{INTEGRATION_NAME} - Create a Security Policy"
ADD_RULE_TO_SECURITY_POLICY_SCRIPT_NAME = (
    f"{INTEGRATION_NAME} - Add a Rule to a Security Policy"
)
UPDATE_SECURITY_POLICY_SCRIPT_NAME = f"{INTEGRATION_NAME} - Update a Security Policy"
SET_SECURITY_POLICY_SCRIPT_NAME = f"{INTEGRATION_NAME} - Set a Security Policy"

# EndPoints
ENDPOINTS = {
    "list_security_policies": (
        "projects/{project_id}/{environment}/securityPolicies?maxResults={limit}"
    ),
    "get_security_policy": (
        "projects/{project_id}/{environment}/securityPolicies/{security_policy}"
    ),
    "create_security_policy": (
        "projects/{project_id}/{environment}/securityPolicies?validateOnly=false"
    ),
    "add_rule_to_policy": (
        "projects/{project_id}/{environment}/securityPolicies/{security_policy}/addRule"
    ),
    "update_security_policy": (
        "projects/{project_id}/{environment}/securityPolicies/{security_policy}"
    ),
    "set_security_policy_to_service": (
        "projects/{project_id}/{environment}/backendServices/{service_name}/"
        "setSecurityPolicy"
    ),
    "set_security_policy_to_bucket": (
        "projects/{project_id}/{environment}/backendBuckets/{bucket_name}/"
        "setSecurityPolicy"
    ),
    "get_backend_service": (
        "projects/{project_id}/{environment}/backendServices/{service_name}"
    ),
    "get_backend_bucket": (
        "projects/{project_id}/{environment}/backendBuckets/{bucket_name}"
    ),
}

DEFAULT_ENVIRONMENT = "global"
DEFAULT_LIMIT_1 = "1"
TIME_INTERVAL = 10
DEFAULT_RETRIES = 10

SUCCESS_STATUSES = ["200"]
BAD_REQUEST = 400
NOT_FOUND_STATUS = 404
PERMISSION_DENIED_STATUS = 403
REGION_ERROR = "Unknown region"
BACKEND_SERVICE = "Backend Service"
BACKEND_BUCKET = "Backend Bucket"


# API Methods CONSTANTS
GET = "GET"
POST = "POST"
DELETE = "DELETE"
PUT = "PUT"
PATCH = "PATCH"
