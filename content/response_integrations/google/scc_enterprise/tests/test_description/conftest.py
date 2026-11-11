from __future__ import annotations

from typing import Callable, TypeVar

import pytest

from scc_enterprise.core.SCCEnterpriseDatamodels import (
    FindingContext
)
from scc_enterprise.core.SCCEnterpriseDescCreation import (
    CreateDescFn,
    get_create_desc_fn,
)
from scc_enterprise.core.SCCEnterpriseDescParams import (
    CloudProviderEnum,
    DescriptionOutputType,
    DescriptionParamsCreator,
    ParseStringFn,
    get_desc_parameter_creator,
)
from TIPCommon.types import SingleJson


ParamCreatorFn: TypeVar = Callable[[SingleJson], SingleJson]


@pytest.fixture()
def event_keys_and_values() -> dict[str, str]:
    yield {
        "description": "An Assumed Identity has more permissions than it uses, violating the principle of least privilege. To align with security best practices, update its IAM policy and remove the unnecessary permissions.",
        "nextSteps": '**Step 1**\nCreate a new IAM Policy with least privilege.\n\n```\n{\n  "Statement":[\n    {\n      "Effect":"Allow",\n      "Action":["s3:TagResource"],\n      "Resources":["arn:aws:s3::bucket1/hello","arn:aws:s3::bucket1/world*"]\n    }\n  ]\n}\n```\n\n**Step 2**\nAttach the new IAM Policy.\n\n**Step 3**\nDetach the old IAM Policy.',
        "sourceProperties_ExceptionInstructions": "Exception Instructions",
        "sourceProperties_Explanation": "Explanation",
        "sourceProperties_Recommendation": "Recommendation",
        "vulnerability_cve_observedInTheWild": "a",
        "vulnerability_cve_zeroDay": "b",
        "vulnerability_cve_exploitationActivity": "c",
        "vulnerability_cve_impact": "d",
        "vulnerability_cve_upstreamFixAvailable": "e",
        "vulnerability_cve_cvssv3_availabilityImpact": "f",
        "vulnerability_cve_cvssv3_integrityImpact": "g",
        "vulnerability_cve_cvssv3_confidentialityImpact": "h",
        "vulnerability_cve_cvssv3_scope": "i",
        "vulnerability_cve_cvssv3_userInteraction": "j",
        "vulnerability_cve_cvssv3_privilegesRequired": "k",
        "vulnerability_cve_cvssv3_attackComplexity": "l",
        "vulnerability_cve_cvssv3_attackVector": "m",
        "vulnerability_cve_cvssv3_baseScore": "n",
    }


@pytest.fixture()
def event_keys_and_link_values() -> dict[str, str]:
    yield {
        "description": "https://www.google.com",
        "nextSteps": "https://www.google.com",
        "sourceProperties_ExceptionInstructions": "https://www.google.com",
        "sourceProperties_Explanation": "https://www.google.com",
        "sourceProperties_Recommendation": "https://www.google.com",
    }


@pytest.fixture
def empty_event() -> dict[str, str]:
    yield {}


@pytest.fixture
def event_with_source_properties() -> dict[str, str]:
    yield {
        "name": "organizations/971363459032/sources/3683318981399653071/findings/85b394ed644941b67c89bacebb95da16",
        "parent": "organizations/971363459032/sources/3683318981399653071",
        "resourceName": "//compute.googleapis.com/projects/nexus-lab-401713/global/targetHttpProxies/1181954275444882742",
        "state": "ACTIVE",
        "category": "HTTP_LOAD_BALANCER",
        "externalUri": "https://console.cloud.google.com/net-services/loadbalancing/advanced/targetHttpProxies/details/http-redirect?project=nexus-lab-401713&organizationId=971363459032",
        "sourceProperties_Recommendation": 'Go to https://console.cloud.google.com/net-services/loadbalancing/advanced/targetHttpProxies/details/http-redirect?project=nexus-lab-401713&organizationId=971363459032 and click the link under the "URL map" section. It will take you to the load balancer page. Click "Edit". Click "Frontend configuration". On the right-hand side, delete all "Frontend IP and port" configurations that allow HTTP traffic and create new ones that allow HTTPS traffic.',
        "sourceProperties_ExceptionInstructions": 'Add the security mark "allow_http_load_balancer" to the asset with a value of "true" to prevent this finding from being activated again.',
        "sourceProperties_Explanation": "To protect the integrity of your data and prevent intruders from tampering with your communications, it is recommended to configure your HTTP(S) load balancers to allow only HTTPS traffic.",
        "sourceProperties_ScannerName": "COMPUTE_INSTANCE_SCANNER",
        "sourceProperties_ResourcePath_1": "projects/nexus-lab-401713/",
        "sourceProperties_ResourcePath_2": "organizations/971363459032/",
        "sourceProperties_compliance_standards_pci_1_ids_1": "2.3",
        "sourceProperties_ReactivationCount": "0.0",
        "securityMarks_name": "organizations/971363459032/sources/3683318981399653071/findings/85b394ed644941b67c89bacebb95da16/securityMarks",
        "eventTime": "2024-03-31T13:56:45.029886Z",
        "createTime": "2024-03-31T14:03:53.911Z",
        "propertyDataTypes_ResourcePath_listValues_propertyDataTypes_1_primitiveDataType": "STRING",
        "propertyDataTypes_ReactivationCount_primitiveDataType": "NUMBER",
        "propertyDataTypes_Explanation_primitiveDataType": "STRING",
        "propertyDataTypes_ScannerName_primitiveDataType": "STRING",
        "propertyDataTypes_compliance_standards_structValue_fields_pci_listValues_propertyDataTypes_1_structValue_fields_ids_listValues_propertyDataTypes_1_primitiveDataType": "STRING",
        "propertyDataTypes_ExceptionInstructions_primitiveDataType": "STRING",
        "propertyDataTypes_Recommendation_primitiveDataType": "STRING",
        "severity": "MEDIUM",
        "workflowState": "NEW",
        "canonicalName": "projects/429213313266/sources/3683318981399653071/findings/85b394ed644941b67c89bacebb95da16",
        "mute": "UNDEFINED",
        "findingClass": "MISCONFIGURATION",
        "muteUpdateTime": "1970-01-01T00:00:00Z",
        "caiResource": "//compute.googleapis.com/projects/nexus-lab-401713/global/targetHttpProxies/http-redirect",
        "contacts_security_contacts_1_email": "admin@olivierba.altostrat.com",
        "compliances_1_standard": "pci",
        "compliances_1_ids_1": "2.3",
        "originalProviderId": "SECURITY_HEALTH_ADVISOR",
        "parentDisplayName": "Security Health Analytics",
        "description": "To protect the integrity of your data and prevent intruders from tampering with your communications, it is recommended to configure your HTTP(S) load balancers to allow only HTTPS traffic.",
        "cloudProvider": "GOOGLE_CLOUD_PLATFORM",
        "muteInfo_staticMute_state": "UNDEFINED",
        "muteInfo_staticMute_applyTime": "1970-01-01T00:00:00Z",
        "resource_name": "//compute.googleapis.com/projects/nexus-lab-401713/global/targetHttpProxies/http-redirect",
        "resource_project": "//cloudresourcemanager.googleapis.com/projects/429213313266",
        "resource_projectDisplayName": "nexus-lab-401713",
        "resource_parent": "//cloudresourcemanager.googleapis.com/projects/429213313266",
        "resource_parentDisplayName": "nexus-lab-401713",
        "resource_type": "google.compute.TargetHttpProxy",
        "resource_displayName": "http-redirect",
        "resource_cloudProvider": "GOOGLE_CLOUD_PLATFORM",
        "resource_organization": "organizations/971363459032",
        "resource_service": "compute.googleapis.com",
        "resource_location": "global",
        "resource_resourcePath_nodes_1_nodeType": "GCP_PROJECT",
        "resource_resourcePath_nodes_1_id": "projects/429213313266",
        "resource_resourcePath_nodes_1_displayName": "nexus-lab-401713",
        "resource_resourcePath_nodes_2_nodeType": "GCP_ORGANIZATION",
        "resource_resourcePath_nodes_2_id": "organizations/971363459032",
        "resource_resourcePathString": "organizations/971363459032/projects/429213313266",
        "resource_google.compute.TargetHttpProxy": "http-redirect",
        "DeviceEventClassId": "HTTP_LOAD_BALANCER",
        "Name": "HTTP_LOAD_BALANCER",
    }


