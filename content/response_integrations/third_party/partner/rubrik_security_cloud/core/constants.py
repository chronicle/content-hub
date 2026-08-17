from __future__ import annotations

INTEGRATION_NAME = "Rubrik Security Cloud"
INTEGRATION_VERSION = "1.0.0"

RESULT_VALUE_TRUE = True
RESULT_VALUE_FALSE = False
DEFAULT_DEVICE_VENDOR = "Rubrik"
DEFAULT_DEVICE_PRODUCT = INTEGRATION_NAME
RULE_GENERATOR = DEFAULT_DEVICE_VENDOR
COMMON_ACTION_ERROR_MESSAGE = "Error while executing action {}. Reason: {}"
DEFAULT_PAGE_SIZE = 1000
RETRY_COUNT = 3
WAIT_TIME_FOR_RETRY = 5
DEFAULT_RESULTS_LIMIT = 10000000
RATE_LIMIT_EXCEEDED_STATUS_CODE = 429
UNAUTHORIZED_STATUS_CODE = 401
DEFAULT_REQUEST_TIMEOUT = 60
DEFAULT_OFFSET = "0"
DEFAULT_LIMIT = "100"
MAX_TABLE_RECORDS = 1000
MAX_JSON_CHARS = 300
MAX_INT_VALUE = 65535
DEFAULT_REQUEST_NAME = "GoogleSecOps"
DEFAULT_SCAN_NAME = "Google-SecOps-{DATE}-{TIME}"
MAX_SNAPSHOTS_LIMIT = 1000
DEFAULT_TIMEZONE = "UTC"
DEFAULT_SNAPSHOTS_SORT_TYPE = "ASC"
DEFAULT_SONAR_FILE_SORT_ORDER = "DESC"
INTERNAL_SERVER_ERROR_STATUS_CODES = [500, 502, 503, 504]
LIST_EVENTS_DEFAULT_SORT_BY = "LAST_UPDATED"
LIST_EVENTS_DEFAULT_SORT_ORDER = "DESC"
DEFAULT_SEARCH_TIME_PERIOD = "7"
TOKEN_EXPIRY_BUFFER_SECONDS = 30  # 30 seconds buffer
DEFAULT_EXPIRY_SECONDS = 1800 - TOKEN_EXPIRY_BUFFER_SECONDS  # 30 minutes
EXPIRES_IN_KEY = "expires_in"

# Time formats
UNIX_FORMAT = "unix"
ISO_FORMAT = "%Y-%m-%dT%H:%M:%S.%fZ"

# Script Names
PING_SCRIPT_NAME = f"{INTEGRATION_NAME} - Ping"
TURBO_IOC_SCAN_SCRIPT_NAME = f"{INTEGRATION_NAME} - Turbo IOC Scan"
ADVANCE_IOC_SCAN_SCRIPT_NAME = f"{INTEGRATION_NAME} - Advanced IOC Scan"
IOC_SCAN_RESULTS_SCRIPT_NAME = f"{INTEGRATION_NAME} - IOC Scan Results"
LIST_OBJECT_SNAPSHOTS_SCRIPT_NAME = f"{INTEGRATION_NAME} - List Object-Snapshots"
LIST_SONAR_FILE_CONTEXTS_SCRIPT_NAME = f"{INTEGRATION_NAME} - List Sonar File Contexts"
LIST_EVENTS_SCRIPT_NAME = f"{INTEGRATION_NAME} - List Events"
GET_CDM_CLUSTER_LOCATION_SCRIPT_NAME = f"{INTEGRATION_NAME} - Get CDM Cluster Location"
GET_CDM_CLUSTER_CONNECTION_STATE_SCRIPT_NAME = (
    f"{INTEGRATION_NAME} - Get CDM Cluster Connection State"
)
GET_SONAR_SENSITIVE_HITS_SCRIPT_NAME = f"{INTEGRATION_NAME} - Get Sonar Sensitive Hits"
SEARCH_DSPM_VIOLATIONS_SCRIPT_NAME = f"{INTEGRATION_NAME} - Search DSPM Violations"
GET_DSPM_VIOLATION_DETAILS_SCRIPT_NAME = f"{INTEGRATION_NAME} - Get DSPM Violation Details"
UPDATE_VIOLATION_STATUS_SCRIPT_NAME = f"{INTEGRATION_NAME} - Update Violation Status"
DOWNLOAD_SNAPSHOT_RESULTS_CSV_SCRIPT_NAME = f"{INTEGRATION_NAME} - Download Snapshot Results CSV"
DOWNLOAD_REMEDIATION_LOG_SCRIPT_NAME = f"{INTEGRATION_NAME} - Download Remediation Log"
GET_VIOLATION_FILE_LIST_SCRIPT_NAME = f"{INTEGRATION_NAME} - Get Violation File List"
SEARCH_IR_VIOLATIONS_SCRIPT_NAME = f"{INTEGRATION_NAME} - Search IR Violations"
GET_IR_VIOLATION_DETAILS_SCRIPT_NAME = f"{INTEGRATION_NAME} - Get IR Violation Details"

