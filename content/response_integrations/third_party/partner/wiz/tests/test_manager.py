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
import copy

import pytest
from wiz.core import constants
from wiz.core.exceptions import InvalidCredsError, IssueNotFoundError
from . import common

if TYPE_CHECKING:
    from wiz.core.api_client import WizApiClient
    from wiz.core.datamodels import Issue
    from tests.core.product import Wiz
    from tests.core.session import WizSession


ISSUE: Issue = common.ISSUE


class TestApiManager:
    """Unit tests for Integration's WizApiClient methods."""

    def test_ping_success(
        self,
        manager: WizApiClient,
        wiz: Wiz,
        script_session: WizSession,
    ) -> None:
        """Test ping success.

        Verify that the test_connectivity method successfully pings the Wiz API and
        returns a 200 status code.

        Args:
            manager (WizApiClient): WizApiClient object.
            wiz (Wiz): Wiz product object.
            script_session (WizSession): WizSession object.
        """
        wiz.cleanup_issues()
        issue: Issue = copy.deepcopy(ISSUE)
        wiz.add_issue(issue)

        manager.test_connectivity()

        assert len(script_session.request_history) == 1
        assert script_session.request_history[0].response.status_code == 200

    def test_ping_failure_invalid_token(
        self,
        manager: WizApiClient,
        wiz: Wiz,
        script_session: WizSession,
    ) -> None:
        """Test ping failure due to invalid token.

        Args:
            manager (WizApiClient): WizApiClient object.
            wiz (Wiz): Wiz product object.
            script_session (WizSession): WizSession object.
        """
        wiz.cleanup_issues()
        issue: Issue = copy.deepcopy(ISSUE)
        issue.issue_id: str = common.INVALID_TOKEN_ID
        wiz.add_issue(issue)

        expected_error_message_regex = (
            r"Invalid credentials provided\. "
            r"Please check the integration configuration\."
        )

        with pytest.raises(InvalidCredsError, match=expected_error_message_regex):
            manager.test_connectivity()

        assert len(script_session.request_history) == 1
        assert script_session.request_history[0].response.status_code == 401
        assert script_session.request_history[0].response.json() == common.INVALID_TOKEN

    def test_get_issue_details_success(
        self,
        manager: WizApiClient,
        wiz: Wiz,
        script_session: WizSession,
    ) -> None:
        """Test get issue details success.

        Verify that the get_issue_details method successfully retrieves issue details
        and returns a 200 status code.

        Args:
            manager (WizApiClient): WizApiClient object.
            wiz (Wiz): Wiz product object.
            script_session (WizSession): WizSession object.
        """
        wiz.cleanup_issues()
        issue: Issue = copy.deepcopy(ISSUE)
        issue_id: str = issue.issue_id
        wiz.add_issue(issue)

        manager.get_issue_details(issue_id=issue_id)

        assert len(script_session.request_history) == 1
        assert script_session.request_history[0].response.status_code == 200
        assert script_session.request_history[0].response.json() == {
            "data": {"issue": issue.to_json()}
        }

    def test_get_issue_details_failure(
        self,
        manager: WizApiClient,
        wiz: Wiz,
        script_session: WizSession,
    ) -> None:
        """Test get issue details failure due to invalid token.

        Args:
            manager (WizApiClient): WizApiClient object.
            wiz (Wiz): Wiz product object.
            script_session (WizSession): WizSession object.
        """
        wiz.cleanup_issues()
        issue: Issue = copy.deepcopy(ISSUE)
        issue.issue_id: str = common.INVALID_ISSUE_ID
        wiz.add_issue(issue)
        expected_error_message_regex = r"id must be a valid service issue id"

        with pytest.raises(IssueNotFoundError, match=expected_error_message_regex):
            manager.get_issue_details(issue.issue_id)

        assert len(script_session.request_history) == 1
        assert script_session.request_history[0].response.status_code == 200
        assert script_session.request_history[0].response.json() == common.INVALID_ISSUE

    def test_add_comment_to_issue_success(
        self,
        manager: WizApiClient,
        wiz: Wiz,
        script_session: WizSession,
    ) -> None:
        """Test add comment to issue success.

        Verify that the add_comment_to_issue method successfully adds a comment to an
        issue and returns a 200 status code.

        Args:
            manager (WizApiClient): WizApiClient object.
            wiz (Wiz): Wiz product object.
            script_session (WizSession): WizSession object.
        """
        wiz.cleanup_issues()
        issue: Issue = copy.deepcopy(ISSUE)
        issue_id: str = issue.issue_id
        comment: common.Comment = common.Comment(
            issue_id=issue_id,
            comment=common.TEST_COMMENT,
        )
        wiz.add_issue(issue)
        wiz.add_comment(comment)

        manager.add_comment_to_issue(
            issue_id=issue_id,
            comment=comment.comment,
        )

        assert comment.is_comment is True
        assert len(script_session.request_history) == 1
        assert script_session.request_history[0].response.status_code == 200
        assert script_session.request_history[0].response.json() == common.ADD_COMMENT_TO_ISSUE

    def test_reopen_issue_success(
        self,
        manager: WizApiClient,
        wiz: Wiz,
        script_session: WizSession,
    ) -> None:
        """Test reopen issue success.

        Verify that the reopen_issue method successfully reopens an issue and returns a
        200 status code.

        Args:
            manager (WizApiClient): WizApiClient object.
            wiz (Wiz): Wiz product object.
            script_session (WizSession): WizSession object.
        """
        wiz.cleanup_issues()
        issue: common.IssueStatus = common.IssueStatus(issue_id="test_issue_id")
        issue_id = issue.issue_id
        wiz.add_issue(issue)

        manager.reopen_issue(issue_id=issue_id)

        assert issue.status == constants.STATUS_REOPEN
        assert len(script_session.request_history) == 1
        assert script_session.request_history[0].response.status_code == 200
        assert script_session.request_history[0].response.json() == common.REOPEN_ISSUE

    def test_ignore_issue_success(
        self,
        manager: WizApiClient,
        wiz: Wiz,
        script_session: WizSession,
    ) -> None:
        """Test reopen issue success.

        Verify that the reopen_issue method successfully reopens an issue and returns a
        200 status code.

        Args:
            manager (WizApiClient): WizApiClient object.
            wiz (Wiz): Wiz product object.
            script_session (WizSession): WizSession object.
        """
        wiz.cleanup_issues()
        issue: common.IssueStatus = common.IssueStatus(issue_id="test_issue_id")
        issue_id: str = issue.issue_id
        wiz.add_issue(issue)

        manager.ignore_issue(
            issue_id=issue_id,
            resolution_reason="False Positive",
            note="Test ignore note",
        )

        assert issue.status == constants.STATUS_REJECTED
        assert len(script_session.request_history) == 1
        assert script_session.request_history[0].response.status_code == 200
        assert script_session.request_history[0].response.json() == common.IGNORE_ISSUE

    def test_resolve_issue_success(
        self,
        manager: WizApiClient,
        wiz: Wiz,
        script_session: WizSession,
    ) -> None:
        """Test reopen issue success.

        Verify that the reopen_issue method successfully reopens an issue and returns a
        200 status code.

        Args:
            manager (WizApiClient): WizApiClient object.
            wiz (Wiz): Wiz product object.
            script_session (WizSession): WizSession object.
        """
        wiz.cleanup_issues()
        issue: common.IssueStatus = common.IssueStatus(issue_id="test_issue_id")
        issue_id: str = issue.issue_id
        wiz.add_issue(issue)

        manager.resolve_issue(
            issue_id=issue_id,
            resolution_note="Test resolution note",
            resolution_reason="Malicious Threat",
        )

        assert issue.status == constants.STATUS_RESOLVED
        assert len(script_session.request_history) == 1
        assert script_session.request_history[0].response.status_code == 200
        assert script_session.request_history[0].response.json() == common.RESOLVE_ISSUE