@pytest.fixture
def event_without_source_properties() -> dict[str, str]:
    yield {
        "name": "organizations/971363459032/sources/7302865542775956364/findings/c2b5b51e6ddfe8aac2fd3888a7a91781",
        "parent": "organizations/971363459032/sources/7302865542775956364",
        "resourceName": "//storage.googleapis.com/temp_01352409d637ea7f87d38ba96fa178ece019770d",
        "state": "ACTIVE",
        "category": "non_eu_storage_bucket",
        "securityMarks_name": "organizations/971363459032/sources/7302865542775956364/findings/c2b5b51e6ddfe8aac2fd3888a7a91781/securityMarks",
        "eventTime": "2024-03-31T13:56:45.029886Z",
        "createTime": "2024-03-28T09:31:13.219Z",
        "severity": "HIGH",
        "workflowState": "NEW",
        "canonicalName": "projects/429213313266/sources/7302865542775956364/findings/c2b5b51e6ddfe8aac2fd3888a7a91781",
        "mute": "UNDEFINED",
        "findingClass": "MISCONFIGURATION",
        "muteUpdateTime": "1970-01-01T00:00:00Z",
        "externalSystems_chronicle_soar_name": "organizations/971363459032/sources/7302865542775956364/findings/c2b5b51e6ddfe8aac2fd3888a7a91781/externalSystems/chronicle_soar",
        "externalSystems_chronicle_soar_assignees_1": "@Vulnerability Managers",
        "externalSystems_chronicle_soar_externalUid": "2661",
        "externalSystems_chronicle_soar_status": "Closed",
        "externalSystems_chronicle_soar_externalSystemUpdateTime": "2024-03-31T00:31:33Z",
        "externalSystems_chronicle_soar_caseUri": "https://gglwl.backstory.chronicle.security/cases/2661",
        "externalSystems_chronicle_soar_casePriority": "High",
        "externalSystems_chronicle_soar_ticketInfo_id": "76e16d1847d902108f06d264336d43b5",
        "externalSystems_chronicle_soar_ticketInfo_assignee": "Olivier Barescut",
        "externalSystems_chronicle_soar_ticketInfo_uri": "https://dev57250.service-now.com/now/nav/ui/classic/params/target/u_scc_enterprise_cloud_posture_ticket.do%3Fsys_id%3D76e16d1847d902108f06d264336d43b5",
        "externalSystems_chronicle_soar_ticketInfo_status": "Resolved",
        "externalSystems_chronicle_soar_ticketInfo_updateTime": "2024-03-31T00:31:32Z",
        "externalSystems_chronicle_soar_caseSla": "2024-04-11T09:31:42Z",
        "externalSystems_chronicle_soar_caseCreateTime": "1970-01-01T00:00:00Z",
        "externalSystems_chronicle_soar_caseCloseTime": "1970-01-01T00:00:00Z",
        "caiResource": "//storage.googleapis.com/temp_01352409d637ea7f87d38ba96fa178ece019770d",
        "contacts_security_contacts_1_email": "admin@olivierba.altostrat.com",
        "originalProviderId": "SHA_CUSTOM",
        "parentDisplayName": "Security Health Analytics Custom",
        "description": "Triggered when a storage bucket is created outside of europe",
        "nextSteps": "Remove the bucket and recreated in a european region",
        "moduleName": "organizations/971363459032/securityHealthAnalyticsSettings/customModules/873688668350427895",
        "cloudProvider": "GOOGLE_CLOUD_PLATFORM",
        "muteInfo_staticMute_state": "UNDEFINED",
        "muteInfo_staticMute_applyTime": "1970-01-01T00:00:00Z",
        "resource_name": "//storage.googleapis.com/temp_01352409d637ea7f87d38ba96fa178ece019770d",
        "resource_project": "//cloudresourcemanager.googleapis.com/projects/429213313266",
        "resource_projectDisplayName": "nexus-lab-401713",
        "resource_parent": "//cloudresourcemanager.googleapis.com/projects/429213313266",
        "resource_parentDisplayName": "nexus-lab-401713",
        "resource_type": "google.cloud.storage.Bucket",
        "resource_displayName": "temp_01352409d637ea7f87d38ba96fa178ece019770d",
        "resource_cloudProvider": "GOOGLE_CLOUD_PLATFORM",
        "resource_organization": "organizations/971363459032",
        "resource_service": "storage.googleapis.com",
        "resource_location": "eu",
        "resource_resourcePath_nodes_1_nodeType": "GCP_PROJECT",
        "resource_resourcePath_nodes_1_id": "projects/429213313266",
        "resource_resourcePath_nodes_1_displayName": "nexus-lab-401713",
        "resource_resourcePath_nodes_2_nodeType": "GCP_ORGANIZATION",
        "resource_resourcePath_nodes_2_id": "organizations/971363459032",
        "resource_resourcePathString": "organizations/971363459032/projects/429213313266",
        "resource_google.cloud.storage.Bucket": "temp_01352409d637ea7f87d38ba96fa178ece019770d",
        "DeviceEventClassId": "non_eu_storage_bucket",
        "Name": "non_eu_storage_bucket",
    }


@pytest.fixture
def event_with_cve_cvss_and_references() -> dict[str, str]:
    yield {
        "name": "organizations/971363459032/sources/16275343852955231381/findings/3d3d4dacd8d5b908f6d88ee5f7c9d057",
        "parent": "organizations/971363459032/sources/16275343852955231381",
        "resourceName": "//compute.googleapis.com/projects/429213313266/zones/europe-west2-c/instances/5213005842719294942",
        "state": "ACTIVE",
        "category": "OS_VULNERABILITY",
        "externalUri": "https://console.cloud.google.com/compute/instancesDetail/zones/europe-west2-c/instances/5213005842719294942?project=nexus-lab-401713&tab=os-information",
        "sourceProperties_description": "Object lifecycle issue in V8 in Google Chrome prior to 123.0.6312.58 allowed a remote attacker to potentially exploit object corruption via a crafted HTML page. (Chromium security severity: High)",
        "securityMarks_name": "organizations/971363459032/sources/16275343852955231381/findings/3d3d4dacd8d5b908f6d88ee5f7c9d057/securityMarks",
        "eventTime": "2024-04-02T00:54:16.113814Z",
        "createTime": "2024-04-02T00:54:17.574Z",
        "propertyDataTypes_description_primitiveDataType": "STRING",
        "severity": "HIGH",
        "workflowState": "NEW",
        "canonicalName": "projects/429213313266/sources/16275343852955231381/findings/3d3d4dacd8d5b908f6d88ee5f7c9d057",
        "mute": "UNDEFINED",
        "findingClass": "VULNERABILITY",
        "vulnerability_cve_id": "CVE-2024-2625",
        "vulnerability_cve_references_1_source": "Distro",
        "vulnerability_cve_references_1_uri": "https://security-tracker.debian.org/tracker/CVE-2024-2625",
        "vulnerability_cve_references_2_source": "NVD",
        "vulnerability_cve_references_2_uri": "https://nvd.nist.gov/vuln/detail/CVE-2024-2625",
        "vulnerability_cve_cvssv3_baseScore": "8.800000190734863",
        "vulnerability_cve_cvssv3_attackVector": "ATTACK_VECTOR_NETWORK",
        "vulnerability_cve_cvssv3_attackComplexity": "ATTACK_COMPLEXITY_LOW",
        "vulnerability_cve_cvssv3_privilegesRequired": "PRIVILEGES_REQUIRED_NONE",
        "vulnerability_cve_cvssv3_userInteraction": "USER_INTERACTION_REQUIRED",
        "vulnerability_cve_cvssv3_scope": "SCOPE_UNCHANGED",
        "vulnerability_cve_cvssv3_confidentialityImpact": "IMPACT_HIGH",
        "vulnerability_cve_cvssv3_integrityImpact": "IMPACT_HIGH",
        "vulnerability_cve_cvssv3_availabilityImpact": "IMPACT_HIGH",
        "vulnerability_cve_upstreamFixAvailable": "True",
        "vulnerability_cve_impact": "MEDIUM",
        "vulnerability_cve_exploitationActivity": "NO_KNOWN",
        "vulnerability_securityBulletin_submissionTime": "1970-01-01T00:00:00Z",
        "muteUpdateTime": "1970-01-01T00:00:00Z",
        "caiResource": "//compute.googleapis.com/projects/nexus-lab-401713/zones/europe-west2-c/instances/snowinstance",
        "contacts_security_contacts_1_email": "admin@olivierba.altostrat.com",
        "originalProviderId": "VM_MANAGER",
        "parentDisplayName": "VM Manager",
        "description": "Object lifecycle issue in V8 in Google Chrome prior to 123.0.6312.58 allowed a remote attacker to potentially exploit object corruption via a crafted HTML page. (Chromium security severity: High)",
        "cloudProvider": "GOOGLE_CLOUD_PLATFORM",
        "muteInfo_staticMute_state": "UNDEFINED",
        "muteInfo_staticMute_applyTime": "1970-01-01T00:00:00Z",
        "resource_name": "//compute.googleapis.com/projects/nexus-lab-401713/zones/europe-west2-c/instances/snowinstance",
        "resource_project": "//cloudresourcemanager.googleapis.com/projects/429213313266",
        "resource_projectDisplayName": "nexus-lab-401713",
        "resource_parent": "//cloudresourcemanager.googleapis.com/projects/429213313266",
        "resource_parentDisplayName": "nexus-lab-401713",
        "resource_type": "google.compute.Instance",
        "resource_displayName": "snowinstance",
        "resource_cloudProvider": "GOOGLE_CLOUD_PLATFORM",
        "resource_organization": "organizations/971363459032",
        "resource_service": "compute.googleapis.com",
        "resource_location": "europe-west2-c",
        "resource_resourcePath_nodes_1_nodeType": "GCP_PROJECT",
        "resource_resourcePath_nodes_1_id": "projects/429213313266",
        "resource_resourcePath_nodes_1_displayName": "nexus-lab-401713",
        "resource_resourcePath_nodes_2_nodeType": "GCP_ORGANIZATION",
        "resource_resourcePath_nodes_2_id": "organizations/971363459032",
        "resource_resourcePathString": "organizations/971363459032/projects/429213313266",
        "resource_google.compute.Instance": "snowinstance",
        "DeviceEventClassId": "OS_VULNERABILITY",
        "Name": "OS_VULNERABILITY",
    }


