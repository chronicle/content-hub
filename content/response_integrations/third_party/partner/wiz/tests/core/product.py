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

from .. import common

if TYPE_CHECKING:
    from collections.abc import Iterable, MutableMapping

    from TIPCommon.types import SingleJson

    from wiz.core.datamodels import Issue


class Wiz:
    def __init__(self) -> None:
        self._issues: MutableMapping[str, Issue] = {}
        self._comments: MutableMapping[str, common.Comment] = {}

    def add_issue(self, issue: Issue) -> None:
        self._issues[issue.issue_id] = issue

    def get_issue(self, issue_id: str) -> Issue:
        return self._issues[issue_id]

    def get_issues(self) -> Iterable[Issue]:
        return list(self._issues.values())

    def get_comment(self, issue_id: str) -> SingleJson:
        return self._comments[issue_id]

    def add_comment(self, comment: common.Comment) -> None:
        self._comments[comment.issue_id] = comment

    def cleanup_issues(self) -> None:
        self._issues = {}
