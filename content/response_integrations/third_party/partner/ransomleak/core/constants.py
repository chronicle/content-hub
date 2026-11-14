# Copyright 2026 RansomLeak
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

"""Constants for the RansomLeak integration."""

from __future__ import annotations

INTEGRATION_NAME: str = "RansomLeak"
INTEGRATION_DISPLAY_NAME: str = "RansomLeak"
DEFAULT_API_ROOT: str = "https://app.ransomleak.com"

# Action script names
PING_SCRIPT_NAME: str = f"{INTEGRATION_NAME} - Ping"
ENRICH_USERS_SCRIPT_NAME: str = f"{INTEGRATION_NAME} - Enrich Users"
ASSIGN_TRAINING_SCRIPT_NAME: str = f"{INTEGRATION_NAME} - Assign Training"
GET_TRAINING_STATUS_SCRIPT_NAME: str = f"{INTEGRATION_NAME} - Get Training Status"
LIST_LEARNING_PATHS_SCRIPT_NAME: str = f"{INTEGRATION_NAME} - List Learning Paths"

# Partner API (all routes are relative to the API Root)
API_PREFIX: str = "/api/integration"
ENDPOINTS: dict[str, str] = {
    "health": f"{API_PREFIX}/health",
    "users": f"{API_PREFIX}/users",
    "user": f"{API_PREFIX}/users/{{user_id}}",
    "user_analytics": f"{API_PREFIX}/users/{{user_id}}/analytics",
    "user_risk": f"{API_PREFIX}/users/{{user_id}}/risk",
    "learning_paths": f"{API_PREFIX}/learning-paths",
    "learning_path_enrollments": f"{API_PREFIX}/learning-paths/{{learning_path_id}}/enrollments",
    "assignments": f"{API_PREFIX}/assignments",
    "assignment": f"{API_PREFIX}/assignments/{{assignment_id}}",
}

REQUEST_TIMEOUT_SECONDS: int = 30
MAX_ENROLLMENT_BATCH: int = 1000
MIN_DUE_DAYS: int = 1
MAX_DUE_DAYS: int = 365
DEFAULT_MAX_RESULTS: int = 50
RECENT_HISTORY_LIMIT: int = 5

ENRICHMENT_PREFIX: str = "RansomLeak_"
# Key in the RansomLeak partner-source registry; shown to learners as "Google SecOps".
ASSIGNMENT_SOURCE: str = "google_secops"

# (summary key, display label) for the fields shown in entity enrichment,
# the enrichment insight and the training status table.
SUMMARY_FIELDS: tuple[tuple[str, str], ...] = (
    ("risk_score", "Human Risk Score"),
    ("risk_level", "Risk Level"),
    ("exercises_completed", "Exercises Completed"),
    ("learning_time_minutes", "Learning Time (min)"),
    ("campaigns_completed", "Campaigns Completed"),
    ("campaigns_in_progress", "Campaigns In Progress"),
    ("campaigns_overdue", "Campaigns Overdue"),
    ("average_quiz_score", "Average Quiz Score"),
    ("last_completed_exercise", "Last Completed"),
    ("last_completed_at", "Last Completed At"),
)
# Max concurrent per-user lookups in Enrich Users / Get Training Status.
MAX_LOOKUP_WORKERS: int = 5