@pytest.fixture
def event_without_cve_cvss_and_references() -> dict[str, str]:
    yield {
        "name": "organizations/493277373840/sources/3464266505062453435/findings/14432475124757049381",
        "parent": "organizations/493277373840/sources/3464266505062453435",
        "resourceName": "//container.googleapis.com/projects/iam-recommender-test-project/locations/us-central1/clusters/autopilot-cluster-1",
        "state": "ACTIVE",
        "category": "GKE_SECURITY_BULLETIN",
        "externalUri": "https://pantheon.corp.google.com/kubernetes/security/dashboard?project=iam-recommender-test-project",
        "securityMarks_name": "organizations/493277373840/sources/3464266505062453435/findings/14432475124757049381/securityMarks",
        "eventTime": "2024-03-28T23:15:53.980921270Z",
        "createTime": "2024-03-28T23:15:57.01Z",
        "severity": "HIGH",
        "canonicalName": "projects/437771145314/sources/3464266505062453435/findings/14432475124757049381",
        "mute": "UNDEFINED",
        "findingClass": "VULNERABILITY",
        "vulnerability_securityBulletin_bulletinId": "GCP-2024-012-cos",
        "vulnerability_securityBulletin_submissionTime": "2024-02-20T19:51:53Z",
        "vulnerability_securityBulletin_suggestedUpgradeVersion": "1.27.10-gke.1149000",
        "muteUpdateTime": "1970-01-01T00:00:00Z",
        "parentDisplayName": "GKE Security Posture",
        "description": "A vulnerability (CVE-2024-0193) has been discovered in the Linux kernel that can lead to privilege escalation on Container-Optimized OS and Ubuntu nodes.",
        "nextSteps": "Follow the [instructions to upgrade your NodePool](https://cloud.google.com/kubernetes-engine/docs/how-to/upgrading-a-cluster#upgrading-nodes) to version 1.27.10-gke.1149000 or later\n",
        "kubernetes_objects_1_kind": "NodePool",
        "kubernetes_objects_1_name": "pool-5",
        "resource_name": "//container.googleapis.com/projects/iam-recommender-test-project/locations/us-central1/clusters/autopilot-cluster-1",
        "resource_project": "//cloudresourcemanager.googleapis.com/projects/437771145314",
        "resource_projectDisplayName": "iam-recommender-test-project",
        "resource_parent": "//cloudresourcemanager.googleapis.com/projects/437771145314",
        "resource_parentDisplayName": "iam-recommender-test-project",
        "resource_type": "google.container.Cluster",
        "resource_displayName": "autopilot-cluster-1",
        "resource_cloudProvider": "GOOGLE_CLOUD_PLATFORM",
        "resource_organization": "organizations/493277373840",
        "resource_service": "container.googleapis.com",
        "resource_location": "us-central1",
        "resource_resourcePath_nodes_1_nodeType": "GCP_PROJECT",
        "resource_resourcePath_nodes_1_id": "projects/437771145314",
        "resource_resourcePath_nodes_1_displayName": "iam-recommender-test-project",
        "resource_resourcePath_nodes_2_nodeType": "GCP_ORGANIZATION",
        "resource_resourcePath_nodes_2_id": "organizations/493277373840",
        "resource_resourcePathString": "organizations/493277373840/projects/437771145314",
        "resource_google.container.Cluster": "autopilot-cluster-1",
        "DeviceEventClassId": "GKE_SECURITY_BULLETIN",
        "Name": "GKE_SECURITY_BULLETIN",
    }


@pytest.fixture
def undetermined_cloud_provider_event() -> dict[str, str]:
    yield {
        "name": "organizations/493277373840/sources/17329863415806876445/findings/8036ff670bad28f2d67fc4ccb826c66f",
        "parent": "organizations/493277373840/sources/17329863415806876445",
        "resourceName": "arn:aws:iam::381492280979:role/other-cloud-config-delegate-role",
        "state": "ACTIVE",
        "category": "ASSUMED_IDENTITY_HAS_EXCESSIVE_PERMISSIONS",
        "sourceProperties_Remediation_iamPolicyRemediation_operations_1_awsIamPolicy_Statement_1_Resource_1": "arn:aws:s3::bucket1/hello",
        "sourceProperties_Remediation_iamPolicyRemediation_operations_1_awsIamPolicy_Statement_1_Resource_2": "arn:aws:s3::bucket1/world*",
        "sourceProperties_Remediation_iamPolicyRemediation_operations_1_awsIamPolicy_Statement_1_Effect": "Allow",
        "sourceProperties_Remediation_iamPolicyRemediation_operations_1_awsIamPolicy_Statement_1_Action_1": "s3:GetObject",
        "sourceProperties_Remediation_iamPolicyRemediation_operations_1_description": "Create a new IAM Policy with least privilege",
        "sourceProperties_Remediation_iamPolicyRemediation_operations_1_iamPolicyJson": '{\n "Statement": [\n  {\n   "Effect": "Allow",\n   "Resource": [\n    "arn:aws:s3::bucket1/hello",\n    "arn:aws:s3::bucket1/world*"\n   ],\n   "Action": [\n    "s3:GetObject"\n   ]\n  }\n ]\n}\n',
        "sourceProperties_Remediation_iamPolicyRemediation_operations_1_action": "OPERATION_ACTION_CREATE_IAM_POLICY",
        "sourceProperties_Remediation_iamPolicyRemediation_operations_2_sequenceNumber": "1",
        "sourceProperties_Remediation_iamPolicyRemediation_operations_2_description": "Attach the new IAM Policy",
        "sourceProperties_Remediation_iamPolicyRemediation_operations_2_action": "OPERATION_ACTION_ATTACH_IAM_POLICY",
        "sourceProperties_Remediation_iamPolicyRemediation_operations_2_attachmentPointName": "arn:aws:iam::381492280979:role/other-cloud-config-delegate-role",
        "sourceProperties_Remediation_iamPolicyRemediation_operations_3_policyResourceName": "arn:aws:iam::123456789012:policy/policy_1",
        "sourceProperties_Remediation_iamPolicyRemediation_operations_3_action": "OPERATION_ACTION_DETACH_IAM_POLICY",
        "sourceProperties_Remediation_iamPolicyRemediation_operations_3_sequenceNumber": "2",
        "sourceProperties_Remediation_iamPolicyRemediation_operations_3_description": "Detach the old IAM Policy",
        "sourceProperties_Remediation_iamPolicyRemediation_operations_3_attachmentPointName": "arn:aws:iam::381492280979:role/other-cloud-config-delegate-role",
        "sourceProperties_Metadata_providerName": "PROVIDER_NAME_CIEM",
        "securityMarks_name": "organizations/493277373840/sources/17329863415806876445/findings/8036ff670bad28f2d67fc4ccb826c66f/securityMarks",
        "eventTime": "2024-03-26T04:45:22.826868402Z",
        "createTime": "2024-03-26T04:45:34.974Z",
        "severity": "CRITICAL",
        "canonicalName": "organizations/493277373840/sources/17329863415806876445/findings/8036ff670bad28f2d67fc4ccb826c66f",
        "mute": "UNDEFINED",
        "findingClass": "MISCONFIGURATION",
        "muteUpdateTime": "1970-01-01T00:00:00Z",
        "parentDisplayName": "CIEM",
        "description": "IAM Roles with unused actions in their policies have excessive permissions, violating the principle of least privilege and increasing security risks \u2013 regularly review and remove unused permissions to ensure only necessary actions are allowed.",
        "nextSteps": '**Step 1: Create a new Managed IAM Policy with least privilege.**\n\nUsing AWS Management Console:\n\n* **Sign in to IAM:** Navigate to the IAM console (https://console.aws.amazon.com/iam/) and sign in with credentials that have permissions to create policies.\n\n* **Access Policies:** In the navigation pane, choose "Policies".\n\n* **Create Policy:** Click on the "Create policy" button.\n\n  * Choose Creation Method as JSON.\n\n  * Construct Your Policy (JSON) from the following\n\n```\n{\n "Statement": [\n  {\n   "Effect": "Allow",\n   "Resource": [\n    "arn:aws:s3::bucket1/hello",\n    "arn:aws:s3::bucket1/world*"\n   ],\n   "Action": [\n    "s3:GetObject"\n   ]\n  }\n ]\n}\n\n```\n\n**Step 2: Attach the IAM Policy to the Identity.**\n\nUsing AWS Management Console:\n\n* **Sign in to IAM:** Navigate to the IAM console (https://console.aws.amazon.com/iam/) and sign in with credentials that have permissions to manage IAM users and policies.\n\n* **Locate your Identity:** In the navigation pane, choose one of "Users", "Role" or "User groups" and select the identity you want to attach the policy to. \n  * Identity ARN: `arn:aws:iam::381492280979:role/other-cloud-config-delegate-role`\n\n* **Open Permissions Tab:** Click on the "Permissions" tab for the selected identity.\n\n* **Attach Policy:** Click the "Add permissions" button, search for and select your customer-managed policy, created in the previous step.\n\n* **Review and Attach:** Review the permissions and click "Add permissions".\n\n**Step 3: Detach the old over permissive Managed IAM Policy.**\n\nUsing AWS Management Console:\n\n* **Sign in to IAM:** Navigate to the IAM console (https://console.aws.amazon.com/iam/) and sign in with credentials that have permissions to manage IAM users and policies.\n\n* **Locate your Identity:** In the navigation pane, choose one of "Users", "Role" or "User groups" and select the identity you want to attach the policy to. \n  * Identity ARN: `arn:aws:iam::381492280979:role/other-cloud-config-delegate-role`\n\n* **Open Permissions Tab:** Click on the "Permissions" tab for the selected identity.\n\n* **Find the Policy:** In the list of attached policies, locate the customer-managed policy you want to detach:\n  * Policy ARN: `arn:aws:iam::123456789012:policy/policy_1`\n\n* **Detach Policy:**\n  * Expand the policy name, and click on the "Remove" button.\n  * Confirm Detachment: When prompted, confirm your intention to detach the policy.\n',
        "resource_name": "arn:aws:iam::381492280979:role/other-cloud-config-delegate-role",
        "startTime": "1711448880436",
        "endTime": "1711448880436",
        "DeviceEventClassId": "ASSUMED_IDENTITY_HAS_EXCESSIVE_PERMISSIONS",
        "Name": "ASSUMED_IDENTITY_HAS_EXCESSIVE_PERMISSIONS",
    }


