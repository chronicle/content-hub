"""GraphQL queries and mutations for DSPM and Identity Resilience (IR) violations."""

from __future__ import annotations

DSPM_LIST_QUERY: str = """
query DataSecurityViolationsListQuery(
  $statuses: [PolicyViolationStatus!],
  $severities: [Severity!],
  $categories: [Category!],
  $sensitivityLevels: [SensitivityLevel!],
  $detectionDate: TimeRangeInput,
  $updateDate: TimeRangeInput,
  $first: Int,
  $after: String,
  $sortBy: PolicyViolationSortField,
  $sortOrder: SortOrder,
  $resourceMetadataFilter: ResourceMetadataFiltersInput
) {
  policyViolations(
    statuses: $statuses,
    policySeverities: $severities,
    policyCategories: $categories,
    sensitivityLevels: $sensitivityLevels,
    detectionDate: $detectionDate,
    updateDate: $updateDate,
    policyTypes: [POLICY_TYPE_DATAGOV],
    first: $first,
    after: $after,
    sortBy: $sortBy,
    sortOrder: $sortOrder,
    resourceMetadataFilter: $resourceMetadataFilter
  ) {
    count
    edges {
      node {
        policyViolationId
        status
        createdAt
        lastUpdatedAt
        violationSeverity
        policy { name policyCategory policySeverity }
        resourceId
        resourceMetadata {
          metadata {
            ... on CommonAssetMetadata { name objectType platform }
          }
        }
        details {
          ... on DataGovViolationDetails {
            snapshotId
            violatedHighRiskSensitiveHits
            violatedMediumRiskSensitiveHits
          }
        }
      }
    }
    pageInfo { endCursor hasNextPage }
  }
}
"""

DSPM_GET_QUERY: str = """
query DataSecurityViolationGetQuery($violationId: String!) {
  policyViolation(
    violationId: $violationId
    policyTypes: [POLICY_TYPE_DATAGOV]
  ) {
    policyViolationId
    status
    violationSeverity
    createdAt
    lastUpdatedAt
    resourceId
    policy {
      policyId
      name
      policyCategory
      policySeverity
      description
      containsAccessFilters
    }
    remediations {
      remediationId
      state
      remediationDetails {
        details {
          ticketNumber
          ticketUrl
        }
      }
    }
    details {
      ... on DataGovViolationDetails {
        snapshotId
        violatedSensitiveHits
        violatedHighRiskSensitiveHits
        violatedMediumRiskSensitiveHits
        violatedLowRiskSensitiveHits
        violatedNoRiskSensitiveHits
        dataCategories { id name totalViolatedHits }
        dataTypes { id name totalViolatedHits }
        mipLabels { id name totalViolatedHits }
        documentTypes { id name totalViolatedHits }
      }
    }
    resourceMetadata {
      metadata {
        ... on CommonAssetMetadata {
          name
          objectType
          platform
          physicalHost
          region
          isDeleted
          creationTime
          lastAccessTime
          snapshotTimestamp
          clusterInfo { clusterName clusterUuid }
          cloudAccountInfo { accountName }
        }
      }
    }
  }
}
"""

IR_GET_QUERY: str = """
query DataSecurityViolationGetQuery(
  $violationId: String!,
  $policyTypes: [PolicyType!]!
) {
  policyViolation(violationId: $violationId, policyTypes: $policyTypes) {
    policyViolationId
    status
    violationSeverity
    createdAt
    lastUpdatedAt
    resourceId
    resourceType
    policy {
      policyId
      name
      description
      policyCategory
      policySeverity
      policyType
      frameworks
      manualRemediationProcess
    }
    details {
      ... on IdentityViolationDetails { domainUniqueId principalUniqueId }
      ... on IdpViolationDetails { domainUniqueId }
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
        }
        ... on IdpMetadata {
          domainName
          domainUniqueId
          idpType
          rootDomainName
          rootDomainId
        }
      }
    }
  }
}
"""

