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
class ActiveDirectoryCommon:
    def __init__(self, siemplify_logger):
        self.siemplify_logger = siemplify_logger

    def process_custom_query_fields(self, custom_query_fields):
        """
        Process custom fields provided in action call
        :param custom_query_fields: {str}
        :return: {list} comma separated list of custom fields
        """
        result = []
        if not custom_query_fields:
            return result
        try:
            result = [field.strip() for field in custom_query_fields.split(",")]
        except Exception as e:
            self.siemplify_logger.error(
                f"Unable to process custom query fields:{custom_query_fields}"
            )
            self.siemplify_logger.exception(e)
        return result