@pytest.fixture
def aws_event() -> dict[str, str]:
    yield {
        "name": "organizations/971363459032/sources/3683318981399653071/findings/c8fcb9c5d373023e7f50cacc8a64f8bf",
        "parent": "organizations/971363459032/sources/3683318981399653071",
        "resourceName": "arn:aws:iam::975050047974:user/chronicle-logs-user",
        "state": "ACTIVE",
        "category": "IAM_USER_MFA_ENABLED",
        "sourceProperties_compliance_standards_pci_1_ids_1": "8.3.2",
        "sourceProperties_ReactivationCount": "0.0",
        "securityMarks_name": "organizations/971363459032/sources/3683318981399653071/findings/c8fcb9c5d373023e7f50cacc8a64f8bf/securityMarks",
        "eventTime": "2024-03-28T16:47:44.111252Z",
        "createTime": "2024-03-28T17:03:59.414Z",
        "propertyDataTypes_ReactivationCount_primitiveDataType": "NUMBER",
        "propertyDataTypes_compliance_standards_structValue_fields_pci_listValues_propertyDataTypes_1_structValue_fields_ids_listValues_propertyDataTypes_1_primitiveDataType": "STRING",
        "severity": "CRITICAL",
        "workflowState": "NEW",
        "canonicalName": "organizations/971363459032/sources/3683318981399653071/findings/c8fcb9c5d373023e7f50cacc8a64f8bf",
        "mute": "UNDEFINED",
        "findingClass": "MISCONFIGURATION",
        "muteUpdateTime": "1970-01-01T00:00:00Z",
        "caiResource": "//cloudasset.googleapis.com/organizations/971363459032/otherCloudConnections/aws/arn:aws:iam::975050047974:user/chronicle-logs-user",
        "contacts_security_contacts_1_email": "admin@olivierba.altostrat.com",
        "compliances_1_standard": "pci",
        "compliances_1_ids_1": "8.3.2",
        "originalProviderId": "SECURITY_HEALTH_ADVISOR",
        "parentDisplayName": "Security Health Analytics",
        "description": "Multi-factor authentication (MFA) is a best practice that adds an extra layer of protection on top of user names and passwords. With MFA, when a user signs in to the AWS Management Console, they are required to provide a time-sensitive authentication code, provided by a registered virtual or physical device.\n",
        "nextSteps": 'Note: this control uses the AWS Credential Report, which has a grace period of 4 hours before changes to credentials take effect.\n\n__Terraform__\n\nWhen it comes to Terraform, there are a few options to remediate the absence of MFA devices. You probably already have a sensible structure for organizing your users into groups and restrictive policies.\n\nThe following example shows how to:\n\n1. Create users.\n2. Create users login profiles with a PGP Public key.\n3. Create group and group policy that allows self management of IAM profile.\n4. Attach users to group.\n5. Create Virtual MFA devices for users.\n6. Provide each user with the output QR Code and password.\n\n```hcl\nvariable "users" {\n  type = set(string)\n  default = [\n    "test@example.com",\n    "test2@example.com"\n  ]\n}\n\nresource "aws_iam_user" "test_users" {\n  for_each = toset(var.users)\n  name     = each.key\n}\n\nresource "aws_iam_user_login_profile" "test_users_profile" {\n  for_each                = var.users\n  user                    = each.key\n  # Key pair created using GnuPG, this is the public key\n  pgp_key = file("path/to/gpg_pub_key_base64.pem")\n  password_reset_required = true\n  lifecycle {\n    ignore_changes = [\n      password_length,\n      password_reset_required,\n      pgp_key,\n    ]\n  }\n}\n\nresource "aws_iam_virtual_mfa_device" "test_mfa" {\n  for_each                = toset(var.users)\n  virtual_mfa_device_name = each.key\n}\n\nresource "aws_iam_group" "enforce_mfa_group" {\n  name = "EnforceMFAGroup"\n}\n\nresource "aws_iam_group_membership" "enforce_mfa_group_membership" {\n  name  = "EnforceMFAGroupMembership"\n  group = aws_iam_group.enforce_mfa_group.name\n  users = [for k in aws_iam_user.test_users : k.name]\n}\n\nresource "aws_iam_group_policy" "enforce_mfa_policy" {\n  name   = "EnforceMFAGroupPolicy"\n  group  = aws_iam_group.enforce_mfa_group.id\n  policy = <<POLICY\n{\n  "Version": "2012-10-17",\n  "Statement": [\n    {\n        "Sid": "AllowViewAccountInfo",\n        "Effect": "Allow",\n        "Action": [\n            "iam:GetAccountPasswordPolicy",\n            "iam:ListVirtualMFADevices"\n        ],\n        "Resource": "*"\n    },\n    {\n        "Sid": "AllowManageOwnPasswords",\n        "Effect": "Allow",\n        "Action": [\n            "iam:ChangePassword",\n            "iam:GetUser"\n        ],\n        "Resource": "arn:aws:iam::*:user/$${aws:username}"\n    },\n    {\n        "Sid": "AllowManageOwnAccessKeys",\n        "Effect": "Allow",\n        "Action": [\n            "iam:CreateAccessKey",\n            "iam:DeleteAccessKey",\n            "iam:ListAccessKeys",\n            "iam:UpdateAccessKey"\n        ],\n        "Resource": "arn:aws:iam::*:user/$${aws:username}"\n    },\n    {\n        "Sid": "AllowManageOwnSigningCertificates",\n        "Effect": "Allow",\n        "Action": [\n            "iam:DeleteSigningCertificate",\n            "iam:ListSigningCertificates",\n            "iam:UpdateSigningCertificate",\n            "iam:UploadSigningCertificate"\n        ],\n        "Resource": "arn:aws:iam::*:user/$${aws:username}"\n    },\n    {\n        "Sid": "AllowManageOwnSSHPublicKeys",\n        "Effect": "Allow",\n        "Action": [\n            "iam:DeleteSSHPublicKey",\n            "iam:GetSSHPublicKey",\n            "iam:ListSSHPublicKeys",\n            "iam:UpdateSSHPublicKey",\n            "iam:UploadSSHPublicKey"\n        ],\n        "Resource": "arn:aws:iam::*:user/$${aws:username}"\n    },\n    {\n        "Sid": "AllowManageOwnGitCredentials",\n        "Effect": "Allow",\n        "Action": [\n            "iam:CreateServiceSpecificCredential",\n            "iam:DeleteServiceSpecificCredential",\n            "iam:ListServiceSpecificCredentials",\n            "iam:ResetServiceSpecificCredential",\n            "iam:UpdateServiceSpecificCredential"\n        ],\n        "Resource": "arn:aws:iam::*:user/$${aws:username}"\n    },\n    {\n        "Sid": "AllowManageOwnVirtualMFADevice",\n        "Effect": "Allow",\n        "Action": [\n            "iam:CreateVirtualMFADevice",\n            "iam:DeleteVirtualMFADevice"\n        ],\n        "Resource": "arn:aws:iam::*:mfa/$${aws:username}"\n    },\n    {\n        "Sid": "AllowManageOwnUserMFA",\n        "Effect": "Allow",\n        "Action": [\n            "iam:DeactivateMFADevice",\n            "iam:EnableMFADevice",\n            "iam:ListMFADevices",\n            "iam:ResyncMFADevice"\n        ],\n        "Resource": "arn:aws:iam::*:user/$${aws:username}"\n    },\n    {\n        "Sid": "DenyAllExceptListedIfNoMFA",\n        "Effect": "Deny",\n        "NotAction": [\n            "iam:CreateVirtualMFADevice",\n            "iam:EnableMFADevice",\n            "iam:GetUser",\n            "iam:ListMFADevices",\n            "iam:ListVirtualMFADevices",\n            "iam:ResyncMFADevice",\n            "sts:GetSessionToken"\n        ],\n        "Resource": "*",\n        "Condition": {\n            "BoolIfExists": {\n                "aws:MultiFactorAuthPresent": "False"\n            }\n        }\n    }\n  ]\n}\nPOLICY\n}\n\noutput "user_password_map" {\n  # Outputs a map in the format {"test@example.com": <PGPEncryptedPassword>, "test2@example.com": <PGPEncryptedPassword>}\n  value = { for k, v in aws_iam_user_login_profile.test_users_profile : k => v.password }\n}\n\noutput "user_qr_map" {\n  # Outputs a map in the format {"test@example.com": <QRCode>, "test2@example.com": <QRCode>}\n  value = { for k, v in aws_iam_virtual_mfa_device.test_mfa : k => v.qr_code_png }\n}\n\n__AWS Console__\n\nTo enable MFA for any user accounts with AWS console access, see [Enabling a virtual multi-factor authentication (MFA) device (console)](https://docs.aws.amazon.com/IAM/latest/UserGuide/id_credentials_mfa_enable_virtual.html) in the AWS documentation.\n\n**__AWS CLI__\n\nCreate an MFA device\n\n```bash\naws iam create-virtual-mfa-device \\\n  --virtual-mfa-device-name "test@example.com" \\\n  --outfile ./QRCode.png \\\n  --bootstrap-method QRCodePNG\n```\n\nEnable MFA device for existing user\n\n```bash\naws iam enable-mfa-device \\\n  --user-name "test@example.com" \\\n  --serial-number "arn:aws:iam::123456976749:mfa/test@example.com" \\\n  --authentication-code1 123456 \\\n  --authentication-code2 654321\n```',
        "cloudProvider": "AMAZON_WEB_SERVICES",
        "muteInfo_staticMute_state": "UNDEFINED",
        "muteInfo_staticMute_applyTime": "1970-01-01T00:00:00Z",
        "resource_name": "//cloudasset.googleapis.com/organizations/971363459032/otherCloudConnections/aws/arn:aws:iam::975050047974:user/chronicle-logs-user",
        "resource_type": "AWS::IAM::User",
        "resource_displayName": "arn:aws:iam::975050047974:user/chronicle-logs-user",
        "resource_cloudProvider": "AMAZON_WEB_SERVICES",
        "resource_service": "iam",
        "resource_location": "global",
        "resource_awsMetadata_account_id": "975050047974",
        "resource_resourcePath_nodes_1_nodeType": "AWS_ACCOUNT",
        "resource_resourcePath_nodes_1_id": "975050047974",
        "resource_resourcePathString": "account/975050047974",
        "resource_og_name": "arn:aws:iam::975050047974:user/chronicle-logs-user",
        "resource_AWS::IAM::User": "arn:aws:iam::975050047974:user/chronicle-logs-user",
        "DeviceEventClassId": "IAM_USER_MFA_ENABLED",
        "Name": "IAM_USER_MFA_ENABLED",
    }


