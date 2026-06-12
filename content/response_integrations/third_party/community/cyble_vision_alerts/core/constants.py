# ─────────────────────────────────────────────────────────────────────────────
# Cyble Vision Integration — Constants
# ─────────────────────────────────────────────────────────────────────────────

from __future__ import annotations
INTEGRATION_NAME = "CybleVisionAlerts"
INTEGRATION_DISPLAY_NAME = "Cyble Vision Alerts"
INTEGRATION_VERSION = "1.0.0"

# ── Connector / Action parameter names (match .def files) ────────────────────
PARAM_API_KEY       = "API Key"
PARAM_BASE_URL      = "Base URL"
PARAM_VERIFY_SSL    = "Verify SSL"
PARAM_TIMEOUT       = "Request Timeout (seconds)"
PARAM_MAX_PER_CYCLE = "Max Alerts Per Service Per Cycle"
PARAM_SERVICES      = "Services Filter (comma-separated)"
PARAM_HOURS_BACK    = "Hours Back (initial fetch)"
PARAM_ENVIRONMENT   = "Environment Field Name"

# ── Defaults ─────────────────────────────────────────────────────────────────
DEFAULT_BASE_URL      = "https://bifrost.cyble.ai/engine/api/v1/y/tpi"
DEFAULT_TIMEOUT       = 30
DEFAULT_MAX_PER_CYCLE = 500
DEFAULT_PAGE_SIZE     = 100          # `take` per paginated request
DEFAULT_HOURS_BACK    = 24
MAX_RETRIES           = 3
RETRY_BACKOFF_BASE    = 2            # seconds; jittered exponential
RETRY_STATUS_CODES    = {429, 500, 502, 503, 504}

# ── API Endpoints (relative to base_url) ─────────────────────────────────────
ENDPOINT_SERVICES = "/splunk/alerts/services"
ENDPOINT_ALERTS   = "/splunk/alerts"
ENDPOINT_UPDATE   = "/splunk/alerts"

# ── Cyble alert statuses ──────────────────────────────────────────────────────
CYBLE_STATUSES = [
    "UNREVIEWED",
    "VIEWED",
    "CONFIRMED_INCIDENT",
    "UNDER_REVIEW",
    "INFORMATIONAL",
    "RESOLVED",
]

# Statuses to pull by default (excludes RESOLVED to avoid noise)
DEFAULT_FETCH_STATUSES = [
    "UNREVIEWED",
    "VIEWED",
    "CONFIRMED_INCIDENT",
    "UNDER_REVIEW",
    "INFORMATIONAL",
]

# ── Severity mappings ─────────────────────────────────────────────────────────
CYBLE_TO_SECOPS_SEVERITY = {
    "CRITICAL": -1,   # SecOps: CRITICAL
    "HIGH":     2,    # SecOps: HIGH
    "MEDIUM":   1,    # SecOps: MEDIUM
    "LOW":      0,    # SecOps: LOW
    "INFO":     0,    # SecOps: LOW (informational → low)
}

SECOPS_TO_CYBLE_SEVERITY = {
    "CRITICAL": "CRITICAL",
    "HIGH":     "HIGH",
    "MEDIUM":   "MEDIUM",
    "LOW":      "LOW",
}

# SecOps integer → Cyble string (for update action inputs)
SECOPS_INT_TO_CYBLE_SEVERITY = {
    -1: "CRITICAL",
    2:  "HIGH",
    1:  "MEDIUM",
    0:  "LOW",
}

# ── Status mappings ───────────────────────────────────────────────────────────
CYBLE_TO_SECOPS_STATUS = {
    "UNREVIEWED":         "OPEN",
    "VIEWED":             "IN_PROGRESS",
    "CONFIRMED_INCIDENT": "IN_PROGRESS",
    "UNDER_REVIEW":       "IN_PROGRESS",
    "INFORMATIONAL":      "OPEN",
    "RESOLVED":           "CLOSED",
}

SECOPS_TO_CYBLE_STATUS = {
    "OPEN":         "UNREVIEWED",
    "IN_PROGRESS":  "UNDER_REVIEW",
    "CLOSED":       "RESOLVED",
    "FALSE_POSITIVE": "INFORMATIONAL",
}

