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
from .datamodels import Finding, CustomDataIdentifier


class AmazonMacieParser:
    """
    Amazon Macie Transformation Layer.
    """

    @staticmethod
    def build_siemplify_finding_obj(raw_data):
        """
        :param raw_data: raw json response of single element in 'Findings' raw data response
        :return: Finding data model.
        """
        return Finding(
            raw_data,
            title=raw_data.get("title"),
            type=raw_data.get("type"),
            created_at=raw_data.get("createdAt"),
            updated_at=raw_data.get("updatedAt"),
            description=raw_data.get("description"),
            category=raw_data.get("category"),
            finding_id=raw_data.get("id"),
            account_id=raw_data.get("accountId"),
            archived=raw_data.get("archived"),
            severity=raw_data.get("severity", {}).get("description"),
            score=raw_data.get("severity", {}).get("score"),
            count=raw_data.get("count"),
        )

    @staticmethod
    def build_siemplify_data_identifier(raw_data):
        return CustomDataIdentifier(
            raw_data=raw_data, id=raw_data.get("customDataIdentifierId")
        )
