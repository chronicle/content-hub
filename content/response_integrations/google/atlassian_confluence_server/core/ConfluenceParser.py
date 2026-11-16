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

"""Module: [ConfluenceParser] defined parser class."""
from __future__ import annotations

from .datamodels import ChildPages, ListPages, PageByID, PageComments


class ConfluenceParser:
    """Confluence Transformation Layer."""

    @staticmethod
    def build_siemplify_child_object(response_data):
        return ChildPages(raw_data=response_data, **response_data)

    @staticmethod
    def build_siemplify_list_object(response_data):
        return ListPages(raw_data=response_data, **response_data)

    @staticmethod
    def build_siemplify_comment_object(response_data):
        return PageComments(raw_data=response_data, **response_data)

    @staticmethod
    def build_siemplify_page_object(response_data):
        return PageByID(raw_data=response_data, **response_data)

    @staticmethod
    def get_next_cursor(raw_json):
        return raw_json.get("_links", {}).get("next")

    def extract_error_message(self, error_json):
        default_error_msg = "Error message is not available"
        msgs = error_json.get("messages")
        if msgs and isinstance(msgs, list):
            return msgs[0].get("text", default_error_msg)
        msg = error_json.get("message")

        if msg and isinstance(msg, str):
            return msg

        return default_error_msg
