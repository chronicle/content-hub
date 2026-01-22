from __future__ import annotations

TEST_CONNECTIVITY_QUERY = """query GoogleSecOpsTestConnectivityQuery {
  deploymentVersion
}"""

START_TURBO_THREAT_HUNT_MUTATION = (
    """mutation GoogleSecOpsStartThreatHunt("""
    """$input: StartTurboThreatHuntInput!) {"""
    """startTurboThreatHunt(input: $input) {
    huntId
    __typename
  }
}"""
)

START_BULK_THREAT_HUNT_MUTATION = (
    """mutation GoogleSecOpsStartBulkThreatHuntMutation("""
    """$input: StartThreatHuntV2Input!) {"""
    """startBulkThreatHunt(input: $input) {
    hunts {
      huntId
      huntName
      config {
        huntType
        clusterUuids
        objectFids
        __typename
      }
      status
      __typename
    }
    __typename
  }
}"""
)

THREAT_HUNT_DETAILS_V2_QUERY = """query GoogleSecOpsThreatHuntDetailsV2Query($huntId: String!) {
  threatHuntObjectMetrics(huntId: $huntId) {
    totalObjectsScanned
    totalAffectedObjects
    totalUnaffectedObjects
    totalObjectsUnscannable
    unaffectedObjectsFromDb
    cleanRecoverableObjectLimit
    __typename
  }
  threatHuntDetailV2(huntId: $huntId) {
    totalObjectFids
    startTime
    endTime
    status
    totalMatchedSnapshots
    totalScannedSnapshots
    totalUniqueFileMatches
    clusters{
      id
      name
      type
      __typename
    }
    baseConfig {
      name
      notes
      maxMatchesPerSnapshot
      threatHuntType
      ioc {
        iocList {
          indicatorsOfCompromise {
            iocKind
            iocValue
            __typename
          }
          __typename
        }
        __typename
      }
      snapshotScanLimit {
        scanLimit {
          scanConfig {
            maxSnapshotsPerObject
            startTime
            endTime
            __typename
          }
          objectSnapshotConfig {
            objectFid
            snapshotFid
            __typename
          }
          __typename
        }
        __typename
      }
      fileScanCriteria {
        fileSizeLimits {
          maximumSizeInBytes
          minimumSizeInBytes
          __typename
        }
        fileTimeLimits {
          earliestCreationTime
          earliestModificationTime
          latestCreationTime
          latestModificationTime
          __typename
        }
        pathFilter {
          inclusions
          exclusions
          exemptions
          __typename
        }
        __typename
      }
      __typename
    }
    __typename
  }
}"""

OBJECT_SNAPSHOTS_QUERY = (
    """query GoogleSecOpsObjectSnapshot($snappableId: String!, $first: Int, """
    """$after: String, $snapshotFilter: [SnapshotQueryFilterInput!], """
    """$sortBy: SnapshotQuerySortByField, $sortOrder: SortOrder, """
    """$timeRange: TimeRangeInput) {"""
    """snapshotsListConnection: snapshotOfASnappableConnection(
    workloadId: $snappableId
    first: $first
    after: $after
    snapshotFilter: $snapshotFilter
    sortBy: $sortBy
    sortOrder: $sortOrder
    timeRange: $timeRange
  ) {
    edges {
      node {
        id
        date
        expirationDate
        isOnDemandSnapshot
        ... on CdmSnapshot {
          cdmVersion
          isDownloadedSnapshot
          cluster {
            id
            name
            version
            status
          }
          pendingSnapshotDeletion {
            id: snapshotFid
            status
          }
          slaDomain {
            name
            ... on ClusterSlaDomain {
              fid
              cluster {
                id
                name
              }
            }
            ... on GlobalSlaReply {
              id
            }
          }
          pendingSla {
            id
            name
          }
          snapshotRetentionInfo {
            archivalInfos {
              name
              isExpirationDateCalculated
              expirationTime
            }
            localInfo {
              name
              isExpirationDateCalculated
              expirationTime
            }
            replicationInfos {
              name
              isExpirationDateCalculated
              expirationTime
            }
          }
          sapHanaAppMetadata {
            backupId
            backupPrefix
            snapshotType
            files {
              backupFileSizeInBytes
            }
          }
          legalHoldInfo {
            shouldHoldInPlace
          }
        }
        ... on PolarisSnapshot {
          isDownloadedSnapshot
          isReplica
          isArchivalCopy
          slaDomain {
            name
            ... on ClusterSlaDomain {
              fid
              cluster {
                id
                name
              }
            }
            ... on GlobalSlaReply {
              id
            }
          }
        }
      }
    }
    pageInfo {
      endCursor
      hasNextPage
    }
  }
}"""
)