# ─────────────────────────────────────────────────────────────────────────────
# Custom field names on SecOps alerts.
#
# These string values appear verbatim as Custom Field names in the SOAR UI.
# They are intentionally vendor-agnostic (no "Cyble" prefix) so the same
# integration can be re-skinned for other customers without renaming every
# Custom Field in their SOAR tenant.
#
# The mapper guarantees every COMMON_FIELDS entry is emitted on every alert —
# even when the raw payload has a null/missing value — so analysts see a
# consistent set of columns regardless of service or completeness of the
# upstream record. Service-specific extras (ssl_expiry, github, stealer_logs,
# …) are added on top of the common set by per-service branches.
# ─────────────────────────────────────────────────────────────────────────────

# ── Common alert fields (always emitted, in every service's output) ──────────
FIELD_ALERT_ID                = "AlertId"
FIELD_DATA_ID                 = "DataId"
FIELD_SERVICE                 = "Service"
FIELD_KEYWORD                 = "Keyword"
FIELD_BUCKET                  = "Bucket"
FIELD_BUCKET_ID               = "BucketId"
FIELD_ENTITY_ID               = "EntityId"
FIELD_ENTITY_TYPE             = "EntityType"
FIELD_COMPANY_ID              = "CompanyId"
FIELD_DESCRIPTION             = "Description"
FIELD_STATUS                  = "Status"
FIELD_SEVERITY                = "Severity"
FIELD_USER_SEVERITY           = "UserSeverity"
FIELD_RISK_SCORE              = "RiskScore"
FIELD_TAGS                    = "Tags"
FIELD_ASSIGNEE_ID             = "AssigneeId"
FIELD_ASSIGNMENT_DATE         = "AssignmentDate"
FIELD_ARCHIVE_DATE            = "ArchiveDate"
FIELD_UPDATED_BY_ID           = "UpdatedById"
FIELD_CREATED_BY              = "CreatedBy"
FIELD_CREATED_AT              = "CreatedAt"
FIELD_UPDATED_AT              = "UpdatedAt"
FIELD_DELETED_AT              = "DeletedAt"
FIELD_TRUE_POSITIVE           = "TruePositive"
FIELD_LLM_PROCESSED           = "LlmProcessed"
FIELD_LLM_EXPLANATION         = "LlmExplanation"
FIELD_PROCESSED_AGENTIC_AI    = "ProcessedByAgenticAi"
FIELD_AGENTIC_AI_STATUS       = "AgenticAiProcessStatus"
FIELD_WORKFLOW_ID             = "WorkflowId"
FIELD_LAST_SYNC_AT            = "LastSyncAt"

# COMMON_FIELDS — single source of truth driving the always-emit loop in
# CybleAlertMapper._extract_common_fields(). Order matters: the iteration order
# determines the on-disk field-emission order, which is what SOAR uses to
# render the event blade left-to-right.
#   (custom_field_name, raw_alert_source_key)
COMMON_FIELDS = [
    (FIELD_ALERT_ID,             "id"),
    (FIELD_DATA_ID,              "data_id"),
    (FIELD_SERVICE,              "service"),
    (FIELD_KEYWORD,              "keyword_name"),
    (FIELD_BUCKET,               "bucket_name"),
    (FIELD_BUCKET_ID,            "bucket_id"),
    (FIELD_ENTITY_ID,            "entity_id"),
    (FIELD_ENTITY_TYPE,          "entity_type"),
    (FIELD_COMPANY_ID,           "company_id"),
    (FIELD_DESCRIPTION,          "description"),
    (FIELD_STATUS,               "status"),
    (FIELD_SEVERITY,             "severity"),
    (FIELD_USER_SEVERITY,        "user_severity"),
    (FIELD_RISK_SCORE,           "risk_score"),
    (FIELD_TAGS,                 "tags"),
    (FIELD_ASSIGNEE_ID,          "assignee_id"),
    (FIELD_ASSIGNMENT_DATE,      "assignment_date"),
    (FIELD_ARCHIVE_DATE,         "archive_date"),
    (FIELD_UPDATED_BY_ID,        "updated_by_id"),
    (FIELD_CREATED_BY,           "created_by"),
    (FIELD_CREATED_AT,           "created_at"),
    (FIELD_UPDATED_AT,           "updated_at"),
    (FIELD_DELETED_AT,           "deleted_at"),
    (FIELD_TRUE_POSITIVE,        "true_positive"),
    (FIELD_LLM_PROCESSED,        "llm_processed"),
    (FIELD_LLM_EXPLANATION,      "llm_explanation"),
    (FIELD_PROCESSED_AGENTIC_AI, "processed_by_agentic_ai"),
    (FIELD_AGENTIC_AI_STATUS,    "agentic_ai_process_status"),
    (FIELD_WORKFLOW_ID,          "workflow_id"),
]