# API Endpoints
FILE_DOWNLOAD_ENDPOINT = "/file-downloads/{external_id}"

# Token TTL (seconds) — 12 hours
TOKEN_TTL_SECONDS = 43200

# Default pagination limits
DEFAULT_MAX_RESULTS = 50
DEFAULT_FILE_LIST_MAX_RESULTS = 25
MAX_ALLOWED_RESULTS = 1000

# Maximum violations and files to return
MAX_VIOLATIONS = 1000
MAX_FILES = 1000

# HTTP Headers
USER_AGENT_NAME = "GoogleSecOps"

# File types for async downloads
USER_FILE_TYPE_CSV = "SNAPSHOT_RESULTS_CSV"
USER_FILE_TYPE_LOG = "REMEDIATION_ACTIONS_LOG_CSV"

# File filter types
FILE_TYPE_HITS = "HITS"
ACCESS_TYPE_UNSPECIFIED = "ACCESS_TYPE_UNSPECIFIED"

# Connector Constants
CLASSIFICATION_CONNECTOR_VERSION = "2026-07-16-v3"
CLASSIFICATION_CONNECTOR_NAME = f"{INTEGRATION_NAME} - Classification Events Connector"
MAX_CONNECTOR_RESULTS = 100
TEST_MODE_MAX_RESULTS = 10
EVENTS_PAGE_SIZE = 1000
CLASSIFICATION_ACTIVITY_MESSAGE_FILTER = (
    "Results available in the Objects page for the workload"
)

# Search time period (days) bounds for the classification connector.
# The window must be between 0 and 1 day; a negative or larger value raises.
MIN_SEARCH_TIME_PERIOD_DAYS = 0
MAX_SEARCH_TIME_PERIOD_DAYS = 1

# Checkpoint file (persisted in the connector run folder) storing only the
# {from_timestamp} the next run should start from.
CHECKPOINT_FILE_NAME = "classification_events_checkpoint.json"

# Severity Mapping (Rubrik severity → SOAR priority score)
RUBRIK_SEVERITY_MAP = {
    "CRITICAL": 100,
    "HIGH": 80,
    "MEDIUM": 60,
    "LOW": 40,
    "INFO": 20,
    "NO": 20,
}

