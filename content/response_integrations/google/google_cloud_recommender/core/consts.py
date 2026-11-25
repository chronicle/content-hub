# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from __future__ import annotations
API_URL = "https://recommender.googleapis.com"
SCOPES = ["https://www.googleapis.com/auth/cloud-platform"]
PROVIDER_NAME = "Google Cloud Recommender"
INTEGRATION_NAME = "GoogleCloudRecommender"

# ACTION NAMES
PING_SCRIPT_NAME = f"{INTEGRATION_NAME} - Ping"
LIST_RECOMMENDATION_SCRIPT_NAME = f"{INTEGRATION_NAME} - List Recommendations"
GET_RECOMMENDATION_SCRIPT_NAME = f"{INTEGRATION_NAME} - Get Recommendation"
UPDATE_RECOMMENDATION_SCRIPT_NAME = f"{INTEGRATION_NAME} - Update Recommendation"
APPLY_IAM_RECOMMENDATIONS = f"{INTEGRATION_NAME} - Apply IAM Recommendations"

# EndPoints

RECOMMENDER_ENDPOINTS = {
    "list_recommendations": (
        "{resource_name}/locations/{locations}/"
        "recommenders/{recommenders}/recommendations?pageSize={limit}"
        "&filter={stateInfo}{priority}"
        "{subType}"
    ),
    "get_recommendation": "{recommendation_name}",
    "update_recommendation_status": ("{recommendation_name}:{state_change}"),
}

RESOURCE_MANAGER_ENDPOINTS = {
    "get_iam_policy": "{resource_name}:getIamPolicy",
    "set_iam_policy": "{resource_name}:setIamPolicy",
}

# EndPoints API
GET_RECOMMENDATION_API = "get_recommendation"

UPDATE_RECOMMENDATION_STATE = {
    "Not Specified": "Not Specified",
    "Claimed": "markClaimed",
    "Dismissed": "markDismissed",
}
UPDATE_RECOMMENDATION_RESULT = {
    "Not Specified": "Not Specified",
    "Failed": "markFailed",
    "Succeeded": "markSucceeded",
}

LOCATION = "global"
GOOGLE_SERVICE_RECOMMENDER_ACCOUNT_VALUE = "google.iam.policy.Recommender"

RECOMMENDATION_STATE_TYPE = ["Not Specified", "Active", "Dismissed"]
RECOMMENDER_SUBTYPE = ["Not Specified", "REMOVE_ROLE", "REPLACE_ROLE"]
INVALID_JSON_ERROR = "Invalid Json Error"
MAX_COUNT_OF_RECORDS = "50"
TABLE_NAME = "Available Recommendations"
DEFAULT_STATE = "Not Specified"
DEFAULT_RESULT = "Not Specified"
DEFAULT_PRIORITY = ""
DEFAULT_SUBTYPE = "Not Specified"
DEFAULT_LIMIT_1 = "1"

NUM_OF_MILLI_IN_SEC = 1000
MAX_WORKERS = 8

SERVICES = {"recommender": PROVIDER_NAME, "resource": "Google Cloud Resource Manager"}

SUCCESS_STATUSES = ["200"]
NOT_FOUND_STATUS = 404
PERMISSION_DENIED_STATUS = 403
RESOURCE_REGEX_PATTERN = r"(?:organizations|projects)/\w+"