# ── Service-specific custom fields ───────────────────────────────────────────
# Each block groups fields that are populated for one (or a small set of)
# service(s). All of these are emitted by their respective branches in
# CybleAlertMapper._extract_service_fields(); when the raw payload has no
# value the field is emitted as an empty string so the column is consistent.

# Code-analysis services shared (github, bit_bucket, docker, postman)
FIELD_REPO                  = "Repository"
FIELD_FILENAME              = "Filename"
FIELD_OWNER                 = "Owner"

# Asset-discovery shared (assets, ssl_expiry, …)
FIELD_ASSET                 = "Asset"
FIELD_LAST_DETECTED_AT      = "LastDetectedAt"
FIELD_KEYWORD_ID            = "KeywordId"

# ssl_expiry  (Asset SSL Expiry)
FIELD_EXPIRY_DATE           = "ExpiryDate"
FIELD_DAYS_TO_EXPIRY        = "DaysToExpiry"
FIELD_SSL_PORT              = "SslPort"
FIELD_SSL_IS_VALID          = "SslIsValid"
FIELD_SSL_ISSUED            = "SslIssuedAt"
FIELD_SSL_HASH              = "SslHash"
FIELD_SSL_AGE_DAYS          = "SslAgeDays"
FIELD_SSL_DETAIL            = "SslDetail"
FIELD_SSL_VERSION           = "SslVersion"
FIELD_SSL_TITLE             = "SslTitle"
FIELD_COUNTRY_CODE          = "CountryCode"

# github  (Code Analysis - Github)
FIELD_FILE_URL              = "FileUrl"
FIELD_FILE_PATH             = "FilePath"
FIELD_GIT_URL               = "GitUrl"
FIELD_FILE_API_URL          = "FileApiUrl"
FIELD_COMMIT_SHA            = "CommitSha"
FIELD_MATCH_SCORE           = "MatchScore"
FIELD_REPO_URL              = "RepoUrl"
FIELD_REPO_DESCRIPTION      = "RepoDescription"
FIELD_REPO_FULL_NAME        = "RepoFullName"
FIELD_REPO_LANGUAGE         = "RepoLanguage"
FIELD_REPO_PRIVATE          = "RepoPrivate"
FIELD_REPO_STARS            = "RepoStars"
FIELD_REPO_FORKS            = "RepoForks"
FIELD_REPO_OWNER_LOGIN      = "RepoOwnerLogin"
FIELD_MATCH_FRAGMENT        = "MatchFragment"
FIELD_MATCHED_TEXT          = "MatchedText"

# Generic fields reused by multiple services
FIELD_URL                   = "Url"
FIELD_USERNAME              = "Username"
FIELD_DOMAIN                = "Domain"

# cloud_storage  (Cloud Storage)
# `Bucket` / `BucketId` (from COMMON_FIELDS) are the Cyble *bucket-of-alerts*
# identifiers, not the cloud-storage bucket. These constants are the actual
# S3/GCS/Azure bucket details and never overlap with the common ones.
FIELD_STORAGE_BUCKET          = "StorageBucket"
FIELD_STORAGE_BUCKET_ID       = "StorageBucketId"
FIELD_STORAGE_OBJECT_ID       = "StorageObjectId"

# Title-group services (postman, docker, vulnerability, web_applications,
# physical_threats, darkweb_data_breaches, …) — `title` becomes the second
# half of the case header. It's also emitted as a Custom Field so analysts
# can filter/group by it without parsing the case name.
FIELD_TITLE                   = "Title"

# postman  (Code Analysis - Postman) — engagement & metadata
FIELD_DEVELOPER_URL           = "DeveloperUrl"
FIELD_IS_PUBLIC               = "IsPublic"
FIELD_CATEGORY                = "Category"
FIELD_VIEWS                   = "Views"
FIELD_FORKS                   = "Forks"
FIELD_WATCHERS                = "Watchers"
FIELD_APIS_COUNT              = "Apis"
FIELD_COLLECTIONS_COUNT       = "Collections"
FIELD_WORKSPACES_COUNT        = "Workspaces"
FIELD_ICON_URL                = "IconUrl"
FIELD_POSTMAN_KEY             = "PostmanKey"
FIELD_SOURCE_NAME             = "SourceName"
FIELD_SCRAP_TIME              = "ScrapTime"
FIELD_LAST_UPDATED_AT         = "LastUpdatedAt"
FIELD_METADATA                = "Metadata"

