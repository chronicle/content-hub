"""Core constants that can be used across multiple apps/components."""

# Copyright 2025 Google LLC
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

# ------------------ Common ------------------

REPO_NAME: str = "marketplace"

CONTENT_DIR_NAME: str = "content"
COMMERCIAL_REPO_NAME: str = "google"
CUSTOM_REPO_NAME: str = "custom"
THIRD_PARTY_REPO_NAME: str = "third_party"
COMMUNITY_DIR_NAME: str = "community"
PARTNER_DIR_NAME: str = "partner"
DOWNLOAD_DIR: str = "downloads"

OUT_DIR_NAME: str = "out"

JSON_SUFFIX: str = ".json"
YAML_SUFFIX: str = ".yaml"
HTML_SUFFIX: str = "html"


WINDOWS_PLATFORM: str = "win32"

RECONFIGURE_MP_MSG: str = (
    "Please ensure the content-hub path is properly configured.\n"
    "You can verify your configuration by running [bold]mp config "
    "--display-config[/bold].\n"
    "If the path is incorrect, re-configure it by running [bold]mp config "
    "--root-path <your_path>[/bold]."
)

# ------------------ Integrations ------------------

INTEGRATIONS_DIR_NAME: str = "response_integrations"
POWERUPS_DIR_NAME: str = "power_ups"
INTEGRATIONS_DIRS_NAMES_DICT: dict[str, tuple[str, ...]] = {
    THIRD_PARTY_REPO_NAME: (
        COMMUNITY_DIR_NAME,
        PARTNER_DIR_NAME,
        POWERUPS_DIR_NAME,
    ),
    COMMERCIAL_REPO_NAME: (COMMERCIAL_REPO_NAME,),
}

INTEGRATIONS_TYPES: tuple[str, ...] = (
    COMMERCIAL_REPO_NAME,
    THIRD_PARTY_REPO_NAME,
    COMMUNITY_DIR_NAME,
    PARTNER_DIR_NAME,
    POWERUPS_DIR_NAME,
    CUSTOM_REPO_NAME,
)
OUT_INTEGRATIONS_DIR_NAME: str = "response_integrations"

PROJECT_FILE: str = "pyproject.toml"
REQUIREMENTS_FILE: str = "requirements.txt"
INTEGRATION_DEF_FILE: str = "Integration-{0}.def"
INTEGRATION_FULL_DETAILS_FILE: str = "{0}.fulldetails"
RN_JSON_FILE: str = "RN.json"
OUT_DEPENDENCIES_DIR: str = "Dependencies"
INTEGRATION_VENV: str = ".venv"
MARKETPLACE_JSON_NAME: str = "marketplace.json"

OUT_ACTIONS_META_DIR: str = "ActionsDefinitions"
OUT_CONNECTORS_META_DIR: str = "Connectors"
OUT_JOBS_META_DIR: str = "Jobs"
OUT_WIDGETS_META_DIR: str = "Widgets"

AI_DIR: str = "ai"
ACTIONS_AI_DESCRIPTION_FILE: str = "actions_ai_description.yaml"

ACTIONS_META_SUFFIX: str = ".actiondef"
CONNECTORS_META_SUFFIX: str = ".connectordef"
JOBS_META_SUFFIX: str = ".jobdef"
IMAGE_FILE_SUFFIX: str = ".png"
SVG_FILE_SUFFIX: str = ".svg"

OUT_ACTION_SCRIPTS_DIR: str = "ActionsScripts"
OUT_CONNECTOR_SCRIPTS_DIR: str = "ConnectorsScripts"
OUT_JOB_SCRIPTS_DIR: str = "JobsScrips"
OUT_WIDGET_SCRIPTS_DIR: str = "WidgetsScripts"
OUT_MANAGERS_SCRIPTS_DIR: str = "Managers"
OUT_CUSTOM_FAMILIES_DIR: str = "DefaultCustomFamilies"
OUT_CUSTOM_FAMILIES_FILE: str = "integration_families.json"
OUT_MAPPING_RULES_DIR: str = "DefaultMappingRules"
OUT_MAPPING_RULES_FILE: str = "integration_mapping_rules.json"

CUSTOM_FAMILIES_FILE: str = f"integration_families{YAML_SUFFIX}"
MAPPING_RULES_FILE: str = f"ontology_mapping{YAML_SUFFIX}"
ACTIONS_DIR: str = "actions"
CONNECTORS_DIR: str = "connectors"
JOBS_DIR: str = "jobs"
WIDGETS_DIR: str = "widgets"
TESTS_DIR: str = "tests"
TESTING_DIR: str = "Testing"
CORE_SCRIPTS_DIR: str = "core"
RESOURCES_DIR: str = "resources"
PACKAGE_FILE: str = "__init__.py"
COMMON_SCRIPTS_DIR: str = "group_modules"
DEFINITION_FILE: str = f"definition{YAML_SUFFIX}"
RELEASE_NOTES_FILE: str = f"release_notes{YAML_SUFFIX}"
IMAGE_FILE: str = f"image{IMAGE_FILE_SUFFIX}"
LOGO_FILE: str = f"logo{SVG_FILE_SUFFIX}"
SDK_PACKAGE_NAME: str = "soar_sdk"

