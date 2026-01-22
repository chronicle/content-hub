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

from .data_models import CaseAttachment, CaseComment
from ...types import SingleJson


def parse_case_attachment(attachment: SingleJson) -> CaseAttachment:
    """
    Parses a JSON attachment and returns a CaseAttachment object.

    Args:
        attachment: A response JSON object representing the attachment.

    Returns:
        The parsed `CaseAttachment` object.

    """
    return CaseAttachment(
        attachment_id=attachment.get('id', -1),
        attachment_type=attachment.get('type', 'No type was found'),
        description=attachment.get('description', 'No description was found'),
        is_favorite=attachment.get('is_favorite', False)
    )


def parse_case_comment(comment: SingleJson) -> CaseComment:
    """
    Parses a JSON comment and returns a CaseComment object.

    Args:
        comment: A response JSON object representing the comment.

    Returns:
       The parsed `CaseComment` object.

    """
    return CaseComment(
        comment=comment.get('comment', ''),
        creator_user_id=comment.get('creator_user_id', 'No user ID found'),
        comment_id=comment.get('comment_id', -1),
        comment_type=comment.get('comment_type', -1),
        case_id=comment.get('case_id', -1),
        is_favorite=comment.get('is_favorite', False),
        modification_time_unix_time_in_ms=comment.get(
            'modification_time_unix_time_in_ms', -1
        ),
        creation_time_unix_time_in_ms=comment.get(
            'creation_time_unix_time_in_ms', -1
        ),
        alert_identifier=comment.get('alert_identifier', 'No identifier found'),
        creator_full_name=comment.get('creator_full_name'),
        is_deleted=comment.get('is_deleted'),
        last_editor=comment.get('last_editor'),
        last_editor_full_name=comment.get('last_editor_full_name'),
        modification_time_unix_time_in_ms_for_client=comment.get(
            'modification_time_unix_time_in_ms_for_client'
        ),
        comment_for_client=comment.get('comment_for_client'),
    )