# ── Cross-service reusable fields ────────────────────────────────────────────
# These represent concepts that appear under different names across services
# (e.g. "content", "details", "extension"). Defined once here, used by many.
FIELD_CONTENT                 = "Content"
FIELD_DETAILS                 = "Details"
FIELD_EXTENSION               = "Extension"
FIELD_UPDATED_FIELDS          = "UpdatedFields"
FIELD_S3_KEY                  = "S3Key"
FIELD_TYPE                    = "Type"
FIELD_TIMESTAMP               = "Timestamp"
FIELD_VERSION                 = "Version"
FIELD_HOST                    = "Host"
FIELD_PORT                    = "Port"
FIELD_PROTOCOL                = "Protocol"
FIELD_SOURCE                  = "Source"
FIELD_CVE                     = "Cve"
FIELD_AUTHOR                  = "Author"
FIELD_CONTENT_ADDED_ON        = "ContentAddedOn"
FIELD_INDUSTRY                = "Industry"
FIELD_HASH                    = "Hash"
FIELD_VICTIM                  = "Victim"
FIELD_THREAT_ACTOR            = "ThreatActor"
FIELD_UPDATED_DATE            = "UpdatedDate"
FIELD_CREATED_DATE            = "CreatedDate"
FIELD_SENTIMENT               = "Sentiment"
FIELD_NAME                    = "Name"
FIELD_LANGUAGE                = "Language"
FIELD_MESSAGE                 = "Message"
FIELD_SCORE                   = "Score"

# compromised_endpoints_cookies  (Compromised Cookies)
FIELD_COOKIE_DATA             = "CookieData"
FIELD_IS_UPDATED_ES           = "IsUpdatedEs"
FIELD_SOURCE_ID               = "SourceId"

# compromised_files  (Compromised Files)
FIELD_FILE_OBJ_PATH           = "FileObjPath"
FIELD_LOG_NAME                = "LogName"
FIELD_LOG_OBJ_PATH            = "LogObjPath"
FIELD_RELATIVE_PATH           = "RelativePath"

# advisory  (Cyble Research Labs Advisory)
FIELD_ADVISORY_ID             = "AdvisoryId"

# darkweb_marketplaces  (Darkweb Marketplaces)
FIELD_MARKETPLACE             = "Marketplace"
FIELD_CONTENT_UPDATED_ON      = "ContentUpdatedOn"
FIELD_VENDOR                  = "Vendor"
FIELD_PRICE                   = "Price"
FIELD_DATA_SIZE               = "DataSize"
FIELD_REGION                  = "Region"
FIELD_INFO                    = "Info"
FIELD_OUTLOOK                 = "Outlook"
FIELD_BROWSER                 = "Browser"
FIELD_OS                      = "Os"
FIELD_USER_AGENT              = "UserAgent"
FIELD_IP                      = "Ip"
FIELD_INSTALLED_DATE          = "InstalledDate"
FIELD_COOKIES                 = "Cookies"
FIELD_COOKIES_DATE            = "CookiesDate"
FIELD_COMPANY_LEAKED          = "CompanyLeaked"
FIELD_CONFIG_UPDATE           = "ConfigUpdate"
FIELD_DATA_STRUCT             = "DataStruct"
FIELD_LINKS                   = "Links"
FIELD_EVENT_DATE              = "EventDate"
FIELD_EVENT_DATE_TIMESTAMP    = "EventDateTimestamp"
# Bank / Card details (marketplace sales of compromised cards)
FIELD_BANK_BIN                = "BankBin"
FIELD_BANK_COUNTRY            = "BankCountry"
FIELD_BANK_PHONE              = "BankPhone"
FIELD_BANK_REAL_NAME          = "BankRealName"
FIELD_BANK_REF_NAME           = "BankRefName"
FIELD_BANK_SITE               = "BankSite"
FIELD_CARD_BRAND              = "CardBrand"
FIELD_CARD_NUMBER             = "CardNumber"
FIELD_CARD_TYPE               = "CardType"
FIELD_CARD_CVR                = "CardCvr"
FIELD_CARD_CVV                = "CardCvv"
FIELD_CARD_EXPIRY             = "CardExpiry"
FIELD_CARD_LEVEL              = "CardLevel"

# darkweb_data_breaches  (Data Exposures)
FIELD_BREACH_SOURCE           = "BreachSource"
FIELD_BREACH_DATE             = "BreachDate"

# domain_watchlist  (Domain Watchlist)
FIELD_NEW_DNS_RECORD          = "NewDnsRecord"
FIELD_OLD_DNS_RECORD          = "OldDnsRecord"
FIELD_SCREENSHOT_OBJECT_KEY   = "ScreenshotObjectKey"
FIELD_SCREENSHOT_TIMESTAMP    = "ScreenshotTimestamp"