UPDATE_VIOLATIONS_MUTATION: str = """
mutation UpdatePolicyViolationsMutation($input: BulkUpdatePolicyViolationsInput!) {
  bulkUpdatePolicyViolations(input: $input)
}
"""

DOWNLOAD_CSV_MUTATION: str = """
mutation DownloadFullSnapshotResultsCsvMutation(
  $snappableFid: String!,
  $snapshotFid: String!,
  $filters: DownloadResultsCsvFiltersInput
) {
  downloadSnapshotResultsCsv(
    snappableFid: $snappableFid,
    snapshotFid: $snapshotFid,
    downloadFilter: $filters
  ) {
    isSuccessful
  }
}
"""

DOWNLOAD_BAR_QUERY: str = """
query DownloadBarQuery {
  allUserFiles {
    downloads {
      externalId
      filename
      type
      state
      createdAt
    }
  }
}
"""

CREATE_REMEDIATION_MUTATION: str = """
mutation CreateViolationRemediationMutation($input: CreateViolationRemediationInput!) {
  createViolationRemediation(input: $input) {
    remediationId
  }
}
"""

FILE_LIST_QUERY: str = """
query DSPMViolationFileListQuery(
  $snappableFid: String!,
  $snapshotFid: String!,
  $first: Int!,
  $after: String,
  $sort: FileResultSortInput,
  $filters: ListFileResultFiltersInput,
  $timezone: String!
) {
  policyObj(snappableFid: $snappableFid, snapshotFid: $snapshotFid) {
    id: snapshotFid
    fileResultConnection(
      first: $first,
      after: $after,
      sort: $sort,
      filter: $filters,
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
          hits { totalHits violations violationsDelta totalHitsDelta }
          filesWithHits { totalHits violations }
          openAccessFilesWithHits { totalHits violations }
          staleFilesWithHits { totalHits violations }
          sensitiveHits {
            highRiskHits { totalHits violatedHits }
            mediumRiskHits { totalHits violatedHits }
            lowRiskHits { totalHits violatedHits }
            noRiskHits { totalHits violatedHits }
          }
          analyzerResults {
            hits { totalHits violations }
            analyzer { id name analyzerType }
          }
          openAccessType
          stalenessType
          numActivities
          numActivitiesDelta
          exposureSummary {
            exposureType
            fileCount { totalCount violatedCount }
          }
          dbEntityType
        }
      }
      pageInfo { startCursor endCursor hasNextPage hasPreviousPage }
      hasLatestData
    }
  }
}
"""

IR_LIST_QUERY: str = """
query IRViolationsListQuery(
  $policyTypes: [PolicyType!]!,
  $statuses: [PolicyViolationStatus!],
  $severities: [Severity!],
  $categories: [Category!],
  $detectionDate: TimeRangeInput,
  $updateDate: TimeRangeInput,
  $first: Int,
  $after: String,
  $sortBy: PolicyViolationSortField,
  $sortOrder: SortOrder,
  $resourceMetadataFilter: ResourceMetadataFiltersInput
) {
  policyViolations(
    policyTypes: $policyTypes,
    statuses: $statuses,
    policySeverities: $severities,
    policyCategories: $categories,
    detectionDate: $detectionDate,
    updateDate: $updateDate,
    first: $first,
    after: $after,
    sortBy: $sortBy,
    sortOrder: $sortOrder,
    resourceMetadataFilter: $resourceMetadataFilter
  ) {
    count
    edges {
      node {
        policyViolationId
        violationSeverity
        status
        createdAt
        lastUpdatedAt
        resourceId
        resourceType
        policy {
          policyId
          name
          description
          policyCategory
          policySeverity
          policyType
          frameworks
          manualRemediationProcess
        }
        details {
          ... on IdentityViolationDetails { domainUniqueId }
          ... on IdpViolationDetails { domainUniqueId }
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
            }
            ... on IdpMetadata {
              domainName
              domainUniqueId
              idpType
              rootDomainName
              rootDomainId
            }
          }
        }
      }
    }
    pageInfo { startCursor endCursor hasNextPage hasPreviousPage }
  }
}
"""