# Action Identifiers
PING_ACTION_IDENTIFIER = "ping"
TURBO_IOC_SCAN_ACTION_IDENTIFIER = "turbo_ioc_scan"
ADVANCE_IOC_SCAN_ACTION_IDENTIFIER = "advance_ioc_scan"
IOC_SCAN_RESULTS_ACTION_IDENTIFIER = "ioc_scan_results"
LIST_OBJECT_SNAPSHOTS_ACTION_IDENTIFIER = "list_object_snapshots"
LIST_SONAR_FILE_CONTEXTS_ACTION_IDENTIFIER = "list_sonar_file_contexts"
LIST_EVENTS_ACTION_IDENTIFIER = "list_events"
GET_CDM_CLUSTER_LOCATION_ACTION_IDENTIFIER = "get_cdm_cluster_location"
GET_CDM_CLUSTER_CONNECTION_STATE_ACTION_IDENTIFIER = "get_cdm_cluster_connection_state"
GET_SONAR_SENSITIVE_HITS_ACTION_IDENTIFIER = "get_sonar_sensitive_hits"
GET_CLOSEST_SNAPSHOT_ACTION_IDENTIFIER = "get_closest_snapshot"
GET_CLASSIFICATION_OBJECT_DETAIL_ACTION_IDENTIFIER = "get_classification_object_detail"

# GraphQL URL
GRAPHQL_URL = "https://{domain}/api/graphql"

# IOC type mapping from UI dropdown/JSON keys to Rubrik GraphQL iocKind values
IOC_TYPE_MAP = {
    "INDICATOR_OF_COMPROMISE_TYPE_HASH": "IOC_HASH",
    "INDICATOR_OF_COMPROMISE_TYPE_PATH_OR_FILENAME": "IOC_FILE_PATTERN",
    "INDICATOR_OF_COMPROMISE_TYPE_YARA_RULE": "IOC_YARA",
    # Also allow direct GraphQL kinds if passed in JSON
    "IOC_HASH": "IOC_HASH",
    "IOC_PATH_OR_FILENAME": "IOC_FILE_PATTERN",
    "IOC_YARA_RULE": "IOC_YARA",
}

# ENUM Lists
SORT_ORDER_ENUM = ["ASC", "DESC"]


# GraphQL Operations
GRAPHQL_DSPM_LIST_OPERATION = "DataSecurityViolationsListQuery"
GRAPHQL_DSPM_GET_OPERATION = "DataSecurityViolationGetQuery"
GRAPHQL_IR_LIST_OPERATION = "IRViolationsListQuery"
GRAPHQL_UPDATE_VIOLATIONS_OPERATION = "UpdatePolicyViolationsMutation"
GRAPHQL_DOWNLOAD_CSV_OPERATION = "DownloadFullSnapshotResultsCsvMutation"
GRAPHQL_DOWNLOAD_BAR_OPERATION = "DownloadBarQuery"
GRAPHQL_CREATE_REMEDIATION_OPERATION = "CreateViolationRemediationMutation"
GRAPHQL_FILE_LIST_OPERATION = "DSPMViolationFileListQuery"

# Policy Types — Fixed for DSPM
DSPM_POLICY_TYPE = "POLICY_TYPE_DATAGOV"

# Status Enum Mapping (UI label → API value)
STATUS_ENUM_MAP = {
    "Open": "POLICY_VIOLATION_STATUS_OPEN",
    "In Progress": "POLICY_VIOLATION_STATUS_IN_PROGRESS",
    "Remediated": "POLICY_VIOLATION_STATUS_REMEDIATED",
    "Dismissed": "POLICY_VIOLATION_STATUS_DISMISSED",
    "Closed": "POLICY_VIOLATION_STATUS_CLOSED",
}

# Severity Enum Mapping
SEVERITY_ENUM_MAP = {
    "Low": "LOW",
    "Medium": "MEDIUM",
    "High": "HIGH",
    "Critical": "CRITICAL",
}

# DSPM Category Enum Mapping
DSPM_CATEGORY_ENUM_MAP = {
    "Misplaced": "MISPLACED",
    "Redundant": "REDUNDANT",
    "Overexposed": "OVEREXPOSED",
    "Unprotected": "UNPROTECTED",
}

# Sensitivity Level Enum Mapping
SENSITIVITY_LEVEL_ENUM_MAP = {
    "High Sensitivity": "HIGH_SENSITIVITY",
    "Medium Sensitivity": "MEDIUM_SENSITIVITY",
    "Low Sensitivity": "LOW_SENSITIVITY",
    "No Sensitivity": "NO_SENSITIVITY",
}