# hacktivism  (Hacktivism)
FIELD_CHANNEL_NAME            = "ChannelName"
FIELD_ATTACKER                = "Attacker"
FIELD_MIRROR                  = "Mirror"
FIELD_SERVER                  = "Server"
FIELD_SOURCE_WEBSITE          = "SourceWebsite"
FIELD_TEAM                    = "Team"
FIELD_UNIQUE_KEY              = "UniqueKey"

# i2p  (I2P Links)
FIELD_SEARCH_ENGINE           = "SearchEngine"
FIELD_SEARCH_KEYWORD          = "SearchKeyword"

# ip_risk_score  (IP Risk Score)
FIELD_OLD_RISK_SCORE          = "OldRiskScore"
FIELD_NEW_RISK_SCORE          = "NewRiskScore"

# vulnerability  (Issues Catalog)
FIELD_CONFIDENCE              = "Confidence"
FIELD_FIRST_SEEN_ON           = "FirstSeenOn"
FIELD_LAST_SEEN_ON            = "LastSeenOn"
FIELD_VULNERABILITY_ID        = "VulnerabilityId"
FIELD_VULNERABILITY_TYPE      = "VulnerabilityType"

# new_port  (New Ports)
FIELD_LAST_DETECTED_AT        = "LastDetectedAt"

# flash_report  (News Flash)
FIELD_FOR_COMPANY             = "ForCompany"
FIELD_REPORT_ID               = "ReportId"

# ot_ics  (OT/ICS)
FIELD_ASN                     = "Asn"
FIELD_SOURCE_IP               = "SourceIp"
FIELD_DATA_TYPE               = "DataType"
FIELD_DEST_PORT               = "DestPort"
FIELD_IP_REPUTATION           = "IpReputation"

# pastebin  (Pastesite)
FIELD_PASTE_TYPE              = "PasteType"

# phishing  (Phishing Monitoring) — rich nested payload
FIELD_BRAND                   = "Brand"
FIELD_BRAND_INDUSTRY          = "BrandIndustry"
FIELD_BRAND_WEBSITE           = "BrandWebsite"
FIELD_AWS_OBJECT_NAME         = "AwsObjectName"
FIELD_CONTENT_MATCH           = "ContentMatch"
FIELD_DETECTED_AT             = "DetectedAt"
FIELD_DO_OBJECT_NAME          = "DoObjectName"
FIELD_DOMAIN_RANKING          = "DomainRanking"
FIELD_HOST_NAME               = "HostName"
FIELD_IS_DELETED              = "IsDeleted"
FIELD_IS_LIVE                 = "IsLive"
FIELD_IS_TAKEDOWN             = "IsTakedown"
FIELD_LAST_LIVE_ON            = "LastLiveOn"
FIELD_LOGO_MATCH              = "LogoMatch"
FIELD_PHISHING_KEYWORD_NAME   = "PhishingKeywordName"
FIELD_PHISHING_STATUS         = "PhishingStatus"
FIELD_SCREENSHOT_URL          = "ScreenshotUrl"
FIELD_STATUS_CODE             = "StatusCode"
FIELD_WATERMARKING_DATA       = "WatermarkingData"

# product_vulnerability  (Vulnerability Intelligence)
FIELD_COMPANY                 = "Company"
FIELD_PRODUCT                 = "Product"
FIELD_LAST_MODIFIED_DATE      = "LastModifiedDate"
FIELD_PUBLISHED_DATE          = "PublishedDate"
FIELD_NEW_CVE_DETAILS         = "NewCveDetails"
FIELD_OLD_CVE_DETAILS         = "OldCveDetails"
FIELD_SEVERITY_DATA           = "SeverityData"
FIELD_SOFTWARE_DETAILS        = "SoftwareDetails"

# ransomware_updates  (Ransomware Updates)
FIELD_ADDED_BY                = "AddedBy"
FIELD_IS_PUBLISHED            = "IsPublished"
FIELD_SCREENSHOTS_PATH        = "ScreenshotsPath"
FIELD_TA_LINK                 = "TaLink"
FIELD_TM_LINK                 = "TmLink"
FIELD_UPDATED_BY              = "UpdatedBy"

# darkweb_ransomware  (Darkweb Ransomware)
FIELD_DOCUMENT_CREATED_YEAR   = "DocumentCreatedYear"
FIELD_ORIGINAL_FILENAME       = "OriginalFilename"

