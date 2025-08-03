from __future__ import annotations

from typing import TYPE_CHECKING

import dataclasses
import requests

from . import api_utils
from . import constants
from . import datamodels
from . import data_parser
from . import query_builder

if TYPE_CHECKING:
    from collections.abc import Mapping
    from TIPCommon.base.interfaces.logger import ScriptLogger


@dataclasses.dataclass(slots=True)
class ApiParameters:
    api_root: str


class ApiManager:
    def __init__(
        self,
        session: requests.Session,
        api_parameters: ApiParameters,
        logger: ScriptLogger,
    ) -> None:
        self.session: requests.Session = session
        self.api_root: str = api_parameters.api_root
        self.logger: ScriptLogger = logger
        self.parser: data_parser = data_parser

    def test_connectivity(self) -> None:
        """Test the connectivity to the Wiz API."""
        graphql_query: Mapping[str, str] = {
            "query": """
        query {
            issues(first: 1) {
                nodes { id }
            }
        }
        """
        }
        url: str = api_utils.get_full_url(
            api_root=self.api_root,
            url_id="graphql",
        )
        response: requests.Response = self.session.post(url=url, json=graphql_query)
        api_utils.validate_response(response=response)

    def get_issue_details(self, issue_id: str) -> datamodels.Issue:
        """Get details of a specific issue by its ID using graphql_query lib.

        Args:
            issue_id (str): The ID of the issue to retrieve details for.

        Returns:
            datamodels.Issue: An Issue object containing the details of the issue.
        """
        issue_query_builder: query_builder.IssueQueryBuilder = query_builder.IssueQueryBuilder(
            issue_id=issue_id
        )

        url: str = api_utils.get_full_url(
            api_root=self.api_root,
            url_id="graphql",
        )
        response: requests.Response = self.session.post(
            url=url,
            json=issue_query_builder.build_query(),
        )
        api_utils.validate_response(response=response)

        return self.parser.build_issue_object(response.json())

    def add_comment_to_issue(
        self,
        issue_id: str,
        comment: str,
    ) -> datamodels.IssueComment:
        """Add a comment to an issue.

        Args:
            issue_id (str): The ID of the issue to add a comment to.
            comment (str): The comment to add to the issue.

        Returns:
            datamodels.IssueComment: An issue object containing details of the commented
            issue.
        """
        mutation_query: query_builder.AddCommentThreadMutationBuilder = (
            query_builder.AddCommentThreadMutationBuilder(
                issue_id=issue_id,
                comment=comment,
            )
        )
        url: str = api_utils.get_full_url(
            api_root=self.api_root,
            url_id="graphql",
        )
        response: requests.Response = self.session.post(
            url=url,
            json=mutation_query.build_mutation(),
        )
        api_utils.validate_response(response=response)

        return self.parser.build_issue_comment_object(response.json())

    def reopen_issue(self, issue_id: str) -> datamodels.Issue:
        """Reopen an issue.

        Args:
            issue_id (str): The ID of the issue to reopen.

        Returns:
            datamodels.Issue: An Issue object containing the details of the reopened
            issue.
        """
        mutation_query: query_builder.UpdateIssueMutationBuilder = (
            query_builder.UpdateIssueMutationBuilder(
                issue_id=issue_id,
                patch=query_builder.UpdateIssuePatch(
                    status=constants.STATUS_REOPEN,
                ),
            )
        )
        url: str = api_utils.get_full_url(
            api_root=self.api_root,
            url_id="graphql",
        )
        response: requests.Response = self.session.post(
            url=url,
            json=mutation_query.build_mutation(),
        )
        api_utils.validate_response(response=response)

        return self.parser.build_update_issue_object(response.json())

    def ignore_issue(
        self,
        issue_id: str,
        resolution_reason: str,
        note: str | None = None,
    ) -> datamodels.Issue:
        """Reject an issue.

        Args:
            issue_id (str): The ID of the issue to reject.
            resolution_reason (str): The reason for rejecting the issue.
            note (str | None): An optional note to add to the rejection.

        Returns:
            datamodels.Issue: An Issue object containing the details of the rejected
            issue.
        """
        mutation_query: query_builder.UpdateIssueMutationBuilder = (
            query_builder.UpdateIssueMutationBuilder(
                issue_id=issue_id,
                patch=query_builder.UpdateIssuePatch(
                    status=constants.STATUS_REJECTED,
                    resolution_reason=constants.IGNORE_ISSUE_RESOLUTION_REASONS[resolution_reason],
                    note=note,
                ),
            )
        )
        url: str = api_utils.get_full_url(
            api_root=self.api_root,
            url_id="graphql",
        )
        response: requests.Response = self.session.post(
            url=url,
            json=mutation_query.build_mutation(),
        )
        api_utils.validate_response(response=response)

        return self.parser.build_update_issue_object(response.json())

    def resolve_issue(
        self,
        issue_id: str,
        resolution_reason: str,
        resolution_note: str | None = None,
    ) -> datamodels.Issue:
        """Resolve an issue.

        Args:
            issue_id (str): The ID of the issue to resolve.
            resolution_reason (str): The reason for resolving the issue.
            resolution_note (str | None): An optional note to add to the resolution.

        Returns:
            datamodels.Issue: An Issue object containing the details of the resolved
            issue.
        """
        mutation_query: query_builder.UpdateIssueMutationBuilder = (
            query_builder.UpdateIssueMutationBuilder(
                issue_id=issue_id,
                patch=query_builder.UpdateIssuePatch(
                    status=constants.STATUS_RESOLVED,
                    resolution_reason=constants.RESOLVE_ISSUE_RESOLUTION_REASONS[resolution_reason],
                    resolution_note=resolution_note,
                ),
                return_note_field=True,
            )
        )
        url: str = api_utils.get_full_url(
            api_root=self.api_root,
            url_id="graphql",
        )
        response: requests.Response = self.session.post(
            url=url,
            json=mutation_query.build_mutation(),
        )
        api_utils.validate_response(response=response)

        return self.parser.build_update_issue_object(response.json())
