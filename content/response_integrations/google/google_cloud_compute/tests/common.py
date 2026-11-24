from __future__ import annotations
from integration_testing.common import get_def_file_content
"""Shared test constants for GoogleCloudCompute action tests."""

import json
import pathlib

from TIPCommon.types import SingleJson

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

TEST_DIR: pathlib.Path = pathlib.Path(__file__).parent
MOCK_DATA_PATH: pathlib.Path = TEST_DIR / "mock_data.json"

MOCK_DATA: SingleJson = json.loads(MOCK_DATA_PATH.read_text(encoding="utf-8"))

# ---------------------------------------------------------------------------
# Integration config – dict form used with @set_metadata(integration_config=…)
# ---------------------------------------------------------------------------

CONFIG: SingleJson = {
    "API Root": "https://compute.googleapis.com",
    "OS Config API Root": "https://osconfig.googleapis.com",
    "Account Type": "service_account",
    "Project ID": "test-project",
    "Private Key ID": "",
    "Private Key": "",
    "Client Email": "",
    "Client ID": "",
    "Auth URI": "https://accounts.google.com/o/oauth2/auth",
    "Token URI": "https://oauth2.googleapis.com/token",
    "Auth Provider X509 URL": "https://www.googleapis.com/oauth2/v1/certs",
    "Client X509 URL": "",
    "Service Account Json File Content": "",
    "Workload Identity Email": "",
    "Verify SSL": True,
}

# ---------------------------------------------------------------------------
# Canonical resource paths used across multiple test files
# ---------------------------------------------------------------------------

PROJECT_ID: str = "test-project"
ZONE: str = "us-central1-a"
INSTANCE_ID: str = "test-instance-1"
INSTANCE_RESOURCE_PATH: str = (
    f"projects/{PROJECT_ID}/zones/{ZONE}/instances/{INSTANCE_ID}"
)
FIREWALL_RULE_NAME: str = "test-firewall-rule"
FIREWALL_RESOURCE_PATH: str = (
    f"projects/{PROJECT_ID}/global/firewalls/{FIREWALL_RULE_NAME}"
)
OPERATION_SELF_LINK: str = (
    f"https://www.googleapis.com/compute/v1/{PROJECT_ID}/zones/{ZONE}/operations/operation-1234"
)
PATCH_JOB_NAME: str = f"projects/{PROJECT_ID}/patchJobs/patch-job-uuid-1234"
PATCH_JOB_INSTANCE_FILTER: str = '{"all": true}'
PATCH_JOB_DURATION: int = 60  # minutes
PATCH_JOB_DISRUPTION_BUDGET: str = "10%"
PATCH_JOB_ROLLOUT_STRATEGY: str = "Zone By Zone"

# ---------------------------------------------------------------------------
# Execution deadline – must be far in the future so async actions' timeout
# guard does not trigger during unit tests (the default is epoch 0).
# ---------------------------------------------------------------------------

FAR_FUTURE_DEADLINE_MS: int = 9_999_999_999_999  # year ~2286
INTEGRATION_PATH: pathlib.Path = pathlib.Path(__file__).parent.parent
CONFIG_PATH: pathlib.Path = pathlib.Path(__file__).parent / 'config.json'