# social_media_monitoring  (Brand Mentions) — rich nested payload
FIELD_CONFIDENCE_SCORE        = "ConfidenceScore"
FIELD_FINDING_ID              = "FindingId"
FIELD_LOCATION                = "Location"
FIELD_WEIGHTAGE               = "Weightage"
FIELD_FOLLOWERS               = "Followers"
FIELD_FOLLOWING               = "Following"
FIELD_IS_VERIFIED             = "IsVerified"
FIELD_CREATOR_URL             = "CreatorUrl"
FIELD_CREATOR_TYPE            = "CreatorType"
FIELD_HASHTAGS                = "Hashtags"
FIELD_POSTED_AT               = "PostedAt"
FIELD_MEDIA                   = "Media"
FIELD_EXCERPTS                = "Excerpts"
FIELD_EXTRACTED_DOMAINS       = "ExtractedDomains"
FIELD_EXTRACTED_URLS          = "ExtractedUrls"
FIELD_EXTRACTED_SUBDOMAINS    = "ExtractedSubdomains"
FIELD_EXTRACTED_IPS           = "ExtractedIps"
FIELD_SUSPICIOUS_URLS         = "SuspiciousUrls"
FIELD_MENTIONS                = "Mentions"
FIELD_RULES                   = "Rules"

# subdomains  (Subdomains)
FIELD_SUBDOMAIN               = "Subdomain"

# suspicious_domains  (Suspicious Domains)
FIELD_REGISTRATION_DATE       = "RegistrationDate"
FIELD_DETECTED_TECHNOLOGIES   = "DetectedTechnologies"
FIELD_DNS_RECORDS             = "DnsRecords"
FIELD_FUZZER                  = "Fuzzer"
FIELD_LAST_LIVE_CHECK         = "LastLiveCheck"
FIELD_RAW_REGISTRATION_DATE   = "RawRegistrationDate"
FIELD_DETECTION_SERVICE       = "DetectionService"
FIELD_WHOIS_ENRICHED          = "WhoisEnriched"
FIELD_WHOIS_ENRICHED_TRIES    = "WhoisEnrichedTries"

# telegram_mentions  (Telegram Channels)
FIELD_CHAT_TITLE              = "ChatTitle"
FIELD_CHAT_ID                 = "ChatId"
FIELD_USER_ID                 = "UserId"

# web_applications  (Web Application Discovery)
FIELD_APP_ID                  = "AppId"
FIELD_FAVICON                 = "Favicon"
FIELD_IS_BEHIND_WAF           = "IsBehindWaf"
FIELD_IS_CDN                  = "IsCdn"
FIELD_IS_VHOST                = "IsVhost"
FIELD_PATH                    = "Path"

# physical_threats  (Physical Threats)
FIELD_PIN_NAME                = "PinName"
FIELD_CITY                    = "City"
FIELD_THREAT_TYPE             = "ThreatType"
FIELD_ADDRESS                 = "Address"
FIELD_BASE_SOURCE             = "BaseSource"
FIELD_COMPANY_UUID            = "CompanyUuid"
FIELD_LATITUDE                = "Latitude"
FIELD_LLM_SEVERITY_DESCRIPTION = "LlmSeverityDescription"
FIELD_LOCATION_NAME           = "LocationName"
FIELD_LOCATION_TYPE           = "LocationType"
FIELD_LONGITUDE               = "Longitude"
FIELD_PIN_ID                  = "PinId"
FIELD_SOURCE_COUNT            = "SourceCount"
FIELD_SOURCES                 = "Sources"
FIELD_STATE                   = "State"

# leaked_credentials  (Leaked Credentials)
FIELD_PASSWORD                = "Password"

# osint  (OSINT)
FIELD_UPLOADED_AT             = "UploadedAt"
FIELD_MENTION_DATE            = "MentionDate"
FIELD_REACH                   = "Reach"
FIELD_STARRED                 = "Starred"

# malicious_ads  (Malicious Ads) — shares most fields with phishing
FIELD_IP_DETAIL               = "IpDetail"
FIELD_SPONSORED               = "Sponsored"
FIELD_URLS                    = "Urls"

# bit_bucket  (Code Analysis - BitBucket) — list of secret-scan findings
FIELD_FINDINGS_COUNT          = "FindingsCount"
FIELD_DETECTOR_NAME           = "DetectorName"
FIELD_VERIFIED                = "Verified"
FIELD_RAW_SECRET              = "RawSecret"
FIELD_REPOSITORY              = "Repository"
FIELD_FILES                   = "Files"
FIELD_COMMITS                 = "Commits"
FIELD_COMMIT_LINKS            = "CommitLinks"
FIELD_AUTHORS                 = "Authors"
FIELD_ROTATION_GUIDE          = "RotationGuide"
FIELD_FINDINGS                = "Findings"

