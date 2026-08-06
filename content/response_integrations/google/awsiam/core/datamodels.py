# Copyright 2026 Google LLC
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

from typing import Any


class User:
    """
    User data model
    """

    def __init__(
        self,
        raw_data,
        path=None,
        username=None,
        user_id=None,
        arn=None,
        create_date=None
    ):
        self.raw_data = raw_data
        self.path = path
        self.username = username
        self.user_id = user_id
        self.arn = arn
        self.create_date = create_date

    def as_json(self):
        return {
            "Arn": self.arn,
            "CreateDate": self.create_date,
            "Path": self.path,
            "UserId": self.user_id,
            "UserName": self.username,
        }

    def as_csv(self):
        return {
            "User Name": self.username,
            "User ID": self.user_id,
            "ARN": self.arn,
            "Creation Date": self.create_date,
        }

    @classmethod
    def from_json(cls, user_json: dict[str, Any]) -> User:
        return cls(
            raw_data=user_json,
            path=user_json.get("Path", user_json.get("path")),
            username=user_json.get("UserName", user_json.get("username")),
            user_id=user_json.get("UserId", user_json.get("user_id")),
            arn=user_json.get("Arn", user_json.get("arn")),
            create_date=user_json.get("CreateDate", user_json.get("create_date")),
        )


class Group:
    """
    Group data model
    """

    def __init__(
        self,
        raw_data,
        path=None,
        group_name=None,
        group_id=None,
        arn=None,
        create_date=None
    ):
        self.raw_data = raw_data
        self.path = path
        self.group_name = group_name
        self.group_id = group_id
        self.arn = arn
        self.create_date = create_date

    def as_json(self):
        return {
            "Arn": self.arn,
            "CreateDate": self.create_date,
            "Path": self.path,
            "GroupId": self.group_id,
            "GroupName": self.group_name,
        }

    def as_csv(self):
        return {
            "Group Name": self.group_name,
            "Group ID": self.group_id,
            "ARN": self.arn,
            "Creation Date": self.create_date,
        }

    @classmethod
    def from_json(cls, group_json: dict[str, Any]) -> User:
        return cls(
            raw_data=group_json,
            path=group_json.get("Path", group_json.get("path")),
            group_name=group_json.get("GroupName", group_json.get("group_name")),
            group_id=group_json.get("GroupId", group_json.get("group_id")),
            arn=group_json.get("Arn", group_json.get("arn")),
            create_date=group_json.get("CreateDate", group_json.get("create_date")),
        )


class Policy:
    """
    AWS IAM Policy data model.
    """

    def __init__(
        self,
        raw_data,
        policy_name=None,
        policy_id=None,
        arn=None,
        path=None,
        default_version_id=None,
        attachment_count=None,
        permission_boundary_usage_count=None,
        is_attachable=None,
        description=None,
        create_date=None,
        update_date=None,
    ):
        self.raw_data = raw_data
        self.policy_name = policy_name
        self.policy_id = policy_id
        self.arn = arn
        self.path = path
        self.default_version_id = default_version_id
        self.attachment_count = attachment_count
        self.permission_boundary_usage_count = permission_boundary_usage_count
        self.is_attachable = is_attachable
        self.description = description
        self.create_date = create_date  # datetime.datetime object
        self.update_date = update_date  # datetime.datetime object

    def as_json(self):
        return {
            "PolicyName": self.policy_name,
            "PolicyId": self.policy_id,
            "Arn": self.arn,
            "Path": self.path,
            "DefaultVersionId": self.default_version_id,
            "AttachmentCount": self.attachment_count,
            "PermissionsBoundaryUsageCount": self.permission_boundary_usage_count,
            "IsAttachable": self.is_attachable,
            "Description": self.description,
            "CreateDate": self.create_date,
            "UpdateDate": self.update_date,
        }

    def as_csv(self):
        return {
            "Policy Name": self.policy_name,
            "Policy ID": self.policy_id,
            "Create Date": self.create_date,
            "Update Date": self.update_date,
        }

    @classmethod
    def from_json(cls, policy_json: dict[str, Any]) -> User:
        return cls(
            raw_data=policy_json,
            policy_name=policy_json.get("PolicyName", policy_json.get("policy_name")),
            policy_id=policy_json.get("PolicyId", policy_json.get("policy_id")),
            arn=policy_json.get("Arn", policy_json.get("arn")),
            path=policy_json.get("Path", policy_json.get("path")),
            default_version_id=policy_json.get(
                "DefaultVersionId", policy_json.get("default_version_id")
            ),
            attachment_count=policy_json.get(
                "AttachmentCount", policy_json.get("attachment_count")
            ),
            permission_boundary_usage_count=policy_json.get(
                "PermissionsBoundaryUsageCount",
                policy_json.get("permission_boundary_usage_count"),
            ),
            is_attachable=policy_json.get(
                "IsAttachable", policy_json.get("is_attachable")
            ),
            description=policy_json.get("Description", policy_json.get("description")),
            create_date=policy_json.get("CreateDate", policy_json.get("create_date")),
            update_date=policy_json.get("UpdateDate", policy_json.get("update_date")),
        )
