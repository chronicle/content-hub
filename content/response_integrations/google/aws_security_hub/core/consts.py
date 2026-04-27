from __future__ import annotations
INTEGRATION_NAME = "AWSSecurityHub"
PAGE_SIZE = 100  # findings page size default max
VENDOR = "AWS"
PRODUCT = "Security Hub"
TIME_FORMAT = "%Y-%m-%dT%H:%M:%SZ"

MAX_ALERTS_TO_FETCH = 100  # total max alerts to fetch per page

DEFAULT_NUM_INSIGHT_DETAILS = 50  # default number of insight details to return
DEFAULT_TIMEOUT_IN_SECONDS = 180

MAPPED_GROUP_BY_ATTRIBUTE = {  # Map name to aws group by attribute
    "AWS Account ID": "AwsAccountId",
    "Company Name": "CompanyName",
    "Status": "ComplianceStatus",
    "Generator ID": "ComplianceStatus",
    "Malware Name": "MalwareName",
    "Process Name": "ProcessName",
    "Threat Intel Type": "ThreatIntelIndicatorType",
    "Product ARN": "ProductArn",
    "Product Name": "ProductName",
    "Record State": "RecordState",
    "EC2 Instance Image ID": "ResourceAwsEc2InstanceImageId",
    "EC2 Instance IPv4": "ResourceAwsEc2InstanceIpV4Addresses",
    "EC2 Instance IPv6": "ResourceAwsEc2InstanceIpV6Addresses",
    "EC2 Instance Key Name": "ResourceAwsEc2InstanceKeyName",
    "EC2 Instance Subnet ID": "ResourceAwsEc2InstanceSubnetId",
    "EC2 Instance Type": "ResourceAwsEc2InstanceType",
    "EC2 Instance VPC ID": "ResourceAwsEc2InstanceVpcId",
    "IAM Access Key User Name": "ResourceAwsIamAccessKeyUserName",
    "S3 Bucket Owner Name": "ResourceAwsS3BucketOwnerName",
    "Container Image ID": "ResourceContainerImageId",
    "Container Image Name": "ResourceContainerImageName",
    "Container Name": "ResourceContainerName",
    "Resource ID": "ResourceId",
    "Resource Type": "ResourceType",
    "Severity Label": "SeverityLabel",
    "Source URL": "SourceUrl",
    "Type": "Type",
    "Verification State": "VerificationState",
    "Workflow Status": "WorkflowStatus",
}

CONFIDENCE_DEFAULT = 0
CRITICALITY_DEFAULT = 50

CONFIDENCE_CRITICALITY_RANGE = range(0, 101)

MAPPED_SEVERITY = {  # map user specified severity to aws security hub severity
    "Critical": "CRITICAL",
    "High": "HIGH",
    "Medium": "MEDIUM",
    "Low": "LOW",
    "Informational": "INFORMATIONAL",
}

MAPPED_VERIFICATION_STATE = (
    {  # map user specified verification state to aws security hub verification state
        "Unknown": "UNKNOWN",
        "True Positive": "TRUE_POSITIVE",
        "False Positive": "FALSE_POSITIVE",
        "Benign Positive": "BENIGN_POSITIVE",
    }
)

MAPPED_WORKFLOW_STATUS = (
    {  # map user specified workflow status to aws security hub workflow status
        "New": "NEW",
        "Notified": "NOTIFIED",
        "Resolved": "RESOLVED",
        "Suppressed": "SUPPRESSED",
    }
)
