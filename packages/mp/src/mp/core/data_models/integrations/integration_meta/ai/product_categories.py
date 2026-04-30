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

import enum
from typing import Annotated

from pydantic import BaseModel, Field


class IntegrationProductCategories(BaseModel):
    reasoning: Annotated[
        str,
        Field(
            title="Categorization Reasoning",
            description=(
                "Step-by-step reasoning evaluating the integration against all available product "
                "categories. Explicitly state why the integration matches or does not match the "
                "criteria of relevant categories before setting their boolean flags."
            ),
        ),
    ]
    siem: Annotated[
        bool,
        Field(
            title="SIEM",
            description=(
                "When to Use:"
                " Use when you need to find the activity related to Assets,"
                " Users or see if an IOC has been seen globally across your logs in the last 90"
                " days."
                " Expected Outcome:"
                " Returns a timeline of activity, lists all internal assets that touched an IOC,"
                " and identifies source of the suspicious activity"
            ),
        ),
    ]
    edr: Annotated[
        bool,
        Field(
            title="EDR",
            description=(
                "When to Use:"
                " Use when the investigation involves a specific host (workstation/server) and you"
                " need to see deep process-level activity."
                " Expected Outcome:"
                " Returns the process tree (Parent/Child), retrieves suspicious files for analysis,"
                " or contains the host by isolating it from the network."
            ),
        ),
    ]
    network_security: Annotated[
        bool,
        Field(
            title="Network Security",
            description=(
                "When to Use:"
                " Use when an internal asset is communicating with a known malicious external IP or"
                " to verify if a web-based attack was blocked."
                " Expected Outcome:"
                " Returns firewall/WAF permit/deny logs and allows the agent to block malicious"
                " IPs/URLs at the gateway."
            ),
        ),
    ]
    threat_intelligence: Annotated[
        bool,
        Field(
            title="Threat Intelligence",
            description=(
                "When to Use:"
                " Use as the first step of enrichment for any external indicator (IP, Hash, URL) to"
                " determine its reputation."
                " Expected Outcome:"
                " Returns risk scores, malware family names, and historical 'last seen' data to"
                " confirm if an alert is a True Positive."
            ),
        ),
    ]
    email_security: Annotated[
        bool,
        Field(
            title="Email Security",
            description=(
                "When to Use:"
                " Use when the alert involves a phishing report, a suspicious attachment, or a link"
                " delivered via email."
                " Expected Outcome:"
                " Returns a list of all affected users who received the same email and allows the"
                " agent to manage emails in all inboxes."
            ),
        ),
    ]
    iam_and_identity_management: Annotated[
        bool,
        Field(
            title="IAM & Identity Management",
            description=(
                "When to Use:"
                ' Use when a user account is showing suspicious behavior ("Impossible Travel,"'
                " credential stuffing, or unauthorized privilege escalation) and you want to manage"
                " identity."
                " Expected Outcome:"
                " Returns user or identity group/privilege levels and allows the agent to suspend"
                " accounts, force password resets, reset service accounts."
            ),
        ),
    ]
    cloud_security: Annotated[
        bool,
        Field(
            title="Cloud Security",
            description=(
                "When to Use: Use for alerts involving cloud-native resources GCP/AWS/Azure."
                " Expected Outcome:"
                " Returns resource configuration states, findings and identifies rogue cloud"
                " instances or API keys."
            ),
        ),
    ]
    itsm: Annotated[
        bool,
        Field(
            title="ITSM",
            description=(
                "When to Use: Use to document the investigation, assign tasks to other teams."
                " Expected Outcome:"
                " Creates/updates tickets, assigns tasks to specific departments."
            ),
        ),
    ]
    vulnerability_management: Annotated[
        bool,
        Field(
            title="Vulnerability Management",
            description=(
                "When to Use:"
                " Use to verify if a targeted asset is actually susceptible to the exploit seen in"
                " the alert."
                " Expected Outcome:"
                " Returns CVE information and a list of missing patches on the target host to"
                " determine if the attack had a high probability of success."
            ),
        ),
    ]
    asset_inventory: Annotated[
        bool,
        Field(
            title="Asset Inventory",
            description=(
                "When to Use:"
                " Use when you want to get more information about an internal asset."
                " Expected Outcome:"
                " Returns the asset owner, department, business criticality, and whether the device"
                " is managed by IT."
            ),
        ),
    ]
    collaboration: Annotated[
        bool,
        Field(
            title="Collaboration",
            description=(
                "When to Use: "
                'Use when an automated action requires a "Human-in-the-Loop" approval or when the'
                " SOC needs to be notified of a critical find."
                " Expected Outcome:"
                " Sends interactive alerts to Slack/Teams for manual approval and notifies"
                " stakeholders of critical findings."
            ),
        ),
    ]


class IntegrationProductCategory(enum.StrEnum):
    SIEM = "SIEM"
    EDR = "EDR"
    NETWORK_SECURITY = "Network Security"
    THREAT_INTELLIGENCE = "Threat Intelligence"
    EMAIL_SECURITY = "Email Security"
    IAM_AND_IDENTITY_MANAGEMENT = "IAM & Identity Management"
    CLOUD_SECURITY = "Cloud Security"
    ITSM = "ITSM"
    VULNERABILITY_MANAGEMENT = "Vulnerability Management"
    ASSET_INVENTORY = "Asset Inventory"
    COLLABORATION = "Collaboration"


PRODUCT_CATEGORY_TO_DEF_PRODUCT_CATEGORY: dict[str, IntegrationProductCategory] = {
    "siem": IntegrationProductCategory.SIEM,
    "edr": IntegrationProductCategory.EDR,
    "network_security": IntegrationProductCategory.NETWORK_SECURITY,
    "threat_intelligence": IntegrationProductCategory.THREAT_INTELLIGENCE,
    "email_security": IntegrationProductCategory.EMAIL_SECURITY,
    "iam_and_identity_management": IntegrationProductCategory.IAM_AND_IDENTITY_MANAGEMENT,
    "cloud_security": IntegrationProductCategory.CLOUD_SECURITY,
    "itsm": IntegrationProductCategory.ITSM,
    "vulnerability_management": IntegrationProductCategory.VULNERABILITY_MANAGEMENT,
    "asset_inventory": IntegrationProductCategory.ASSET_INVENTORY,
    "collaboration": IntegrationProductCategory.COLLABORATION,
}