# docker  (Code Analysis - Docker Hub) — additions beyond postman's shared set
FIELD_DOWNLOADS               = "Downloads"
FIELD_STARS                   = "Stars"
FIELD_TRUSTED_CONTENT         = "TrustedContent"
FIELD_IMAGE_TAGS              = "ImageTags"

# defacement_content / defacement_keyword  (Defacement Content / Keyword)
FIELD_KEYWORDS                = "Keywords"
FIELD_MATCHED_KEYWORD         = "MatchedKeyword"
FIELD_WEBSITE_ADDED_ON        = "WebsiteAddedOn"
FIELD_WEBSITE_ID              = "WebsiteId"
FIELD_FREQUENCY               = "Frequency"

# discord  (Discord)
FIELD_SERVER_NAME             = "ServerName"
FIELD_AUTHOR_ID               = "AuthorId"
FIELD_AVATAR                  = "Avatar"
FIELD_AUTHOR_DATA             = "AuthorData"
FIELD_ATTACHMENTS             = "Attachments"
FIELD_EMBEDS                  = "Embeds"

# iocs  (IoCs)
FIELD_IOC                     = "Ioc"
FIELD_BEHAVIOUR_TAGS          = "BehaviourTags"
FIELD_CONFIDENT_RATING        = "ConfidentRating"
FIELD_HOSTING_IP              = "HostingIp"
FIELD_IOC_ATTACK_NAME         = "IocAttackName"
FIELD_IOC_TYPE                = "IocType"
FIELD_REFERENCE_LINK          = "ReferenceLink"
FIELD_RISK_RATING             = "RiskRating"
FIELD_SOURCE_NAME_ID          = "SourceNameId"
FIELD_UUID                    = "Uuid"

# mobile_apps  (Mobile Apps)
FIELD_APPLICATION_NAME        = "ApplicationName"
FIELD_MARKET_SOURCE           = "MarketSource"
FIELD_INDEX                   = "Index"
FIELD_APP_AVAILABILITY        = "AppAvailability"
FIELD_CAT_KEY                 = "CatKey"
FIELD_DEEP_LINK               = "DeepLink"
FIELD_EMAIL                   = "Email"
FIELD_IDENTIFIED_AT           = "IdentifiedAt"
FIELD_MARKET_STATUS           = "MarketStatus"
FIELD_MARKET_UPDATE           = "MarketUpdate"
FIELD_PACKAGE_NAME            = "PackageName"
FIELD_PRIVACY_POLICY          = "PrivacyPolicy"
FIELD_RATINGS                 = "Ratings"
FIELD_SCREENSHOTS             = "Screenshots"
FIELD_SHORT_DESCRIPTION       = "ShortDescription"
FIELD_WEBSITE                 = "Website"
FIELD_WHAT_IS_NEW             = "WhatIsNew"

# news_feed  (Cyber Newsfeed)
FIELD_ARTICLE_NAME            = "ArticleName"
FIELD_AI_SUMMARY              = "AiSummary"
FIELD_COUNTRIES               = "Countries"
FIELD_CVES                    = "Cves"
FIELD_INDUSTRIES              = "Industries"
FIELD_IOC_DETAILS             = "IocDetails"
FIELD_IOC_TYPES               = "IocTypes"
FIELD_IOCS                    = "Iocs"
FIELD_IS_NOTIFIED             = "IsNotified"
FIELD_MALWARES                = "Malwares"
FIELD_MALWARES_NEW            = "MalwaresNew"
FIELD_NEWS_FEED_TYPE          = "NewsFeedType"
FIELD_POST_DATE               = "PostDate"
FIELD_POST_IMG                = "PostImg"
FIELD_POST_SOURCE             = "PostSource"
FIELD_REGIONS                 = "Regions"
FIELD_SOURCE_COUNTRIES        = "SourceCountries"
FIELD_TACTICS                 = "Tactics"
FIELD_TARGET_COUNTRIES        = "TargetCountries"
FIELD_THREAT_ACTORS           = "ThreatActors"
FIELD_THREAT_ACTORS_NEW       = "ThreatActorsNew"
FIELD_TTPS                    = "Ttps"