SONAR_FILE_CONTEXTS_QUERY = (
    """query GoogleSecOpsCrawlsFileListQuery($snappableFid: String!, """
    """$snapshotFid: String!, $first: Int!, $after: String, """
    """$filters: ListFileResultFiltersInput, $sort: FileResultSortInput, """
    """$timezone: String!) {"""
    """policyObj(snappableFid: $snappableFid, snapshotFid: $snapshotFid) {
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
          ...DiscoveryFileFragment
          __typename
        }
        __typename
      }
      pageInfo {
        endCursor
        hasNextPage
        __typename
      }
      __typename
    }
    __typename
  }
}

fragment DiscoveryFileFragment on FileResult {
  nativePath
  stdPath
  filename
  mode
  size
  lastAccessTime
  lastModifiedTime
  directory
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
  analyzerGroupResults {
    ...AnalyzerGroupResultFragment
    __typename
  }
  sensitiveFiles {
    highRiskFileCount {
      totalCount
      violatedCount
      __typename
    }
    mediumRiskFileCount {
      totalCount
      violatedCount
      __typename
    }
    lowRiskFileCount {
      totalCount
      violatedCount
      __typename
    }
    __typename
  }
  openAccessType
  stalenessType
  numActivities
  numActivitiesDelta
  __typename
}

fragment AnalyzerGroupResultFragment on AnalyzerGroupResult {
  analyzerGroup {
    groupType
    id
    name
    __typename
  }
  analyzerResults {
    hits {
      totalHits
      violations
      __typename
    }
    analyzer {
      id
      name
      analyzerType
      __typename
    }
    __typename
  }
  hits {
    totalHits
    violations
    violationsDelta
    totalHitsDelta
    __typename
  }
  __typename
}"""
)

LIST_EVENTS_QUERY = (
    """query GoogleSecOpsEventSeriesList($after: String, """
    """$filters: ActivitySeriesFilter, $first: Int, """
    """$sortBy: ActivitySeriesSortField, $sortOrder: SortOrder) {"""
    """activitySeriesConnection(
    after: $after
    first: $first
    filters: $filters
    sortBy: $sortBy
    sortOrder: $sortOrder
  ) {
    edges {
      node {
        id
        fid
        activitySeriesId
        startTime
        lastUpdated
        lastActivityType
        lastActivityStatus
        location
        objectName
        objectId
        objectType
        severity
        progress
        cluster {
          id
          name
        }
        activityConnection {
          nodes {
            id
            message
            severity
            time
          }
        }
      }
    }
    pageInfo {
      endCursor
      hasNextPage
      hasPreviousPage
    }
  }
}"""
)

CDM_CLUSTER_LOCATION_QUERY = (
    """query GoogleSecOpsCDMClusterLocationQuery("""
    """$filter: ClusterFilterInput) {"""
    """clusterConnection(filter: $filter) {
      nodes{
         geoLocation{
            address
         }
      }
   }
}"""
)

CDM_CLUSTER_CONNECTION_STATE_QUERY = (
    """query GoogleSecOpsCDMClusterConnectionStateQuery("""
    """$filter: ClusterFilterInput) {"""
    """clusterConnection(filter: $filter) {
    nodes{
      state {
        connectedState
      }
    }
  }
}"""
)

SONAR_POLICY_OBJECTS_LIST_QUERY = (
    """query GoogleSecOpsSonarSensitiveHitsObjectList("""
    """$day: String!, $timezone: String!) {"""
    """policyObjs(day: $day, timezone: $timezone) {
    edges {
      node {
        snapshotFid
        snapshotTimestamp
        objectStatus {
          latestSnapshotResult {
            snapshotTime
            snapshotFid
          }
        }
        snappable {
          name
          id
        }
      }
    }
  }
}"""
)

SONAR_OBJECT_DETAIL_QUERY = (
    """query GoogleSecOpsObjectDetailQuery($snappableFid: String!, """
    """$snapshotFid: String!) {"""
    """policyObj(snappableFid: $snappableFid, snapshotFid: $snapshotFid) {
    id
    snapshotFid
    snappable {
      id
      name
    }
    rootFileResult {
      hits {
        totalHits
      }
      analyzerGroupResults {
        analyzerGroup {
          name
        }
        analyzerResults {
          hits {
            totalHits
          }
          analyzer {
            name
          }
        }
        hits {
          totalHits
        }
      }
      filesWithHits {
        totalHits
      }
      openAccessFiles {
        totalHits
      }
      openAccessFolders {
        totalHits
      }
      openAccessFilesWithHits {
        totalHits
      }
      staleFiles {
        totalHits
      }
      staleFilesWithHits {
        totalHits
      }
      openAccessStaleFiles {
        totalHits
      }
    }
  }
}"""
)