@pytest.fixture
def event_with_document_statement_mitigation_description() -> dict[str, str]:
    yield {
        "name": "organizations/971363459032/sources/7302865542775956364/findings/c2b5b51e6ddfe8aac2fd3888a7a91781",
        "parent": "organizations/971363459032/sources/7302865542775956364",
        "resourceName": "//storage.googleapis.com/temp_01352409d637ea7f87d38ba96fa178ece019770d",
        "state": "ACTIVE",
        "category": "non_eu_storage_bucket",
        "securityMarks_name": "organizations/971363459032/sources/7302865542775956364/findings/c2b5b51e6ddfe8aac2fd3888a7a91781/securityMarks",
        "eventTime": "2024-03-31T13:56:45.029886Z",
        "createTime": "2024-03-28T09:31:13.219Z",
        "severity": "HIGH",
        "workflowState": "NEW",
        "canonicalName": "projects/429213313266/sources/7302865542775956364/findings/c2b5b51e6ddfe8aac2fd3888a7a91781",
        "mute": "UNDEFINED",
        "findingClass": "MISCONFIGURATION",
        "muteUpdateTime": "1970-01-01T00:00:00Z",
        "externalSystems_chronicle_soar_name": "organizations/971363459032/sources/7302865542775956364/findings/c2b5b51e6ddfe8aac2fd3888a7a91781/externalSystems/chronicle_soar",
        "externalSystems_chronicle_soar_assignees_1": "@Vulnerability Managers",
        "externalSystems_chronicle_soar_externalUid": "2661",
        "externalSystems_chronicle_soar_status": "Closed",
        "externalSystems_chronicle_soar_externalSystemUpdateTime": "2024-03-31T00:31:33Z",
        "externalSystems_chronicle_soar_caseUri": "https://gglwl.backstory.chronicle.security/cases/2661",
        "externalSystems_chronicle_soar_casePriority": "High",
        "externalSystems_chronicle_soar_ticketInfo_id": "76e16d1847d902108f06d264336d43b5",
        "externalSystems_chronicle_soar_ticketInfo_assignee": "Olivier Barescut",
        "externalSystems_chronicle_soar_ticketInfo_uri": "https://dev57250.service-now.com/now/nav/ui/classic/params/target/u_scc_enterprise_cloud_posture_ticket.do%3Fsys_id%3D76e16d1847d902108f06d264336d43b5",
        "externalSystems_chronicle_soar_ticketInfo_status": "Resolved",
        "externalSystems_chronicle_soar_ticketInfo_updateTime": "2024-03-31T00:31:32Z",
        "externalSystems_chronicle_soar_caseSla": "2024-04-11T09:31:42Z",
        "externalSystems_chronicle_soar_caseCreateTime": "1970-01-01T00:00:00Z",
        "externalSystems_chronicle_soar_caseCloseTime": "1970-01-01T00:00:00Z",
        "caiResource": "//storage.googleapis.com/temp_01352409d637ea7f87d38ba96fa178ece019770d",
        "contacts_security_contacts_1_email": "admin@olivierba.altostrat.com",
        "originalProviderId": "SHA_CUSTOM",
        "parentDisplayName": "Security Health Analytics Custom",
        "description": "DOCUMENTATION: An array indexing vulnerability was found in the netfilter subsystem of the Linux kernel. A missing macro could lead to a miscalculation of the `h->nets` array offset, providing attackers with the primitive to arbitrarily increment/decrement a memory buffer out-of-bound. This issue may allow a local user to crash the system or potentially escalate their privileges on the system.STATEMENT: Versions of `python36:3.6/python36` as shipped with Red Hat Enterprise Linux 8 are marked as 'Not affected' as they just provide \"symlinks\" to the main `python3` component, which provides the actual interpreter of the Python programming language. MITIGATION: Red Hat has investigated whether a possible mitigation exists for this issue, and has not been able to identify a practical example. Please update the affected package as soon as possible.",
        "nextSteps": "Remove the bucket and recreated in a european region",
        "moduleName": "organizations/971363459032/securityHealthAnalyticsSettings/customModules/873688668350427895",
        "cloudProvider": "GOOGLE_CLOUD_PLATFORM",
        "muteInfo_staticMute_state": "UNDEFINED",
        "muteInfo_staticMute_applyTime": "1970-01-01T00:00:00Z",
        "resource_name": "//storage.googleapis.com/temp_01352409d637ea7f87d38ba96fa178ece019770d",
        "resource_project": "//cloudresourcemanager.googleapis.com/projects/429213313266",
        "resource_projectDisplayName": "nexus-lab-401713",
        "resource_parent": "//cloudresourcemanager.googleapis.com/projects/429213313266",
        "resource_parentDisplayName": "nexus-lab-401713",
        "resource_type": "google.cloud.storage.Bucket",
        "resource_displayName": "temp_01352409d637ea7f87d38ba96fa178ece019770d",
        "resource_cloudProvider": "GOOGLE_CLOUD_PLATFORM",
        "resource_organization": "organizations/971363459032",
        "resource_service": "storage.googleapis.com",
        "resource_location": "eu",
        "resource_resourcePath_nodes_1_nodeType": "GCP_PROJECT",
        "resource_resourcePath_nodes_1_id": "projects/429213313266",
        "resource_resourcePath_nodes_1_displayName": "nexus-lab-401713",
        "resource_resourcePath_nodes_2_nodeType": "GCP_ORGANIZATION",
        "resource_resourcePath_nodes_2_id": "organizations/971363459032",
        "resource_resourcePathString": "organizations/971363459032/projects/429213313266",
        "resource_google.cloud.storage.Bucket": "temp_01352409d637ea7f87d38ba96fa178ece019770d",
        "DeviceEventClassId": "non_eu_storage_bucket",
        "Name": "non_eu_storage_bucket",
    }


