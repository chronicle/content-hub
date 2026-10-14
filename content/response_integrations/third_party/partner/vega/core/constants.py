"""Shared constants for the Vega Google SecOps integration."""

from __future__ import annotations

INTEGRATION_NAME = "Vega"
DEVICE_PRODUCT = "Vega"
PRODUCT_NAME = "Vega"
VENDOR_NAME = "Vega"
ENTITY_TYPE_ALERT = "Alert"
ENTITY_TYPE_INCIDENT = "Incident"
SOAR_ALERT_TYPE_ALERT = "Vega Alert"
SOAR_ALERT_TYPE_INCIDENT = "Vega Incident"
SOAR_META_KEY = "_soar_meta"

PING_SCRIPT_NAME = f"{INTEGRATION_NAME} - Ping"
GET_ALERT_EVENTS_SCRIPT_NAME = f"{INTEGRATION_NAME} - Get Alert Events"
GET_INCIDENT_TIMELINE_SCRIPT_NAME = f"{INTEGRATION_NAME} - Get Incident Timeline"
GET_INCIDENT_DETAILS_SCRIPT_NAME = f"{INTEGRATION_NAME} - Get Incident Details"
UPDATE_ALERT_SCRIPT_NAME = f"{INTEGRATION_NAME} - Update Alert"
UPDATE_INCIDENT_SCRIPT_NAME = f"{INTEGRATION_NAME} - Update Incident"
APPLY_VEGA_LABELS_SCRIPT_NAME = f"{INTEGRATION_NAME} - Apply Vega Labels as Tags"
EXTRACT_RESET_PASSWORD_USER_SCRIPT_NAME = f"{INTEGRATION_NAME} - Extract Reset Password User"
GENERATE_RANDOM_PASSWORD_SCRIPT_NAME = f"{INTEGRATION_NAME} - Generate Random Password"
ADD_CASE_COMMENT_SCRIPT_NAME = f"{INTEGRATION_NAME} - Add Case Comment"
DEFAULT_PASSWORD_LENGTH = 16
MIN_PASSWORD_LENGTH = 12
# Avoid quotes, backslashes, and brackets so the value is safe in playbook JSON.
PASSWORD_SYMBOLS = "!@#$%^&*-_=+"

CONNECTOR_NAME = "Vega Alerts and Incidents Connector"
CHECKPOINT_PROPERTY_KEY = "vega_ingestion_checkpoint"
REMEDIATION_PROPERTY_KEY = "vega_sync_state"
SOAR_CASE_SEARCH_PATH = "external/v1/search/CaseSearchEverything"
SOAR_CASE_DETAILS_PATH = "external/v1/cases/GetCaseFullDetails/{case_id}"
SOAR_SEARCH_PAGE_SIZE = 50
# CaseSearchEverything: 1 = last modification (a case close updates this).
SOAR_TIME_RANGE_MODIFIED = 1
SOAR_DETAILS_GET_CAP = 25
# CaseDataStatus.CLOSED in SecOps/Siemplify.
SOAR_CASE_STATUS_CLOSED = 2
SOAR_CASE_STATUS_OPEN = (0, 1)

DEFAULT_API_ROOT = "https://api.vega.io"
LOGIN_PATH = "/api/v1/login_machine"
QUERY_PATH = "/api/v1/query"