# DSPM Sort By Enum Mapping
DSPM_SORT_BY_ENUM_MAP = {
    "Detection Time": "SORT_DETECTION_TIME",
    "Update Time": "SORT_UPDATE_TIME",
    "Severity": "SORT_SEVERITY",
    "Hits": "SORT_HITS",
    "Files At Risk": "SORT_FILES_AT_RISK",
    "Name": "SORT_NAME",
    "Status": "SORT_STATUS",
}

# IR Sort By Enum Mapping
IR_SORT_BY_ENUM_MAP = {
    "Detection Time": "SORT_DETECTION_TIME",
    "Update Time": "SORT_UPDATE_TIME",
    "Severity": "SORT_SEVERITY",
    "Name": "SORT_NAME",
    "Status": "SORT_STATUS",
    "Identity Type": "SORT_IDENTITY_TYPE",
}

# Sort Order Enum Mapping
SORT_ORDER_ENUM_MAP = {
    "Ascending": "ASC",
    "Descending": "DESC",
}

# IR Policy Types Enum Mapping
IR_POLICY_TYPE_ENUM_MAP = {
    "Identity": "POLICY_TYPE_IDENTITY",
    "IDP": "POLICY_TYPE_IDP",
    "Identity Event": "POLICY_TYPE_IDENTITY_EVENT",
}

# IR Category Enum Mapping
IR_CATEGORY_ENUM_MAP = {
    "Identity Hygiene": "IDENTITY_HYGIENE",
    "Authentication and Secret Management": "AUTHENTICATION_AND_SECRET_MANAGEMENT",
    "Identity Provider Security": "IDENTITY_PROVIDER_SECURITY",
    "Excessive Identity Rights": "EXCESSIVE_IDENTITY_RIGHTS",
}

# IR Identity Provider Enum Mapping
IR_IDENTITY_PROVIDER_ENUM_MAP = {
    "Unspecified": "IDP_UNSPECIFIED",
    "On-Prem AD": "ON_PREM_AD",
    "Entra ID": "ENTRA_ID",
    "AWS": "AWS",
    "Local AD": "LOCAL_AD",
    "SharePoint": "SHAREPOINT",
    "System": "SYSTEM",
    "Okta": "OKTA",
}

# IR Identity Tag Enum Mapping
IR_IDENTITY_TAG_ENUM_MAP = {
    "Unspecified": "IDENTITY_TAG_UNSPECIFIED",
    "Privileged": "PRIVILEGED",
    "At Risk": "AT_RISK",
    "Sensitive": "SENSITIVE",
}

# File List Risk Level Enum Mapping
FILE_RISK_LEVEL_ENUM_MAP = {
    "Unknown Risk": "UNKNOWN_RISK",
    "High Risk": "HIGH_RISK",
    "Medium Risk": "MEDIUM_RISK",
    "Low Risk": "LOW_RISK",
    "No Risk": "NO_RISK",
}

# File List Exposure Enum Mapping
FILE_EXPOSURE_ENUM_MAP = {
    "Explicit": "EXPLICIT",
    "Inherited": "INHERITED",
    "Not Open": "NOT_OPEN",
    "Unknown Access": "UNKNOWN_ACCESS",
    "Public": "PUBLIC",
}

# File List Access Via Enum Mapping
FILE_ACCESS_VIA_ENUM_MAP = {
    "Unspecified": "ACCESS_TYPE_UNSPECIFIED",
    "Direct": "DIRECT",
    "Group": "GROUP",
    "Role": "ROLE",
}

# File List Sort By Enum Mapping
FILE_SORT_BY_ENUM_MAP = {
    "Hits": "HITS",
    "Name": "NAME",
    "Last Access Time": "LAST_ACCESS_TIME",
    "Last Modified": "LAST_MODIFIED",
    "Creation Time": "CREATION_TIME",
    "Last Scan Time": "LAST_SCAN_TIME",
}

