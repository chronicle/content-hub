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

from typing import TYPE_CHECKING

from . import datamodels

if TYPE_CHECKING:
    from TIPCommon.types import SingleJson


def build_issue_object(issue_json: SingleJson) -> datamodels.Issue:
    """Build an Issue object from the provided JSON data.

    Args:
        issue_json: The JSON data containing issue details.

    Returns:
        An Issue object containing the details of the issue.
    """
    return datamodels.Issue.from_json(issue_json.get("data", {}).get("issue", {}))


def build_update_issue_object(issue_json: SingleJson) -> datamodels.Issue:
    """Build an Update Issue object from the provided JSON data.

    Args:
        issue_json: The JSON data containing updated issue details.

    Returns:
        An Issue object containing the details of the updated issue.
    """
    return datamodels.Issue.from_json(issue_json.get("data", {}).get("updateIssue", {}).get("issue", {}))


def build_issue_comment_object(issue_json: SingleJson) -> datamodels.IssueComment:
    """Build an Issue Comment object from the provided JSON data.

    Args:
        issue_json: The JSON data containing commented issue details.

    Returns:
        The commented issue details.
    """
    return datamodels.IssueComment.from_json(issue_json.get("data", {}).get("createIssueNote", {}).get("issueNote", {}))


def build_vulnerability_finding_object(
    finding_json: SingleJson,
) -> datamodels.VulnerabilityFinding:
    """Build a VulnerabilityFinding object from the provided JSON data.

    Args:
        finding_json: The JSON data containing finding details.

    Returns:
        A VulnerabilityFinding object.
    """
    return datamodels.VulnerabilityFinding.from_json(finding_json)


def build_threat_ai_analysis_object(
    response_json: SingleJson,
) -> datamodels.ThreatAIAnalysis | None:
    """Build a ThreatAIAnalysis object from the provided JSON data.

    Args:
        response_json: The JSON response data containing threat detection details.

    Returns:
        A ThreatAIAnalysis object or None if aiAnalysis is not present.
    """
    issue_data = response_json.get("data", {}).get("issue")

    if issue_data is None:
        return None

    threat_details = issue_data.get("threatDetectionDetails")

    if not threat_details:
        return None

    ai_analysis = threat_details.get("aiAnalysis")
    return datamodels.ThreatAIAnalysis.from_json(response_json, ai_analysis)