DEFAULT_HTTP_TIMEOUT = (10, 60)
LOOKBACK_MIN = 1
LOOKBACK_MAX = 60
BACKFILL_MIN = 0
BACKFILL_MAX = 365
GRAPHQL_PAGE_SIZE = 50
ALERT_EVENTS_PAGE_SIZE = 100
ALERT_EVENTS_MAX_FETCH = 2500
# getAlertsEvents(alertIds) accepts at most this many ids per request.
ALERT_EVENTS_ID_BATCH = 10
# SOAR attaches at most this many child events per Vega alert. Ingest stops
# paging getAlertsEvents here so it does not download 2500 rows to keep 200.
MAX_EVENTS_PER_ALERT = 200
# Nested related Vega alerts are attached as events on the incident AlertInfo
# (SOAR creates one case per AlertInfo unless grouping is enabled).
NESTED_RELATED_KEY = "nested_related_alerts"
SYNC_RESOLVED_STATUS = "RESOLVED"
# getAlerts(alertIds) accepts up to 1000 ids, and limit may be 1000.
ALERT_ID_LOOKUP_BATCH = 1000
# getAlerts(alertIds) for incident metadata. One request may carry this many
# UUIDs; the response is still paged with limit/offset.
ALERT_METADATA_ID_BATCH = 1000
TIMELINE_PAGE_SIZE = 100
TIMELINE_MAX_FETCH = 2500
TEST_RUN_MAX_FETCH = 5
MAX_CONSECUTIVE_429 = 8
RATE_LIMIT_INITIAL_WAIT_SECONDS = 2
RATE_LIMIT_STEP_SECONDS = 2
# Leave this much time to package cases and write the checkpoint before
# SecOps kills the connector (PythonProcessTimeout).
INGEST_STOP_BUFFER_SECONDS = 90
SERVER_ERROR_RETRIES = 3
SERVER_ERROR_WAIT_SECONDS = 2
INGESTED_ID_CAP = 5000
# Related-alert case chunks: titles use (batch N) and grouping id
# Vega:incident:<id>:related:batch:<N>, with N from a per-incident checkpoint.
MAX_ALERTS_PER_CASE = 90
# Bump when a previous return marked ids sent that were not all created.
RELATED_BATCH_VERSION = 5
# getAlerts(alertIds) needs a time bound; related alerts can be older than the
# ingest window, so ID lookups use this createdAt/updatedAt floor.
ALERT_ID_LOOKUP_FROM = "2015-01-01T00:00:00.000Z"
PYTHON_PROCESS_TIMEOUT_DEFAULT = "930"

INTEGRATION_VERSION = 3
DOCUMENTATION_LINK = "https://vega.io"

PARAM_API_ROOT = "API Root"
PARAM_ACCESS_KEY_ID = "Access Key ID"
PARAM_ACCESS_KEY = "Access Key"
PARAM_ENTITIES = "Vega Entities to Fetch"
PARAM_LOOKBACK = "Fetch Lookback (Minutes)"
PARAM_BACKFILL = "Backfill Days"
PARAM_ALERT_SEVERITIES = "Alert Severities to Fetch"
PARAM_ALERT_STATUSES = "Alert Statuses to Fetch"
PARAM_ALERT_VERDICTS = "Alert Verdicts to Fetch"
PARAM_HAS_RELATED = "Has Related Incidents"
PARAM_INCIDENT_SEVERITIES = "Incident Severities to Fetch"
PARAM_INCIDENT_USER_STATUSES = "Incident User Statuses to Fetch"
PARAM_INCIDENT_INVESTIGATION_STATUSES = "Incident Investigation Statuses to Fetch"
PARAM_INCIDENT_VERDICTS = "Incident Verdicts to Fetch"
PARAM_FETCH_RELATED_ALERT_METADATA = "Fetch Related Alert Metadata"
PARAM_SYNC = "Sync Case Close to Vega"
PARAM_PYTHON_TIMEOUT = "PythonProcessTimeout"
PYTHON_TIMEOUT_MIN = 30
PYTHON_TIMEOUT_MAX = 3600

SEVERITY_OPTIONS = ("LOW", "MEDIUM", "HIGH", "CRITICAL")
ALERT_STATUS_OPTIONS = ("OPEN", "IN PROGRESS", "PEER REVIEW", "RESOLVED")
INCIDENT_USER_STATUS_OPTIONS = ("OPEN", "IN REVIEW", "ON HOLD", "RESOLVED")
INCIDENT_INVESTIGATION_STATUS_OPTIONS = (
    "NEW",
    "INVESTIGATING",
    "COMPLETED",
    "FAILED",
)
VERDICT_OPTIONS = ("MALICIOUS", "SUSPICIOUS", "BENIGN", "INCONCLUSIVE", "NA")
ENTITY_OPTIONS = ("Alerts", "Incidents")
RELATED_OPTIONS = ("Yes", "No")