# File download types (for polling)
CSV_FILE_TYPE_SNAPSHOT = "SNAPSHOT_RESULTS_CSV"
CSV_FILE_TYPE_REMEDIATION = "REMEDIATION_ACTIONS_LOG_CSV"

# Remediation type for log export
REMEDIATION_TYPE_EXPORT_LOG = "REMEDIATION_TYPE_EXPORT_ACTIONS_LOG_TO_CSV"
REMEDIATION_TARGET_TYPE_VIOLATION = "REMEDIATION_TARGET_TYPE_VIOLATION"

# File states (polling)
FILE_STATE_READY = "READY"
FILE_STATE_FAILED = "FAILED"

# Backward-compatible enum maps for utils.py
DSPM_SEVERITY_MAP = {
    "Low": "LOW",
    "Medium": "MEDIUM",
    "High": "HIGH",
    "Critical": "CRITICAL",
}

DSPM_CATEGORY_MAP = DSPM_CATEGORY_ENUM_MAP
SENSITIVITY_LEVEL_MAP = SENSITIVITY_LEVEL_ENUM_MAP
DSPM_SORT_BY_MAP = DSPM_SORT_BY_ENUM_MAP
IR_SORT_BY_MAP = IR_SORT_BY_ENUM_MAP
SORT_ORDER_MAP = SORT_ORDER_ENUM_MAP
IR_POLICY_TYPE_MAP = IR_POLICY_TYPE_ENUM_MAP
IR_CATEGORY_MAP = IR_CATEGORY_ENUM_MAP
FILE_RISK_LEVEL_MAP = FILE_RISK_LEVEL_ENUM_MAP
FILE_EXPOSURE_MAP = FILE_EXPOSURE_ENUM_MAP
FILE_SORT_BY_MAP = FILE_SORT_BY_ENUM_MAP
FILE_ACCESS_VIA_MAP = FILE_ACCESS_VIA_ENUM_MAP

# Default IR policy types
DEFAULT_IR_POLICY_TYPES = ["POLICY_TYPE_IDENTITY", "POLICY_TYPE_IDP"]

# Error Messages
ERROR_NO_VIOLATION_FOUND = "No violation found with ID: {}"
ERROR_INVALID_STATUS = "Invalid status value: {}. Valid values: {}"
ERROR_INVALID_ENUM = "Invalid value '{}' for parameter '{}'. Valid values: {}"
ERROR_DATE_RANGE_REQUIRED = "Both Detection Start Date and Detection End Date must be provided together."
ERROR_UPDATE_DATE_RANGE_REQUIRED = "Both Update Start Date and Update End Date must be provided together."
ERROR_DETECTION_DATE_ORDER = "Detection End Date must be later than Detection Start Date."
ERROR_UPDATE_DATE_ORDER = "Update End Date must be later than Update Start Date."

# Get Violation File List date-order messages
ERROR_LAST_ACCESS_DATE_ORDER = "Last Access End Date must be later than Last Access Start Date."
ERROR_LAST_UPDATED_DATE_ORDER = "Last Updated End Date must be later than Last Updated Start Date."
ERROR_CREATION_DATE_ORDER = "Creation End Date must be later than Creation Start Date."
ERROR_LAST_SCAN_DATE_ORDER = "Last Scan End Date must be later than Last Scan Start Date."
ERROR_POLL_TIMEOUT = "Timed out waiting for file generation after {} seconds."
ERROR_FILE_GENERATION_FAILED = "File generation failed with state: {}"
ERROR_CSV_TRIGGER_FAILED = "Failed to trigger CSV generation: {}"
ERROR_REMEDIATION_LOG_FAILED = "Failed to create remediation log: {}"