SAFE_TO_IGNORE_PACKAGES: tuple[str, ...] = ("win-unicode-console",)
SAFE_TO_IGNORE_ERROR_MESSAGES: tuple[str, ...] = (
    "Could not find a version that satisfies the requirement",
    "No matching distribution found",
)
REPO_PACKAGES_CONFIG: dict[str, str] = {
    "TIPCommon": "tipcommon",
    "EnvironmentCommon": "envcommon",
    "integration_testing": "integration_testing_whls",
}
SDK_MODULES_CONFIG: dict[str, str] = {
    "dateutil": "python-dateutil",
    "OpenSSL": "pyopenssl",
}

README_FILE: str = "README.md"
LOCK_FILE: str = "uv.lock"
PYTHON_VERSION_FILE: str = ".python-version"

MS_IN_SEC: int = 1_000

SDK_MODULES: frozenset[str] = frozenset({
    "SiemplifyVaultCyberArkPam",
    "CaseAlertsProvider",
    "FileRetentionManager",
    "GcpTokenProvider",
    "MockConnector",
    "MockRunner",
    "OtelLoggingUtils",
    "OverflowManager",
    "PersistentFileStorageMixin",
    "ScriptResult",
    "Siemplify",
    "SiemplifyAction",
    "SiemplifyAddressProvider",
    "SiemplifyBase",
    "SiemplifyCaseWallDataModel",
    "SiemplifyConnectors",
    "SiemplifyConnectorsDataModel",
    "SiemplifyConstants",
    "SiemplifyDataModel",
    "SiemplifyExtensionTypesBase",
    "SiemplifyJob",
    "SiemplifyLogger",
    "SiemplifyLogicalOperator",
    "SiemplifyPublisherUtils",
    "SiemplifySdkConfig",
    "SiemplifyTransformer",
    "SiemplifyUtils",
    "SiemplifyVault",
    "SiemplifyVaultUtils",
    "SimulatedCasesCreator",
    "VaultProviderFactory",
})

EXCLUDED_GLOBS: set[str] = {
    "*.pyc",
    "__pycache__",
    ".ruff_cache",
    ".pytest_cache",
    "CACHEDIR.TAG",
}
EXCLUDED_INTEGRATIONS_IDS_WITHOUT_PING: set[str] = {
    "chronicle_support_tools",
    "connectors",
    "lacework",
}

VALID_SSL_PARAM_NAMES: set[str] = {
    "Verify SSL",
    "Verify SSL Certificate",
    "SSL Verification",
    "Verify SSL ",
    "Git Verify SSL",
    "Siemplify Verify SSL",
}
LONG_DESCRIPTION_MAX_LENGTH: int = 2050
SHORT_DESCRIPTION_MAX_LENGTH: int = 2050
DISPLAY_NAME_MAX_LENGTH: int = 150
MAX_PARAMETERS_LENGTH: int = 50
PARAM_NAME_MAX_LENGTH: int = 150
PARAM_NAME_MAX_WORDS: int = 13
MINIMUM_SCRIPT_VERSION: float = 1.0
MAX_SCRIPT_RESULT_NAME_LENGTH: int = 100

# ------------------ Playbooks ------------------

PLAYBOOKS_DIR_NAME: str = "playbooks"
PLAYBOOK_BASE_OUT_DIR_NAME: str = "Playbooks"

PLAYBOOK_REPOSITORY_TYPE: tuple[str, ...] = (COMMERCIAL_REPO_NAME, THIRD_PARTY_REPO_NAME)

PLAYBOOKS_DIRS_NAMES_DICT: dict[str, tuple[str, ...]] = {
    COMMERCIAL_REPO_NAME: (COMMERCIAL_REPO_NAME,),
    THIRD_PARTY_REPO_NAME: (COMMUNITY_DIR_NAME, PARTNER_DIR_NAME),
}

PLAYBOOK_OUT_DIR_NAME: str = "playbook_definitions"

TRIGGERS_FILE_NAME: str = f"triggers{YAML_SUFFIX}"
DISPLAY_INFO_FILE_NAME: str = f"display_info{YAML_SUFFIX}"
OVERVIEWS_FILE_NAME: str = "overviews.yaml"
STEPS_DIR: str = "steps"
TRIGGER_FILE_NAME: str = f"trigger{YAML_SUFFIX}"
PLAYBOOKS_JSON_NAME: str = "playbooks.json"

MAX_STEP_PARALLEL_ACTIONS: int = 5
NAME_VALIDATION_REGEX: str = r"^[^!@#$%^&*()+=\[\]{};'\\\":~`|,.<>/?]*$"
ALL_ENV: str = "*"
DEFAULT_ENV: str = "Default Environment"
VALID_ENVIRONMENTS: set[str] = {ALL_ENV, DEFAULT_ENV}

PLAYBOOK_MUST_HAVE_KEYS: set[str] = {
    "CategoryName",
    "OverviewTemplatesDetails",
    "WidgetTemplates",
    "Definition",
}