@pytest.fixture
def event_with_document_statement_no_mitigation_description() -> dict[str, str]:
    yield {
        "name": "organizations/971363459032/sources/7302865542775956364/findings/c2b5b51e6ddfe8aac2fd3888a7a91781",
        "parent": "organizations/971363459032/sources/7302865542775956364",
        "resourceName": "//storage.googleapis.com/temp_01352409d637ea7f87d38ba96fa178ece019770d",
        "state": "ACTIVE",
        "category": "non_eu_storage_bucket",
        "securityMarks_name": "organizations/971363459032/sources/7302865542775956364/findings/c2b5b51e6ddfe8aac2fd3888a7a91781/securityMarks",
        "eventTime": "2024-03-31T13:56:45.029886Z",
        "createTime": "2024-03-28T09:31:13.219Z",
        "severity": "HIGH",
        "workflowState": "NEW",
        "canonicalName": "projects/429213313266/sources/7302865542775956364/findings/c2b5b51e6ddfe8aac2fd3888a7a91781",
        "mute": "UNDEFINED",
        "findingClass": "MISCONFIGURATION",
        "muteUpdateTime": "1970-01-01T00:00:00Z",
        "externalSystems_chronicle_soar_name": "organizations/971363459032/sources/7302865542775956364/findings/c2b5b51e6ddfe8aac2fd3888a7a91781/externalSystems/chronicle_soar",
        "externalSystems_chronicle_soar_assignees_1": "@Vulnerability Managers",
        "externalSystems_chronicle_soar_externalUid": "2661",
        "externalSystems_chronicle_soar_status": "Closed",
        "externalSystems_chronicle_soar_externalSystemUpdateTime": "2024-03-31T00:31:33Z",
        "externalSystems_chronicle_soar_caseUri": "https://gglwl.backstory.chronicle.security/cases/2661",
        "externalSystems_chronicle_soar_casePriority": "High",
        "externalSystems_chronicle_soar_ticketInfo_id": "76e16d1847d902108f06d264336d43b5",
        "externalSystems_chronicle_soar_ticketInfo_assignee": "Olivier Barescut",
        "externalSystems_chronicle_soar_ticketInfo_uri": "https://dev57250.service-now.com/now/nav/ui/classic/params/target/u_scc_enterprise_cloud_posture_ticket.do%3Fsys_id%3D76e16d1847d902108f06d264336d43b5",
        "externalSystems_chronicle_soar_ticketInfo_status": "Resolved",
        "externalSystems_chronicle_soar_ticketInfo_updateTime": "2024-03-31T00:31:32Z",
        "externalSystems_chronicle_soar_caseSla": "2024-04-11T09:31:42Z",
        "externalSystems_chronicle_soar_caseCreateTime": "1970-01-01T00:00:00Z",
        "externalSystems_chronicle_soar_caseCloseTime": "1970-01-01T00:00:00Z",
        "caiResource": "//storage.googleapis.com/temp_01352409d637ea7f87d38ba96fa178ece019770d",
        "contacts_security_contacts_1_email": "admin@olivierba.altostrat.com",
        "originalProviderId": "SHA_CUSTOM",
        "parentDisplayName": "Security Health Analytics Custom",
        "description": "DOCUMENTATION: An array indexing vulnerability was found in the netfilter subsystem of the Linux kernel. A missing macro could lead to a miscalculation of the `h->nets` array offset, providing attackers with the primitive to arbitrarily increment/decrement a memory buffer out-of-bound. This issue may allow a local user to crash the system or potentially escalate their privileges on the system.STATEMENT: Versions of `python36:3.6/python36` as shipped with Red Hat Enterprise Linux 8 are marked as 'Not affected' as they just provide \"symlinks\" to the main `python3` component, which provides the actual interpreter of the Python programming language.",
        "nextSteps": "Remove the bucket and recreated in a european region",
        "moduleName": "organizations/971363459032/securityHealthAnalyticsSettings/customModules/873688668350427895",
        "cloudProvider": "GOOGLE_CLOUD_PLATFORM",
        "muteInfo_staticMute_state": "UNDEFINED",
        "muteInfo_staticMute_applyTime": "1970-01-01T00:00:00Z",
        "resource_name": "//storage.googleapis.com/temp_01352409d637ea7f87d38ba96fa178ece019770d",
        "resource_project": "//cloudresourcemanager.googleapis.com/projects/429213313266",
        "resource_projectDisplayName": "nexus-lab-401713",
        "resource_parent": "//cloudresourcemanager.googleapis.com/projects/429213313266",
        "resource_parentDisplayName": "nexus-lab-401713",
        "resource_type": "google.cloud.storage.Bucket",
        "resource_displayName": "temp_01352409d637ea7f87d38ba96fa178ece019770d",
        "resource_cloudProvider": "GOOGLE_CLOUD_PLATFORM",
        "resource_organization": "organizations/971363459032",
        "resource_service": "storage.googleapis.com",
        "resource_location": "eu",
        "resource_resourcePath_nodes_1_nodeType": "GCP_PROJECT",
        "resource_resourcePath_nodes_1_id": "projects/429213313266",
        "resource_resourcePath_nodes_1_displayName": "nexus-lab-401713",
        "resource_resourcePath_nodes_2_nodeType": "GCP_ORGANIZATION",
        "resource_resourcePath_nodes_2_id": "organizations/971363459032",
        "resource_resourcePathString": "organizations/971363459032/projects/429213313266",
        "resource_google.cloud.storage.Bucket": "temp_01352409d637ea7f87d38ba96fa178ece019770d",
        "DeviceEventClassId": "non_eu_storage_bucket",
        "Name": "non_eu_storage_bucket",
    }