# Max Results validation messages (Search DSPM Violations)
ERROR_MAX_RESULTS_NOT_INTEGER = "Max Results must be an integer. Got: {}"
ERROR_MAX_RESULTS_TOO_LOW = "Max Results must be at least 1."
ERROR_MAX_RESULTS_TOO_HIGH = "Max Results cannot exceed {}. Received: {}"

# DSPM Object Type Enum Mapping (values are used verbatim as the API enum)
DSPM_OBJECT_TYPE_VALUES = [
    "VSPHERE_VIRTUAL_MACHINE",
    "LINUX_FILESET",
    "SHARE_FILESET",
    "NUTANIX_VIRTUAL_MACHINE",
    "WINDOWS_FILESET",
    "HYPERV_VIRTUAL_MACHINE",
    "VOLUME_GROUP",
    "NAS_FILESET",
    "AZURE_VIRTUAL_MACHINE",
    "AZURE_MANAGED_DISK",
    "AZURE_STORAGE_ACCOUNT",
    "AZURE_SQL_DATABASE_DB",
    "AZURE_SQL_MANAGED_INSTANCE_DB",
    "O365_ONEDRIVE",
    "O365_SITE",
    "AWS_NATIVE_S3_BUCKET",
    "AWS_NATIVE_EBS_VOLUME",
    "AWS_NATIVE_RDS_INSTANCE",
    "AWS_NATIVE_DYNAMODB_TABLE",
    "ORACLE_DATABASE",
    "ORACLE_DATA_GUARD_GROUP",
    "K8S_VIRTUAL_MACHINE",
    "GCP_NATIVE_DISK",
    "GCP_NATIVE_GCE_INSTANCE",
    "K8S_PROTECTION_SET",
]
DSPM_OBJECT_TYPE_ENUM_MAP = {value: value for value in DSPM_OBJECT_TYPE_VALUES}

# GraphQL Queries
DSPM_LIST_QUERY = """
query DataSecurityViolationsListQuery(
  $policyIds: [UUID!]
  $resourceIds: [String!]
  $statuses: [PolicyViolationStatus!]
  $severities: [Severity!]
  $categories: [Category!]
  $sensitivityLevels: [SensitivityLevel!]
  $detectionDate: TimeRangeInput
  $updateDate: TimeRangeInput
  $first: Int
  $after: String
  $sortBy: PolicyViolationSortField
  $sortOrder: SortOrder
  $resourceMetadataFilter: ResourceMetadataFiltersInput
  $dataCategoryIds: [String!]
  $dataTypeIds: [String!]
) {
  policyViolations(
    policyIds: $policyIds
    resourceIds: $resourceIds
    statuses: $statuses
    policySeverities: $severities
    policyCategories: $categories
    sensitivityLevels: $sensitivityLevels
    detectionDate: $detectionDate
    updateDate: $updateDate
    policyTypes: [POLICY_TYPE_DATAGOV]
    first: $first
    after: $after
    sortBy: $sortBy
    sortOrder: $sortOrder
    resourceMetadataFilter: $resourceMetadataFilter
    dataCategoryIds: $dataCategoryIds
    dataTypeIds: $dataTypeIds
  ) {
    edges {
      node {
        policyViolationId
        status
        createdAt
        lastUpdatedAt
        name
        violationSeverity
        policy {
          policyId
          name
          policySeverity
          policyCategory
          description
          __typename
        }
        resourceId
        resourceType
        resourceMetadata {
          metadata {
            ... on CommonAssetMetadata {
              name
              objectType
              platform
              physicalHost
              region
              creationTime
              lastAccessTime
              snapshotTimestamp
              clusterInfo {
                clusterName
                clusterUuid
                __typename
              }
              cloudAccountInfo {
                accountName
                __typename
              }
              __typename
            }
            __typename
          }
          __typename
        }
        details {
          ... on DataGovViolationDetails {
            violatedNoRiskSensitiveHits
            violatedLowRiskSensitiveHits
            violatedMediumRiskSensitiveHits
            violatedHighRiskSensitiveHits
            snapshotId
            __typename
          }
          __typename
        }
        remediations {
          type
          state
          remediationDetails {
            details {
              ticketNumber
              ticketUrl
              __typename
            }
            __typename
          }
          __typename
        }
        __typename
      }
      cursor
      __typename
    }
    pageInfo {
      startCursor
      endCursor
      hasNextPage
      hasPreviousPage
      __typename
    }
    count
    __typename
  }
}
"""

