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

from collections.abc import Iterable

from integration_testing import router
from integration_testing.request import MockRequest
from integration_testing.requests.response import MockResponse
from integration_testing.requests.session import MockSession, RouteFunction

from wiz.core import constants
from .. import common
from tests.core.product import Wiz

if TYPE_CHECKING:
    from TIPCommon.types import SingleJson
    from wiz.core import datamodels


class WizSession(MockSession[MockRequest, MockResponse, Wiz]):
    def get_routed_functions(self) -> Iterable[RouteFunction]:
        return [self.graphql_query, get_oauth_token]

    @router.post(r".*/graphql")
    def graphql_query(self, request: MockRequest) -> MockResponse:
        """Handle GET .*/1.0/alerts/ requests"""
        query: SingleJson = request.kwargs["json"]["query"]
        status: str = (
            request.kwargs.get("json", {}).get("variables", {}).get("patch", {}).get("status", "")
        )
        if common.GET_ISSUE_QUERY_NAME in query or "first: 1" in query:
            return self._get_issue_details()
        if common.ADD_COMMENT_QUERY_NAME in query:
            return self._add_comment_to_issue()
        if common.UPDATE_ISSUE_QUERY_NAME in query:
            if constants.STATUS_REOPEN == status:
                return self._reopen_issue()
            if constants.STATUS_REJECTED == status:
                return self._ignore_issue()

            return self._resolve_issue()

        return MockResponse(
            content={"errors": [{"message": "Invalid query"}]},
            status_code=400,
        )

    def _get_issue_details(self) -> MockResponse:
        """Handle get issue details request's response."""
        issue: datamodels.Issue = self._product.get_issues()[0]
        invalid_response = handle_invalid_response(issue.issue_id)
        if invalid_response is not None:
            return invalid_response

        return MockResponse(
            content={"data": {"issue": issue.to_json()}},
            status_code=200,
        )

    def _add_comment_to_issue(self) -> MockResponse:
        """Handle add comment to issue request's response."""
        issue: datamodels.Issue = self._product.get_issues()[0]
        invalid_response: MockResponse = handle_invalid_response(issue_id=issue.issue_id)
        if invalid_response is not None:
            return invalid_response
        comment: common.Comment = self._product.get_comment(issue.issue_id)
        comment.is_comment = True

        return MockResponse(content=common.ADD_COMMENT_TO_ISSUE, status_code=200)

    def _reopen_issue(self) -> MockResponse:
        """Handle reopen issue request's response."""
        issue: common.IssueStatus = self._product.get_issues()[0]
        invalid_response: MockResponse = handle_invalid_response(issue_id=issue.issue_id)
        if invalid_response is not None:
            return invalid_response
        issue.status = constants.STATUS_REOPEN

        return MockResponse(content=common.REOPEN_ISSUE, status_code=200)

    def _ignore_issue(self) -> MockResponse:
        """Handle reopen issue request's response."""
        issue: common.IssueStatus = self._product.get_issues()[0]
        invalid_response: MockResponse = handle_invalid_response(issue_id=issue.issue_id)
        if invalid_response is not None:
            return invalid_response
        issue.status = constants.STATUS_REJECTED

        return MockResponse(content=common.IGNORE_ISSUE, status_code=200)

    def _resolve_issue(self) -> MockResponse:
        """Handle reopen issue request's response."""
        issue: common.IssueStatus = self._product.get_issues()[0]
        invalid_response: MockResponse = handle_invalid_response(issue_id=issue.issue_id)
        if invalid_response is not None:
            return invalid_response
        issue.status = constants.STATUS_RESOLVED

        return MockResponse(content=common.RESOLVE_ISSUE, status_code=200)


@router.post("/oauth/token")
def get_oauth_token(request: MockRequest) -> MockResponse:
    """Get an OAuth token"""
    if "raise_error" in request.kwargs["data"].values():
        return MockResponse(
            content=common.INVALID_TOKEN,
            status_code=400,
        )

    return MockResponse(common.VALID_TOKEN, status_code=200)


def handle_invalid_response(issue_id) -> MockResponse | None:
    """Handle invalid response."""
    match issue_id:
        case str(common.INVALID_ISSUE_ID):
            return MockResponse(content=common.INVALID_ISSUE, status_code=200)
        case common.INVALID_TOKEN_ID:
            return MockResponse(content=common.INVALID_TOKEN, status_code=401)

    return None