@pytest.fixture
def event_with_source_properties_and_doc_statement_mitigation_desc() -> dict[str, str]:
    yield {
        "name": "organizations/971363459032/sources/3683318981399653071/findings/85b394ed644941b67c89bacebb95da16",
        "parent": "organizations/971363459032/sources/3683318981399653071",
        "resourceName": "//compute.googleapis.com/projects/nexus-lab-401713/global/targetHttpProxies/1181954275444882742",
        "state": "ACTIVE",
        "category": "HTTP_LOAD_BALANCER",
        "externalUri": "https://console.cloud.google.com/net-services/loadbalancing/advanced/targetHttpProxies/details/http-redirect?project=nexus-lab-401713&organizationId=971363459032",
        "sourceProperties_Recommendation": 'Go to https://console.cloud.google.com/net-services/loadbalancing/advanced/targetHttpProxies/details/http-redirect?project=nexus-lab-401713&organizationId=971363459032 and click the link under the "URL map" section. It will take you to the load balancer page. Click "Edit". Click "Frontend configuration". On the right-hand side, delete all "Frontend IP and port" configurations that allow HTTP traffic and create new ones that allow HTTPS traffic.',
        "sourceProperties_ExceptionInstructions": 'Add the security mark "allow_http_load_balancer" to the asset with a value of "true" to prevent this finding from being activated again.',
        "sourceProperties_Explanation": "To protect the integrity of your data and prevent intruders from tampering with your communications, it is recommended to configure your HTTP(S) load balancers to allow only HTTPS traffic.",
        "sourceProperties_ScannerName": "COMPUTE_INSTANCE_SCANNER",
        "sourceProperties_ResourcePath_1": "projects/nexus-lab-401713/",
        "sourceProperties_ResourcePath_2": "organizations/971363459032/",
        "sourceProperties_compliance_standards_pci_1_ids_1": "2.3",
        "sourceProperties_ReactivationCount": "0.0",
        "securityMarks_name": "organizations/971363459032/sources/3683318981399653071/findings/85b394ed644941b67c89bacebb95da16/securityMarks",
        "eventTime": "2024-03-31T13:56:45.029886Z",
        "createTime": "2024-03-31T14:03:53.911Z",
        "propertyDataTypes_ResourcePath_listValues_propertyDataTypes_1_primitiveDataType": "STRING",
        "propertyDataTypes_ReactivationCount_primitiveDataType": "NUMBER",
        "propertyDataTypes_Explanation_primitiveDataType": "STRING",
        "propertyDataTypes_ScannerName_primitiveDataType": "STRING",
        "propertyDataTypes_compliance_standards_structValue_fields_pci_listValues_propertyDataTypes_1_structValue_fields_ids_listValues_propertyDataTypes_1_primitiveDataType": "STRING",
        "propertyDataTypes_ExceptionInstructions_primitiveDataType": "STRING",
        "propertyDataTypes_Recommendation_primitiveDataType": "STRING",
        "severity": "MEDIUM",
        "workflowState": "NEW",
        "canonicalName": "projects/429213313266/sources/3683318981399653071/findings/85b394ed644941b67c89bacebb95da16",
        "mute": "UNDEFINED",
        "findingClass": "MISCONFIGURATION",
        "muteUpdateTime": "1970-01-01T00:00:00Z",
        "caiResource": "//compute.googleapis.com/projects/nexus-lab-401713/global/targetHttpProxies/http-redirect",
        "contacts_security_contacts_1_email": "admin@olivierba.altostrat.com",
        "compliances_1_standard": "pci",
        "compliances_1_ids_1": "2.3",
        "originalProviderId": "SECURITY_HEALTH_ADVISOR",
        "parentDisplayName": "Security Health Analytics",
        "description": "DOCUMENTATION: An array indexing vulnerability was found in the netfilter subsystem of the Linux kernel. A missing macro could lead to a miscalculation of the `h->nets` array offset, providing attackers with the primitive to arbitrarily increment/decrement a memory buffer out-of-bound. This issue may allow a local user to crash the system or potentially escalate their privileges on the system.STATEMENT: Versions of `python36:3.6/python36` as shipped with Red Hat Enterprise Linux 8 are marked as 'Not affected' as they just provide \"symlinks\" to the main `python3` component, which provides the actual interpreter of the Python programming language. MITIGATION: Red Hat has investigated whether a possible mitigation exists for this issue, and has not been able to identify a practical example. Please update the affected package as soon as possible.",
        "cloudProvider": "GOOGLE_CLOUD_PLATFORM",
        "muteInfo_staticMute_state": "UNDEFINED",
        "muteInfo_staticMute_applyTime": "1970-01-01T00:00:00Z",
        "resource_name": "//compute.googleapis.com/projects/nexus-lab-401713/global/targetHttpProxies/http-redirect",
        "resource_project": "//cloudresourcemanager.googleapis.com/projects/429213313266",
        "resource_projectDisplayName": "nexus-lab-401713",
        "resource_parent": "//cloudresourcemanager.googleapis.com/projects/429213313266",
        "resource_parentDisplayName": "nexus-lab-401713",
        "resource_type": "google.compute.TargetHttpProxy",
        "resource_displayName": "http-redirect",
        "resource_cloudProvider": "GOOGLE_CLOUD_PLATFORM",
        "resource_organization": "organizations/971363459032",
        "resource_service": "compute.googleapis.com",
        "resource_location": "global",
        "resource_resourcePath_nodes_1_nodeType": "GCP_PROJECT",
        "resource_resourcePath_nodes_1_id": "projects/429213313266",
        "resource_resourcePath_nodes_1_displayName": "nexus-lab-401713",
        "resource_resourcePath_nodes_2_nodeType": "GCP_ORGANIZATION",
        "resource_resourcePath_nodes_2_id": "organizations/971363459032",
        "resource_resourcePathString": "organizations/971363459032/projects/429213313266",
        "resource_google.compute.TargetHttpProxy": "http-redirect",
        "DeviceEventClassId": "HTTP_LOAD_BALANCER",
        "Name": "HTTP_LOAD_BALANCER",
    }


@pytest.fixture
def aws_event_ciem():
    yield {
        "category": "ASSUMED_IDENTITY_HAS_EXCESSIVE_PERMISSIONS",
        "createTime": "2024-04-01T17:59:24.098Z",
        "description": (
            "IAM role with unused actions in their policies have excessive permissions,"
            " violating the principle of least privilege and increasing security risks"
            " \u2013 regularly review and remove unused permissions to ensure only"
            " necessary actions are allowed.\n"
        ),
        "eventTime": "2024-08-05T09:31:14.63151Z",
        "externalSystems_chronicle_soar_assignees_1": "@Vulnerability Managers",
        "externalSystems_chronicle_soar_caseCloseTime": "1970-01-01T00:00:00Z",
        "externalSystems_chronicle_soar_caseCreateTime": "1970-01-01T00:00:00Z",
        "externalSystems_chronicle_soar_casePriority": "Critical",
        "externalSystems_chronicle_soar_caseSla": "2024-04-16T07:23:26Z",
        "externalSystems_chronicle_soar_caseUri": (
            "https://cztlp.backstory-staging.chronicle.security/cases/97"
        ),
        "externalSystems_chronicle_soar_externalSystemUpdateTime": (
            "2024-04-16T07:26:45Z"
        ),
        "externalSystems_chronicle_soar_externalUid": "97",
        "externalSystems_chronicle_soar_name": (
            "organizations/493277373840/sources/17329863415806876445/"
            "findings/a2a743b3c863d7dafac949c1c29e2b17/externalSystems/chronicle_soar"
        ),
        "externalSystems_chronicle_soar_status": "Opened",
        "externalSystems_chronicle_soar_ticketInfo_assignee": "Yuriy Landovskyy",
        "externalSystems_chronicle_soar_ticketInfo_id": "SCCE-1484",
        "externalSystems_chronicle_soar_ticketInfo_status": "Open",
        "externalSystems_chronicle_soar_ticketInfo_updateTime": "2024-04-16T07:23:42Z",
        "externalSystems_chronicle_soar_ticketInfo_uri": (
            "https://siemplify.atlassian.net/browse/SCCE-1484"
        ),
        "findingClass": "MISCONFIGURATION",
        "mute": "UNDEFINED",
        "muteInfo_staticMute_applyTime": "1970-01-01T00:00:00Z",
        "muteInfo_staticMute_state": "UNDEFINED",
        "muteUpdateTime": "1970-01-01T00:00:00Z",
        "name": (
            "organizations/493277373840/sources/17329863415806876445/"
            "findings/a2a743b3c863d7dafac949c1c29e2b17"
        ),
        "nextSteps": (
            "1. You can click on the ticket ID above to view the ITSM ticket for "
            "critical and high severity findings.\n2. Or follow the steps below in "
            "the [AWS Management Console](https://console.aws.amazon.com/iam/).\n\n"
            "**Detach the old over permissive Managed IAM Policy.**\n\n* **Sign in to "
            "IAM:** Navigate to the [AWS IAM console]"
            "(https://console.aws.amazon.com/iam/) and sign in with credentials that "
            "have permissions to manage IAM users and policies.\n\n* **Locate your "
            "Identity:** In the navigation pane, choose one of \"Users\", \"Role\" or "
            "\"User groups\" and select the identity you want to attach the policy to."
            " \n * Identity ARN: `arn:aws:iam::533267318543:role/Terraform-Role`\n\n* "
            "**Open Permissions Tab:** Click on the \"Permissions\" tab for the "
            "selected identity.\n\n* **Find the Policy:** In the list of attached "
            "policies, locate the customer-managed policy you want to detach:\n * "
            "Policy ARN: `arn:aws:iam::aws:policy/AdministratorAccess`\n\n* "
            "**Detach Policy:**\n * Expand the policy name, and click on the \"Remove\""
            " button.\n * Confirm Detachment: When prompted, confirm your intention to "
            "detach the policy.\n"
        ),
        "parent": "organizations/493277373840/sources/17329863415806876445",
        "parentDisplayName": "CIEM",
        "resourceName": "arn:aws:iam::533267318543:role/Terraform-Role",
        "resource_AWS::IAM::Role": "arn:aws:iam::533267318543:role/Terraform-Role",
        "resource_cloudProvider": "AMAZON_WEB_SERVICES",
        "resource_displayName": "arn:aws:iam::533267318543:role/Terraform-Role",
        "resource_location": "global",
        "resource_name": (
            "//cloudasset.googleapis.com/organizations/493277373840/"
            "otherCloudConnections/aws/arn:aws:iam::533267318543:role/Terraform-Role"
        ),
        "resource_service": "iam",
        "resource_type": "AWS::IAM::Role",
        "securityMarks_name": (
            "organizations/493277373840/sources/17329863415806876445/"
            "findings/a2a743b3c863d7dafac949c1c29e2b17/securityMarks"
        ),
        "severity": "CRITICAL",
        "sourceProperties_DeactivationReason": "The asset was deleted.",
        "sourceProperties_Metadata_providerName": "PROVIDER_NAME_CIEM",
        "sourceProperties_Remediation_iamPolicyRemediation_operations_1_action": (
            "OPERATION_ACTION_DETACH_IAM_POLICY"
        ),
        (
            "sourceProperties_Remediation_iamPolicyRemediation_operations_1"
            "_attachmentPointName"
        ): "arn:aws:iam::533267318543:role/Terraform-Role",
        "sourceProperties_Remediation_iamPolicyRemediation_operations_1_description": (
            "Detach the old IAM Policy"
        ),
        (
            "sourceProperties_Remediation_iamPolicyRemediation_operations_1"
            "_policyResourceName"
        ): "arn:aws:iam::aws:policy/AdministratorAccess",
        "state": "ACTIVE"
      }


