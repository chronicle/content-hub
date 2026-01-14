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
}
EXCLUDED_INTEGRATIONS_WITH_CONNECTORS_AND_NO_MAPPING: set[str] = {
    "air_table",
    "be_secure",
    "connectors",
    "cybersixgill_actionable_alerts",
    "cybersixgill_darkfeed",
    "cybersixgill_dve_feed",
    "data_dog",
    "duo",
    "eclectic_iq",
    "flashpoint",
    "grey_noise",
    "lacework",
    "logzio",
    "luminar_iocs_and_leaked_credentials",
    "microsoft_graph_security_tools",
    "pager_duty",
    "perimeter_x",
    "telegram",
    "vectra_qux",
    "vectra_rux",
    "vorlon",
    "workflow_tools",
}
EXCLUDED_INTEGRATIONS_IDS_WITHOUT_PING: set[str] = {
    "chronicle_support_tools",
    "connectors",
    "lacework",
}

EXCLUDED_INTEGRATIONS_WITHOUT_DOCUMENTATION_LINK: set[str] = {
    "full_contact",
    "workflow_tools",
    "docker_hub",
    "hibob",
    "google_drive",
    "vorlon",
    "aws_ec2",
    "google_sheets",
    "stairwell",
    "microsoft_graph_security_tools",
    "ipqs_fraud_and_risk_scoring",
    "telegram",
    "tools",
    "lacework",
    "spell_checker",
    "data_dog",
    "superna_zero_trust",
    "insights",
    "cybersixgill_darkfeed",
    "anyrun_ti_lookup",
    "bitdefender_gravity_zone",
    "arcanna_ai",
    "file_utilities",
    "cybersixgill_dve_feed",
    "anyrun_ti_feeds",
    "cybersixgill_dve_enrichment",
    "pager_duty",
    "houdin_io",
    "grey_noise",
    "cybersixgill_darkfeed_enrichment",
    "luminar_iocs_and_leaked_credentials",
    "cylusone",
    "google_safe_browsing",
    "imgbb",
    "netenrich_connect",
    "eclectic_iq",
    "nucleon_cyber",
    "cybersixgill_actionable_alerts",
    "chronicle_support_tools",
    "whois_xml_api",
    "azure_devops",
    "doppel_vision",
    "phish_tank",
    "perimeter_x",
    "philips_hue",
    "functions",
    "abuse_ipdb",
    "clarotyxdome",
    "torq",
    "group_ib_ti",
    "pulsedive",
    "git_sync",
    "lists",
    "zoom",
    "flashpoint",
    "google_docs",
    "be_secure",
    "jamf",
    "asana",
    "air_table",
    "country_flags",
    "duo",
    "thinkst_canary",
    "bandura_cyber",
    "webhook",
    "vanilla_forums",
    "anyrun_sandbox",
    "template_engine",
    "send_grid",
    "connectors",
    "marketo",
    "enrichment",
    "email_utilities",
}
EXCLUDED_CONNECTOR_NAMES_WITHOUT_DOCUMENTATION_LINK: set[str] = {
    "Vectra RUX - Entities Connector",
    "Lacework Connector",
    "Cybersixgill - DVE Connector",
    "EclecticIQ - Feed Connector",
    "Thinkst - Alert Connector",
    "Cybersixgill - Darkfeed Connector",
    "Pull reports",
    "Cybersixgill Actionable Alerts",
    "LOGZIO fetch-security-events",
    "Sheet Connector",
    "Generate Alert from GreyNoise GNQL",
    "DUO - Trust Monitor Connector",
    "Slack Connector For Code Defender",
    "Luminar IOCs and Leaked Credentials  Connector",
    "TI IoC Hash Connector",
    "TI IoC IP Connector",
    "Telegram Connector",
    "Infoblox - DNS Security Events Connector",
    "Infoblox - SOC Insights Connector",
    "DataDog Connector",
    "PagerDutyConnector",
    "AirTable Connector",
    "Flashpoint - Compromised Credential Connector",
    "Sample Integration - Simple Connector Example",
    "MS365 MFA Alert",
    "MS SecureScore Alert",
    "Vorlon Connector",
    "Vectra QUX - Entities Connector",
    "Cron Scheduled Connector",
    "Scheduled Connector",
}
EXCLUDED_NAMES_WITHOUT_VERIFY_SSL: set[str] = {
    "Docker Hub",
    "Darktrace",
    "Lacework Connector",
    "PagerDuty",
    "PagerDutyConnector",
    "Google Drive",
    "Hibob",
    "AWS - EC2",
    "Google Docs",
    "Google Safe Browsing",
    "Webhook",
    "AirTable",
    "AirTable Connector",
    "Telegram",
    "Telegram Connector",
    "Zoom",
    "SendGrid",
    "IPQS Fraud and Risk Scoring",
    "DUO",
    "DUO - Trust Monitor Connector",
    "PhilipsHUE",
    "Vectra RUX",
    "Vectra RUX - Entities Connector",
    "Azure DevOps",
    "Asana",
    "Full Contact",
    "Functions",
    "Lists",
    "CountryFlags",
    "TemplateEngine",
    "ChronicleSupportTools",
    "Tools",
    "Spell Checker",
    "Lacework",
    "Insights",
    "Connectors",
    "EmailUtilities",
    "DataDog",
    "DataDog Connector",
    "Logzio",
    "LOGZIO fetch-security-events",
    "VanillaForums",
    "MicrosoftGraphSecurityTools",
    "MS365 MFA Alert",
    "MS SecureScore Alert",
    "PhishTank",
    "WHOIS XML API",
    "Marketo",
    "Vorlon",
    "Vorlon Connector",
    "Flashpoint",
    "Flashpoint - Compromised Credential Connector",
    "Google Sheets",
    "Sheet Connector",
    "PerimeterX",
    "Slack Connector For Code Defender",
    "Cybersixgill Actionable Alerts",
    "Cybersixgill Darkfeed",
    "Cybersixgill - Darkfeed Connector",
    "Cybersixgill Darkfeed Enrichment",
    "Cybersixgill DVE Enrichment",
    "Cybersixgill DVE Feed",
    "Cybersixgill - DVE Connector",
    "Cron Scheduled Connector",
    "Scheduled Connector",
    "Luminar IOCs and Leaked Credentials",
    "XMCyber",
    "NucleonCyber",
    "DoppelVision",
    "GreyNoise",
    "Generate Alert from GreyNoise GNQL",
    "beSECURE",
    "Pull reports",
    "Image Utilities",
}
EXCLUDED_NAMES_WHERE_SSL_DEFAULT_IS_NOT_TRUE: set[str] = {
    "Bitdefender GravityZone",
    "FileUtilities",
    "Enrichment",
    "TeamCymruScout",
    "Workflow Tools",
    "ArcannaAI",
    "Luminar IOCs and Leaked Credentials  Connector",
    "Recorded Future - Playbook Alerts Connector",
    "Recorded Future - Playbook Alerts Tracking Connector",
    "Recorded Future - Classic Alerts Connector",
    "SupernaZeroTrust",
}
VALID_SSL_PARAM_NAMES: set[str] = {
    "Verify SSL",
    "Verify SSL Certificate",
    "SSL Verification",
    "Verify SSL ",
    "Git Verify SSL",
    "Siemplify Verify SSL",
}
EXCLUDED_PARAM_NAMES_WITH_TOO_MANY_WORDS: set[str] = {
    "Country(For multiple countries, provide comma-separated values)",
    "Filter - Depth - All Items Recursively",
    "Save JSON as Case Wall File",
    "Use Alert ID as ID in Arcanna",
    "Use case ID as ID in Arcanna",
    "Use document ID as ID in Arcanna",
}
EXCLUDED_LONG_PARAM_DESCRIPTION_PREFIXES: set[str] = {
    "\t\n\nIf provided, the connector will use this value for Siemplify Rule Generator. Please re",
    "A comma separated list CSV encoding types used for decoding your CSV files, e.g. utf-8, lati",
    "A comma-separated string of email headers to add to Google SecOps events, such as “DKIM-Siga",
    "A custom alert name. You can provide placeholders in the following format: [name of the fiel",
    "A custom case name. When you configure this parameter, the connector adds a new key called c",
    "A custom rule generator.\nYou can use placeholders in the format [field_name], for example: ",
    "A custom rule generator. You can provide placeholders in the following format: [name of the ",
    "A filter condition that specifies the email labels to search for. This parameter accepts mul",
    "A regular expression pattern to run on the value found in the Environment Field Name field. ",
    'A regular expression pattern to run on the value found in the "Environment Field Name" field',
    "By default, the search will be executed in the default mailbox specified in the integration ",
    "Client email of your service account. You can configure either this parameter or the User Se",
    "Comma separated. e.g. customer.combo_name,category.sym,status.sym,priority.sym,active,log_ag",
    "End date of the search. Search will return only records equal or before this point in time.",
    "Grouping mechanism that will be used to create Siemplify Alerts. Possible values: Host, ",
    "If defined - connector will extract the environment from the specified event field. You can ",
    "If provided, connector will use this value for Alert Name. Please refer to the documentation",
    "If provided, connector will use this value for Siemplify Alert Name. Please refer to the doc",
    "If provided, connector will use this value for Google Secops Alert Name. Please refer to the",
    "If provided, the connector uses this value for Chronicle SOAR",
    "If specified, connector will use this value from the Microsoft Azure Sentinel API response f",
    "Number of days before the first connector iteration to retrieve vulnerabilities from. This p",
    "Optional. Specify custom query parameter you want to add to the list users search call. For ",
    "Provide a delimiter character, with which the action will split the input it gets into a num",
    "Search field for free text queries (When query doesn't specify a field name).",
    "Search pattern for a elastic index.\r\nIn elastic, index is like a DatabaseName, and data is",
    "Specify a comma separated list of alert attributes that should be used as a fallback for the",
    "Specify a comma separated list of incident or alert attributes that should be used as a fall",
    "Specify a comma-separated list of engines that should be used to retrieve information, wheth",
    "Specify a comma-separated list of fields to return. Example of values:assetType,project,fold",
    "Specify a comma-separated list of the event types that need to be returned. If nothing is pr",
    "Specify a limit for how many events for a single offense connector should query from Qradar ",
    'Specify a time frame for the results. If "Alert Time Till Now" is selected, action will use ',
    'Specify a time frame for the results. If "Custom" is selected, you also need to provide "Sta',
    "Specify a time frame for the results. If “Alert Time Till Now” is selected, action will use ",
    "Specify the amount of time in minutes to pass before the connector will try to fetch events ",
    "Specify the filter to fetch the recommendations for. Parameter expects a string of a format ",
    "Specify the query that needs to be executed. Note: the query should follow a strict pattern ",
    "Specify the query that needs to be executed. Note: this query should follow a strict pattern",
    "Specify the time frame for the search. Only hours and days are supported. Note: end time wil",
    'Specify the wait mode for the action. If "Until Timeout" is selected, action will wait until',
    "Specify what attributes need to be used, when the action is to search for similar alerts. If",
    'Specify what selection should be used for users. If "From Entities & User Identifiers" is se',
    "Start date of the search. Search will return only records equal or after this point in time.",
    "The client email address of your workload identity. You can configure either this parameter ",
    "The conditions that are required for the custom fields for the action to resume running a pl",
    "The content of the service account key JSON file. You can configure either this parameter or",
    "The number of days for the action to wait before refreshing the entity summary. The action g",
    'The search query to perform. It is in Lucene syntax.\r\nIE1: "*" (this is a wildcard that wi',
    'When provided, connector will add a new key called "custom_case_name" to the',
}
LONG_DESCRIPTION_MAX_LENGTH: int = 2_200
SHORT_DESCRIPTION_MAX_LENGTH: int = 2050
DISPLAY_NAME_MAX_LENGTH: int = 150
MAX_PARAMETERS_LENGTH: int = 50
PARAM_NAME_MAX_LENGTH: int = 150
PARAM_NAME_MAX_WORDS: int = 13
MINIMUM_SCRIPT_VERSION: float = 1.0
# language=regexp
SCRIPT_DISPLAY_NAME_REGEX: str = (
    r"^[a-zA-Z0-9-\s]+$"
    # Excluded scripts that already have issues with their name
    r"|^IOC_Enrichment$"
    r"|^Symantec Email Security\.Cloud - Block Entities$"
    r"|^Symantec Email Security\.Cloud$"
    r"|^Azure Active Directory - List User's Groups Membership$"
    r"|^List User's Groups Membership$"
    r"|^Cisco AMP - Get Computers By Network Activity \(URL\)$"
    r"|^Get Computers By Network Activity \(URL\)$"
    r"|^Cisco AMP - Get Computers By Network Activity \(Ip\)$"
    r"|^Get Computers By Network Activity \(Ip\)$"
    r"|^Stealthwatch V6\.10$"
    r"|^Pub/Sub$"
    r"|^Google Rapid Response \(GRR\)$"
    r"|^Google Rapid Response \(GRR\) - Stop a Hunt$"
    r"|^Google Rapid Response \(GRR\) - Get Hunt Details$"
    r"|^Google Rapid Response \(GRR\) - Get Client Details$"
    r"|^Google Rapid Response \(GRR\) - Start a Hunt$"
    r"|^Google Rapid Response \(GRR\) - List Launched Flows$"
    r"|^Google Rapid Response \(GRR\) - List Clients$"
    r"|^Google Rapid Response \(GRR\) - List Hunts$"
    r"|^Tenable\.io - List Endpoint Vulnerabilities$"
    r"|^Tenable\.io - Enrich Entities$"
    r"|^Tenable\.io - List Plugin Families$"
    r"|^Tenable\.io - List Policies$"
    r"|^Tenable\.io - Get Vulnerability Details$"
    r"|^Tenable\.io - Scan Endpoints$"
    r"|^Tenable\.io - List Scanners$"
    r"|^Tenable\.io$"
    r"|^Google Cloud Storage - Get a Bucket’s Access Control List$"  # noqa: RUF001
    r"|^Get a Bucket’s Access Control List$"  # noqa: RUF001
    r"|^MITRE ATT\&CK™ - Get Mitigations$"
    r"|^MITRE ATT\&CK™ - Get Associated Intrusions$"
    r"|^MITRE ATT\&CK™ - Get Technique Details$"
    r"|^MITRE ATT\&CK™$"
)
# language=regexp
SCRIPT_IDENTIFIER_REGEX: str = (
    r"^[a-zA-Z0-9-_]+$"
    # Excluded integrations that already have blank spaces in their identifier
    r"|^Bitdefender GravityZone$"
    r"|^Cybersixgill Actionable Alerts$"
    r"|^Full Contact$"
    r"|^IPQS Fraud and Risk Scoring$"
    r"|^Cybersixgill DVE Feed$"
    r"|^Google Safe Browsing$"
    r"|^WHOIS XML API$"
    r"|^Google Docs$"
    r"|^AWS - EC2$"
    r"|^Google Sheets$"
    r"|^Google Drive$"
    r"|^Bandura Cyber$"
    r"|^Luminar IOCs and Leaked Credentials$"
    r"|^Docker Hub$"
    r"|^Azure DevOps$"
    r"|^Cybersixgill Darkfeed$"
    r"|^Cybersixgill DVE Enrichment$"
    r"|^Spell Checker$"
    r"|^Cybersixgill Darkfeed Enrichment$"
    r"|^Workflow Tools$"
)
# language=regexp
PARAM_DISPLAY_NAME_REGEX: str = (
    r"^[a-zA-Z0-9-'\s]+$"
    # Excluded parameters that already have issues with their name
    r"|^Verify SSL Ceritifcate\?$"
    r"|^Git Password/Token/SSH Key$"
    r"|^EML/MSG Base64 String$"
    r"|^Country\(For multiple countries, provide comma-separated values\)$"
    r"|^Entity Identifier\(s\)$"
    r"|^logzio_security_token$"
    r"|^logzio_region$"
    r"|^minimum_score$"
    r"|^api_token$"
    r"|^eyeglass_ip$"
    r"|^API_Key$"
    r"|^Alert_ID$"
    r"|^Queue_State$"
    r"|^logzio_operations_token$"
    r"|^logzio_custom_endpoint$"
    r"|^api_key$"
    r"|^fields_to_search$"
    r"|^severity_threshold$"
    r"|^Entity Identifier\(s\) Type$"
    r"|^Target Entity Identifier\(s\)$"
    r"|^IOC_Enrichment$"
    r"|^SLA \(in minutes\)$"
    r"|^raw_json$"
    r"|^alert_event_id$"
    r"|^Additional_Data$"
    r"|^page_size$"
    r"|^sort_by$"
    r"|^Data_Range$"
    r"|^Incident_Key$"
    r"|^Team_IDS$"
    r"|^User_IDS$"
    r"|^Service_IDS$"
    r"|^Entity_State$"
    r"|^Incidents_Statuses$"
    r"|^from_time$"
    r"|^to_time$"
    r"|^Incident_ID$"
    r"|^from_date$"
    r"|^logzio_token$"
    r"|^search_term$"
    r"|^Ingest\ only\ alerts\ that\ have\ “is_security”\ attribute\ set\ to\ True\?$"
    r"|^Ingest\ only\ alerts\ that\ have\ “is_incident”\ attribute\ set\ to\ True\?$"
    r"|^Fetch\ Backwards\ Time\ Interval\ \(minutes\)$"
    r"|^Events\ Padding\ Period\ \(hours\)$"
    r"|^Is\ Exchange\ On\-Prem\?$"
    r"|^Is\ Office365\ \(Exchange\ Online\)\?$"
    r"|^Extract\ urls\ from\ HTML\ email\ part\?$"
    r"|^Create\ a\ Separate\ Siemplify\ Alert\ per\ Attached\ Mail\ File\?$"
    r"|^Email\ Padding\ Period\ \(minutes\)$"
    r"|^Tenant\ \(Directory\)\ ID$"
    r"|^Should\ ingest\ only\ starred\ threats\?$"
    r"|^Should\ ingest\ threats\ related\ to\ incidents\?$"
    r"|^Use\ the\ same\ approach\ with\ event\ creation\ for\ all\ alert\ types\?$"
    r"|^Enable\ Fallback\ Logic\ Debug\?$"
    r"|^Create\ Chronicle\ SOAR\ Alerts\ for\ Sentinel\ incidents\ that\ do\ not\ have\ entities\?$"
    r"|^Incidents\ Padding\ Period\ \(minutes\)$"
    r"|^Wait\ For\ Scheduled/NRT\ Alert\ Object$"
    r"|^Api_Key$"
    r"|^Fetch\ Private\ Notes\?$"
    r"|^Offenses\ Creation\ Timer\ \(minutes\)$"
    r"|^What\ Value\ to\ use\ for\ the\ Name\ Field\ of\ Siemplify\ Alert\?$"
    r"|^What\ Value\ to\ use\ for\ the\ Rule\ Generator\ Field\ of\ Siemplify\ Alert\?$"
    r"|^Mask\ findings\?$"
    r"|^Events\ Padding\ Period\ \(minutes\)$"
    r"|^Track\ New\ Events\ Threshold\ \(hours\)$"
    r"|^Token\ Timeout\ \(in\ Seconds\)$"
    r"|^Script\ Timeout\ \(Seconds\)$"
)

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