SEVERITY_TO_ALERT_PRIORITY = {
    "CRITICAL": 100,
    "HIGH": 80,
    "MEDIUM": 60,
    "LOW": 40,
}

MSG_UNAUTHORIZED = "The Access Key or Access Key ID is incorrect. Check both values and try again."
MSG_INVALID_ACCESS_KEY = "The Access Key is incorrect. Enter a valid Access Key and try again."
MSG_INVALID_ACCESS_KEY_ID = "The Access Key ID is incorrect. Enter a valid Access Key ID and try again."
MSG_INVALID_API_ROOT = (
    "The API Root is incorrect or unreachable. Enter a valid Vega HTTPS URL, for example https://api.vega.io."
)
MSG_FORBIDDEN = "Access denied by Vega. Verify the Access Key permissions."
MSG_BAD_REQUEST = "Invalid request to Vega. Check filters and identifiers."
MSG_NOT_FOUND = "Requested Vega resource was not found."
MSG_RATE_LIMIT = "Vega rate limit reached. Wait and try again."
MSG_SERVER_ERROR = "Vega is temporarily unavailable. Try again later."
MSG_TIMEOUT = "Connection to Vega timed out. Check the API Root and network access, then try again."
MSG_UNREACHABLE = MSG_INVALID_API_ROOT

# getAlerts used by ingest. Arguments match what the connector sends. Extra
# unused args (sortBy, originType, alertNames, ...) are omitted: unknown
# arguments reject the whole query. AlertInfo fields including vegaAlertId
# and labels are valid here (they are not valid on IncidentAlertSummary).
GET_ALERTS_QUERY = """
query GetAlerts(
  $alertIds: [ID!],
  $vegaAlertIds: [String!],
  $alertSeverities: [AlertSeverity!],
  $statuses: [AlertStatus!],
  $alertVerdicts: [AlertVerdict!],
  $hasRelatedIncidents: Boolean,
  $from: Time,
  $to: Time,
  $updatedFrom: Time,
  $updatedTo: Time,
  $limit: Int,
  $offset: Int
) {
  getAlerts(
    alertIds: $alertIds,
    vegaAlertIds: $vegaAlertIds,
    alertSeverities: $alertSeverities,
    statuses: $statuses,
    alertVerdicts: $alertVerdicts,
    hasRelatedIncidents: $hasRelatedIncidents,
    from: $from,
    to: $to,
    updatedFrom: $updatedFrom,
    updatedTo: $updatedTo,
    limit: $limit,
    offset: $offset
  ) {
    alerts {
      id
      vegaAlertId
      detectionId
      name
      description
      severity
      status
      assignee { userId displayName email }
      assignees { userId displayName email }
      dataSources
      createdAt
      updatedAt
      mitre { mitreTactics mitreTechniques }
      relatedIncidents { incidentId name }
      detectionSource
      detectionDescription
      detectionQuery
      eventCount
      isTestMode
      verdict
      verdictReasoning
      escalation {
        status
        reasoning
        determinedAt
        incident { incidentId name }
      }
      dedupCount
      comments { text addedBy addedAt }
      labels { name color }
      skills { id name version }
      actors { field values }
      targets { field values }
      href
    }
    total
    limit
    offset
    error { code message }
  }
}
""".strip()