@pytest.fixture()
def single_non_gcp_finding_state_context() -> list[FindingContext]:
    finding_state_context = [
        {
            "finding_id": "organizations/111/sources/222/findings/333",
            "status": "ACTIVE",
            "mute": "UNMUTED",
            "aps_score": 0.25,
            "severity": "MEDIUM",
            "resource_name": "//cloudasset.googleapis.com/organizations/111/otherCloudConnections/aws/arn:aws:test/vpc-222",
            "project_display_name": None,
            "cloud_provider": "AMAZON_WEB_SERVICES",
            "alert_identifier": "VPC_FLOW_LOGGING_ENABLED_ALL_VPCS_GSCC_ORGANIZATIONS/111/SOURCES/222/FINDINGS/333_NO_CASE",
            "tc_count": 4,
            "last_update_time": 1712721375425
        }
    ]

    finding_context: list[FindingContext] = [
        FindingContext(**finding_json)
        for finding_json in finding_state_context
    ]

    yield finding_context


@pytest.fixture()
def single_gcp_finding_state_context() -> list[FindingContext]:
    finding_state_context = [
        {
            "finding_id": "organizations/111/sources/222/findings/333",
            "status": "ACTIVE",
            "mute": "UNDEFINED",
            "aps_score": None,
            "severity": "LOW",
            "resource_name": "//storage.googleapis.com/gcf-v2-sources-111-us-222",
            "project_display_name": "dlp-billing-container",
            "cloud_provider": "GOOGLE_CLOUD_PLATFORM",
            "alert_identifier": "DEPRECATED_SSL_PROTOCOL_DETECTED_GSCC_ORGANIZATIONS/111/SOURCES/222/FINDINGS/333_NO_CASE",
            "tc_count": 12,
            "last_update_time": 1712852755000
        }
    ]

    finding_context: list[FindingContext] = [
        FindingContext(**finding_json)
        for finding_json in finding_state_context
    ]

    yield finding_context


@pytest.fixture
def get_gcp_html_params() -> ParamCreatorFn:
    def do_create_html_params(event_data: SingleJson) -> SingleJson:
        param_creator: DescriptionParamsCreator = get_desc_parameter_creator(
            output_type=DescriptionOutputType.HTML,
            cloud_provider=CloudProviderEnum.GCP,
            event_data=event_data,
        )
        return param_creator.get_parameters()

    yield do_create_html_params


@pytest.fixture
def get_gcp_jwm_params() -> ParamCreatorFn:
    def do_create_html_params(event_data: SingleJson) -> SingleJson:
        param_creator: DescriptionParamsCreator = get_desc_parameter_creator(
            output_type=DescriptionOutputType.HTML,
            cloud_provider=CloudProviderEnum.GCP,
            event_data=event_data,
        )
        return param_creator.get_parameters()

    yield do_create_html_params


@pytest.fixture
def get_aws_html_params() -> ParamCreatorFn:
    def do_create_html_params(event_data: SingleJson) -> SingleJson:
        param_creator: DescriptionParamsCreator = get_desc_parameter_creator(
            output_type=DescriptionOutputType.HTML,
            cloud_provider=CloudProviderEnum.AWS,
            event_data=event_data,
        )
        return param_creator.get_parameters()

    yield do_create_html_params


@pytest.fixture
def get_aws_jwm_params() -> ParamCreatorFn:
    def do_create_html_params(event_data: SingleJson) -> SingleJson:
        param_creator: DescriptionParamsCreator = get_desc_parameter_creator(
            output_type=DescriptionOutputType.HTML,
            cloud_provider=CloudProviderEnum.AWS,
            event_data=event_data,
        )
        return param_creator.get_parameters()

    yield do_create_html_params


@pytest.fixture
def get_azure_html_params() -> ParamCreatorFn:
    def do_create_html_params(event_data: SingleJson) -> SingleJson:
        param_creator: DescriptionParamsCreator = get_desc_parameter_creator(
            output_type=DescriptionOutputType.HTML,
            cloud_provider=CloudProviderEnum.GCP,
            event_data=event_data,
        )
        return param_creator.get_parameters()

    yield do_create_html_params


@pytest.fixture
def get_azure_jwm_params() -> ParamCreatorFn:
    def do_create_html_params(event_data: SingleJson) -> SingleJson:
        param_creator: DescriptionParamsCreator = get_desc_parameter_creator(
            output_type=DescriptionOutputType.HTML,
            cloud_provider=CloudProviderEnum.GCP,
            event_data=event_data,
        )
        return param_creator.get_parameters()

    yield do_create_html_params


@pytest.fixture
def get_other_html_params() -> ParamCreatorFn:
    def do_create_html_params(event_data: SingleJson) -> SingleJson:
        param_creator: DescriptionParamsCreator = get_desc_parameter_creator(
            output_type=DescriptionOutputType.HTML,
            cloud_provider=CloudProviderEnum.OTHER,
            event_data=event_data,
        )
        return param_creator.get_parameters()

    yield do_create_html_params


@pytest.fixture
def get_other_jwm_params() -> ParamCreatorFn:
    def do_create_html_params(event_data: SingleJson) -> SingleJson:
        param_creator: DescriptionParamsCreator = get_desc_parameter_creator(
            output_type=DescriptionOutputType.HTML,
            cloud_provider=CloudProviderEnum.OTHER,
            event_data=event_data,
        )
        return param_creator.get_parameters()

    yield do_create_html_params


@pytest.fixture
def html_create_desc_fn() -> CreateDescFn:
    yield get_create_desc_fn(DescriptionOutputType.HTML)


@pytest.fixture
def jwm_create_desc_fn() -> CreateDescFn:
    yield get_create_desc_fn(DescriptionOutputType.JWM)


@pytest.fixture
def parse_markdown_to_html(event_keys_and_values: SingleJson) -> ParseStringFn:
    param_creator: DescriptionParamsCreator = get_desc_parameter_creator(
        output_type=DescriptionOutputType.HTML,
        cloud_provider=CloudProviderEnum.OTHER,
        event_data=event_keys_and_values,
    )
    yield param_creator.parse_markdown_fn


@pytest.fixture
def parse_markdown_to_jwm(event_keys_and_values: SingleJson) -> ParseStringFn:
    param_creator: DescriptionParamsCreator = get_desc_parameter_creator(
        output_type=DescriptionOutputType.JWM,
        cloud_provider=CloudProviderEnum.OTHER,
        event_data=event_keys_and_values,
    )
    yield param_creator.parse_markdown_fn