DSPM_GET_QUERY = """
query DataSecurityViolationGetQuery($violationId: String!) {
  policyViolation(
    violationId: $violationId
    policyTypes: [POLICY_TYPE_DATAGOV]
  ) {
    ...DataAtRiskPanelFragment
    status
    violationSeverity
    policyViolationId
    createdAt
    lastUpdatedAt
    resourceId
    policy {
      policyId
      name
      description
      policyCategory
      policySeverity
      containsAccessFilters
      __typename
    }
    remediations {
      remediationId
      state
      remediationDetails {
        details {
          ticketNumber
          ticketUrl
          __typename
        }
        __typename
      }
      __typename
    }
    resourceMetadata {
      metadata {
        ... on CommonAssetMetadata {
          platform
          cloudAccountInfo {
            accountName
            __typename
          }
          objectType
          clusterInfo {
            clusterName
            clusterUuid
            __typename
          }
          creationTime
          lastAccessTime
          snapshotTimestamp
          physicalHost
          name
          isDeleted
          region
          __typename
        }
      }
      __typename
    }
    __typename
  }
}

fragment SensitiveHitsChartFragment on DataGovViolationDetails {
  snapshotId
  violatedSensitiveHits
  violatedNoRiskSensitiveHits
  violatedLowRiskSensitiveHits
  violatedMediumRiskSensitiveHits
  violatedHighRiskSensitiveHits
  __typename
}

fragment DataAtRiskPanelFragment on PolicyViolation {
  details {
    ...SensitiveHitsChartFragment
    ... on DataGovViolationDetails {
      dataCategories {
        id
        name
        totalViolatedHits
        __typename
      }
      dataTypes {
        id
        name
        totalViolatedHits
        __typename
      }
      mipLabels {
        id
        totalViolatedHits
        name
        __typename
      }
      documentTypes {
        id
        name
        totalViolatedHits
        __typename
      }
      __typename
    }
    __typename
  }
  __typename
}
"""

UPDATE_VIOLATIONS_MUTATION = """
mutation UpdatePolicyViolationsMutation($input: BulkUpdatePolicyViolationsInput!) {
  bulkUpdatePolicyViolations(input: $input)
}
"""

DOWNLOAD_CSV_MUTATION = """
mutation DownloadFullSnapshotResultsCsvMutation(
  $filters: DownloadResultsCsvFiltersInput
  $snappableFid: String!
  $snapshotFid: String!
) {
  downloadSnapshotResultsCsv(
    snappableFid: $snappableFid
    snapshotFid: $snapshotFid
    downloadFilter: $filters
  ) {
    isSuccessful
    __typename
  }
}
"""

DOWNLOAD_BAR_QUERY = """
query DownloadBarQuery {
  allUserFiles {
    downloads {
      externalId
      createdAt
      expiresAt
      completedAt
      creator
      filename
      type
      state
      __typename
    }
    __typename
  }
}
"""

CREATE_REMEDIATION_MUTATION = """
mutation CreateViolationRemediationMutation($input: CreateViolationRemediationInput!) {
  createViolationRemediation(input: $input) {
    remediationId
    __typename
  }
}
"""