# Incident list used by the Yes path. Nested `alerts` is IncidentAlertSummary
# (alertId, name, createdAt only). Do not add `vegaAlertId` or `labels` there:
# Vega rejects those fields and getIncidents returns no incidents at all.
# Related-alert vegaAlertId and labels come from getAlerts, not this nested
# selection.
GET_INCIDENTS_QUERY = """
query GetIncidents(
  $incidentNames: [String!],
  $nameContains: String,
  $incidentIds: [ID!],
  $vegaIncidentIds: [String!],
  $severities: [IncidentSeverity!],
  $investigationStatuses: [IncidentInvestigationStatusPublic!],
  $userStatuses: [IncidentUserStatusPublic!],
  $verdicts: [IncidentVerdictPublic!],
  $assets: [String!],
  $from: Time,
  $to: Time,
  $updatedFrom: Time,
  $updatedTo: Time,
  $sortBy: IncidentSortFieldPublic,
  $sortOrder: SortOrderPublic,
  $limit: Int,
  $offset: Int
) {
  getIncidents(
    incidentNames: $incidentNames,
    nameContains: $nameContains,
    incidentIds: $incidentIds,
    vegaIncidentIds: $vegaIncidentIds,
    severities: $severities,
    investigationStatuses: $investigationStatuses,
    userStatuses: $userStatuses,
    verdicts: $verdicts,
    assets: $assets,
    from: $from,
    to: $to,
    updatedFrom: $updatedFrom,
    updatedTo: $updatedTo,
    sortBy: $sortBy,
    sortOrder: $sortOrder,
    limit: $limit,
    offset: $offset
  ) {
    incidents {
      id
      vegaUniqueIncidentId
      name
      createdBy
      createdAt
      lastUpdated
      severity
      investigationStatus
      userStatus
      dataSources
      verdict
      verdictReasoning
      assignee { userId displayName email }
      assignees { userId displayName email }
      comments { text addedBy addedAt }
      incidentSummary
      incidentFindings
      assets
      observables
      alertsCount
      alerts { alertId name createdAt }
      recommendedActions { name description actionKey targetParams }
      investigationPlan {
        stepName
        stepConclusion
        cells { cellName query queryId }
      }
      labels { id categoryId name color usageCount }
      skills { id name version }
      link
      href
    }
    total
    limit
    offset
    error { code message }
  }
}
""".strip()

GET_ALERT_EVENTS_QUERY = """
query GetAlertsEvents($alertId: ID, $alertIds: [ID!], $limit: Int, $offset: Int) {
  getAlertsEvents(alertId: $alertId, alertIds: $alertIds, limit: $limit, offset: $offset) {
    total
    limit
    offset
    results
    error { code message }
    alerts {
      alertId
      total
      results
      error { code message }
    }
  }
}
""".strip()

GET_INCIDENT_TIMELINE_QUERY = """
query GetIncidentTimeline($incidentId: ID!, $limit: Int, $offset: Int) {
  getIncidentTimeline(incidentId: $incidentId, limit: $limit, offset: $offset) {
    events {
      id
      timestamp
      summary
      dataSources
      assets
      observables
      alert { alertId name createdAt }
    }
    total
    limit
    offset
    error { code message }
  }
}
""".strip()

UPDATE_ALERTS_MUTATION = """
mutation UpdateAlerts($input: UpdateAlertsInput!) {
  updateAlerts(input: $input) {
    alerts {
      id
      vegaAlertId
      severity
      status
      verdict
      verdictReasoning
      assignee { userId displayName email }
      assignees { userId displayName email }
      comments { text addedBy addedAt }
    }
    error { code message }
  }
}
""".strip()

UPDATE_INCIDENTS_MUTATION = """
mutation UpdateIncidents($input: UpdateIncidentsInput!) {
  updateIncidents(input: $input) {
    incidents {
      incidentId
      incidentName
      investigationStatus
      userStatus
      assignee { userId displayName email }
      assignees { userId displayName email }
      verdict
      verdictReasoning
      updatedAt
    }
    errors { code message }
  }
}
""".strip()

# Close-sync only sets alert status / incident userStatus. Selection is
# identifiers plus those fields and errors.
UPDATE_ALERTS_STATUS_MUTATION = """
mutation UpdateAlertsStatus($input: UpdateAlertsInput!) {
  updateAlerts(input: $input) {
    alerts { id vegaAlertId status }
    error { code message }
  }
}
""".strip()

UPDATE_INCIDENTS_STATUS_MUTATION = """
mutation UpdateIncidentsStatus($input: UpdateIncidentsInput!) {
  updateIncidents(input: $input) {
    incidents { incidentId investigationStatus userStatus }
    errors { code message }
  }
}
""".strip()