# cyber_crime_forums  (Cybercrime Forum Mentions)
FIELD_DISCUSSION_DATE         = "DiscussionDate"
FIELD_DISCUSSION_BY           = "DiscussionBy"
FIELD_TOPIC_NAME              = "TopicName"
FIELD_CATEGORY_ID             = "CategoryId"
FIELD_DISCUSSION_ID           = "DiscussionId"
FIELD_JOINED_DATE             = "JoinedDate"
FIELD_LIKES                   = "Likes"
FIELD_NUMBER_OF_POSTS         = "NumberOfPosts"
FIELD_REPUTATION              = "Reputation"
FIELD_TOPIC_CREATED_BY        = "TopicCreatedBy"
FIELD_TOPIC_ID                = "TopicId"

# stealer_logs  (Compromised Endpoints)
FIELD_COMPROMISED_DATE      = "CompromisedDate"
FIELD_MALWARE_FAMILY        = "MalwareFamily"
FIELD_APPLICATION           = "Application"
FIELD_PASSWORD              = "Password"
FIELD_USER_HASH             = "UserHash"
FIELD_DOC_ID                = "DocId"
FIELD_COUNTRY_NAME          = "CountryName"
FIELD_FILE_CREATED_DATE     = "FileCreatedDate"
FIELD_FILE_MODIFIED_DATE    = "FileModifiedDate"
FIELD_FILE_C_DATE           = "FileCDate"
FIELD_FILE_M_DATE           = "FileMDate"
FIELD_FILE_FULL_PATH        = "FileFullPath"
FIELD_FILE_SIZE             = "FileSize"
FIELD_FILE_TYPE             = "FileType"
FIELD_PARENT_FOLDER_ID      = "ParentFolderId"
FIELD_DOC_CREATED_ON        = "DocCreatedOn"

# ── Job persistent-state keys ─────────────────────────────────────────────────
# Stored in job context; keyed by service name
STATE_KEY_LAST_RUN_PREFIX = "cyble_last_run_"   # + service_name

# ── All known Cyble services (from live API, used for validation) ─────────────
ALL_KNOWN_SERVICES = [
    "ssl_expiry", "assets", "botnet", "cloud_storage",
    "bit_bucket", "docker", "github", "postman",
    "compromised_cards", "compromised_endpoints_cookies", "stealer_logs",
    "compromised_files", "news_feed", "cyber_crime_forums",
    "cyble_research_labs", "advisory", "darkweb_marketplaces",
    "darkweb_data_breaches", "defacement_content", "defacement_keyword",
    "defacement_url", "discord", "domain_expiry", "domain_watchlist",
    "hacktivism", "i2p", "iocs", "ip_risk_score", "vulnerability",
    "mobile_apps", "new_vulnerability", "new_port", "flash_report",
    "osint", "ot_ics", "pastebin", "phishing", "product_vulnerability",
    "ransomware_updates", "darkweb_ransomware", "social_media_monitoring",
    "subdomains", "suspicious_domains", "telegram_mentions", "tor_links",
    "web_applications", "physical_threats", "malicious_ads",
    "leaked_credentials",
]

# ── Service → SecOps alert type hints (for playbook routing) ─────────────────
HIGH_PRIORITY_SERVICES = {
    "ransomware_updates", "darkweb_ransomware", "leaked_credentials",
    "compromised_cards", "stealer_logs", "phishing", "iocs",
    "darkweb_data_breaches", "botnet",
}

# ── Alert name templates ──────────────────────────────────────────────────────
# Format: "<Service Display Name> - <value of TITLE_FIELD_BY_SERVICE[service]>"
# Default field is `keyword_name`; some services use a different field (see below).
# Example: "Asset SSL Expiry - adairports.ae"
ALERT_NAME_TEMPLATE = "{display_name} - {keyword}"
CASE_NAME_TEMPLATE  = "{service} Alert - {keyword}"

# Per-service override for which raw-alert field becomes the second half of the
# case title. The resolver checks top-level keys first, then `data.data.*`, then
# falls back to keyword_name → "N/A" so the case header is never blank.
#
# To change the title source for a service, just add/edit an entry here — no
# code changes needed in CybleAlertMapper.
TITLE_FIELD_BY_SERVICE = {
    "darkweb_data_breaches": "breach_source",
    "product_vulnerability": "company",
    "subdomains":            "subdomain",
    "physical_threats":      "title",
    "web_applications":      "title",
    "vulnerability":         "title",
    "postman":               "title",
    "docker":                "title",
}
TITLE_FIELD_DEFAULT = "keyword_name"

# ── Connector test constants ──────────────────────────────────────────────────
PING_TIMEOUT = 10
