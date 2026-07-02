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

"""GraphQL queries for SentinelOne Singularity Operations Center."""

TEST_CONNECTIVITY_QUERY = """query GetUnifiedAlerts($first: Int, $viewType: ViewType) {
  alerts(first: $first, viewType: $viewType) {
    edges {
      node {
        id
      }
    }
  }
}"""

GET_UNIFIED_ALERTS_QUERY = """query GetUnifiedAlerts(
  $first: Int
  $after: String
  $viewType: ViewType
  $orFilter: OrFilterSelectionInput
) {
  alerts(
    first: $first
    after: $after
    viewType: $viewType
    orFilter: $orFilter
  ) {
    totalCount
    pageInfo {
      hasNextPage
      endCursor
    }
    edges {
      node {
        id
        name
        severity
        status
        analystVerdict
        detectedAt
        createdAt
        lastSeenAt
        updatedAt
      }
    }
  }
}"""

GET_ALERT_DETAILS_QUERY = """query GetAlertByIdAllFields($id: ID!) {
  alert(id: $id) {
    id
    externalId
    name
    description
    severity
    status
    analystVerdict
    classification
    confidenceLevel
    detectedAt
    createdAt
    firstSeenAt
    lastSeenAt
    updatedAt
    ticketId
    storylineId
    selfLink
    dataSources
    attackSurfaces
    labels
    noteExists
    result
    preemptiveMitigationType
    aiInvestigation {
      status
      timestamp
      verdict
    }
    analytics {
      category
      name
      typeValue
      uid
    }
    assignee {
      userId
      fullName
      email
    }
    assets {
      id
      name
      category
      subcategory
      assetTypeClassifier
      osType
      osVersion
      agentUuid
      agentVersion
      connectivityToConsole
      decommissioned
      deleted
      lastLoggedInUser
      pendingReboot
      policy
      primary
      role
      status
      origin
    }
    detectionTime {
      attacker {
        host
        ip
      }
      scope {
        accountId
        accountName
        groupId
        groupName
        siteId
        siteName
      }
      targetUser {
        domain
        emailAddress
        name
      }
    }
    indicators {
      uid
      type
      message
      eventTime
      severity
    }
    observables {
      name
      type
      typeName
      value
    }
    process {
      cmdLine
      parentName
      username
      userDomain
      userDisplayName
      file {
        name
        path
        size
        md5
        sha1
        sha256
        certSubject
        certSerialNumber
        certExpiresAt
        signatureVerification
      }
    }
  }
}"""


UPDATE_ALERT_MUTATION = """mutation AlertTriggerActions(
  $actions: [TriggerActionInput!]!
  $filter: OrFilterSelectionInput
  $scope: ScopeSelectorInput
  $viewType: ViewType
) {
  alertTriggerActions(
    actions: $actions
    filter: $filter
    scope: $scope
    viewType: $viewType
  ) {
    __typename
    ... on ActionsTriggered {
      actions {
        actionId
        alertCount
        success {
          id
        }
        failure {
          id
          errorMessage
          errorType
        }
        skip {
          id
          skipMessage
          skipType
        }
      }
    }
    ... on TriggerActionsError {
      errors {
        errorMessage
        errorPayload {
          ... on ActionsErrorConcurrentUserLimitPayload {
            limit
          }
          ... on ActionsErrorLimitPayload {
            limit
          }
        }
      }
    }
    ... on TriggerActionsScheduled {
      executionId
      bulkActionTriggerId
    }
  }
}"""

ADD_ALERT_NOTE_MUTATION = """mutation AddAlertNote(
  $alertId: ID!
  $text: String!
  $plainText: String
  $type: ContentType
) {
  addAlertNote(
    alertId: $alertId
    text: $text
    plainText: $plainText
    type: $type
  ) {
    data {
      id
      alertId
      text
      type
      createdAt
      updatedAt
    }
  }
}"""