FILE_LIST_QUERY = """
query DSPMViolationFileListQuery(
  $first: Int!
  $after: String
  $snappableFid: String!
  $snapshotFid: String!
  $filters: ListFileResultFiltersInput
  $sort: FileResultSortInput
  $timezone: String!
) {
  policyObj(snappableFid: $snappableFid, snapshotFid: $snapshotFid) {
    id: snapshotFid
    fileResultConnection(
      first: $first
      after: $after
      filter: $filters
      sort: $sort
      timezone: $timezone
    ) {
      edges {
        cursor
        node {
          nativePath
          stdPath
          filename
          mode
          size
          lastAccessTime
          lastModifiedTime
          creationTime
          lastScanTime
          directory
          createdBy
          modifiedBy
          numDescendantFiles
          numDescendantErrorFiles
          numDescendantSkippedExtFiles
          numDescendantSkippedSizeFiles
          errorCode
          hits {
            totalHits
            violations
            violationsDelta
            totalHitsDelta
            __typename
          }
          filesWithHits {
            totalHits
            violations
            __typename
          }
          openAccessFilesWithHits {
            totalHits
            violations
            __typename
          }
          staleFilesWithHits {
            totalHits
            violations
            __typename
          }
          sensitiveHits {
            highRiskHits { totalHits violatedHits __typename }
            mediumRiskHits { totalHits violatedHits __typename }
            lowRiskHits { totalHits violatedHits __typename }
            noRiskHits { totalHits violatedHits __typename }
            __typename
          }
          analyzerResults {
            hits { totalHits violations __typename }
            analyzer { id name analyzerType __typename }
            __typename
          }
          openAccessType
          stalenessType
          numActivities
          numActivitiesDelta
          exposureSummary {
            exposureType
            fileCount { totalCount violatedCount __typename }
            __typename
          }
          dbEntityType
          __typename
        }
        __typename
      }
      pageInfo {
        startCursor
        endCursor
        hasNextPage
        hasPreviousPage
        __typename
      }
      hasLatestData
      __typename
    }
    __typename
  }
}
"""

IR_LIST_QUERY = """
query IRViolationsListQuery(
  $policyIds: [UUID!]
  $resourceIds: [String!]
  $statuses: [PolicyViolationStatus!]
  $severities: [Severity!]
  $categories: [Category!]
  $policyTypes: [PolicyType!]!
  $detectionDate: TimeRangeInput
  $updateDate: TimeRangeInput
  $first: Int
  $after: String
  $sortBy: PolicyViolationSortField
  $sortOrder: SortOrder
  $resourceMetadataFilter: ResourceMetadataFiltersInput
  $dataCategoryIds: [String!]
  $dataTypeIds: [String!]
) {
  policyViolations(
    policyIds: $policyIds
    resourceIds: $resourceIds
    statuses: $statuses
    policySeverities: $severities
    policyCategories: $categories
    detectionDate: $detectionDate
    updateDate: $updateDate
    policyTypes: $policyTypes
    first: $first
    after: $after
    sortBy: $sortBy
    sortOrder: $sortOrder
    resourceMetadataFilter: $resourceMetadataFilter
    dataCategoryIds: $dataCategoryIds
    dataTypeIds: $dataTypeIds
  ) {
    edges {
      node {
        policyViolationId
        violationSeverity
        createdAt
        resourceId
        resourceType
        status
        lastUpdatedAt
        policy {
          policyId
          name
          description
          policySeverity
          policyCategory
          frameworks
          manualRemediationProcess
          __typename
        }
        details {
          ... on IdentityViolationDetails {
            domainUniqueId
            __typename
          }
          ... on IdpViolationDetails {
            domainUniqueId
            __typename
          }
          __typename
        }
        resourceMetadata {
          metadata {
            ... on IdentityMetadata {
              displayName
              domainName
              idpType
              principalType
              privilegeType
              userPrincipalName
              status
              title
              source
              identityTags
              uniqueId
              nativeType
              __typename
            }
            ... on IdpMetadata {
              domainName
              domainUniqueId
              idpType
              rootDomainName
              rootDomainId
              __typename
            }
            __typename
          }
          __typename
        }
        __typename
      }
      cursor
      __typename
    }
    pageInfo {
      startCursor
      endCursor
      hasNextPage
      hasPreviousPage
      __typename
    }
    count
    __typename
  }
}
"""
