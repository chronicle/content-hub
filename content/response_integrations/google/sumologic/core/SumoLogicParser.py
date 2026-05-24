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
from typing import List

from .datamodels import JobInfo, SearchMessage


class SumoLogicParser:
    """
    Sumo Logic Transformation Layer.
    """

    @staticmethod
    def get_search_job_id(raw_data) -> str:
        return raw_data.get("id")

    @staticmethod
    def build_job_info_obj(raw_data) -> JobInfo:
        return JobInfo(
            raw_data=raw_data,
            state=raw_data.get("state"),
            message_count=raw_data.get("messageCount"),
        )

    @staticmethod
    def build_search_message_obj_list(raw_data) -> List[SearchMessage]:
        raw_messages = raw_data.get("messages", [])
        return [
            SumoLogicParser.build_search_message_obj(raw_message.get("map"))
            for raw_message in raw_messages
        ]

    @staticmethod
    def build_search_message_obj(raw_message) -> SearchMessage:
        return SearchMessage(
            raw_data=raw_message,
            message_time=raw_message.get("_messagetime"),
            block_id=raw_message.get("_blockid"),
            raw=raw_message.get("_raw"),
            source_id=raw_message.get("_sourceid"),
            message_count=raw_message.get("_messagecount"),
            collector=raw_message.get("_collector"),
            message_id=raw_message.get("_messageid"),
            receipt_time=raw_message.get("_receipttime"),
            source=raw_message.get("_source"),
            source_category=raw_message.get("_sourcecategory"),
        )
