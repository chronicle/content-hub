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
from .datamodels import *


class ServiceDeskPlusV3Parser:

    def build_universal_object(self, raw_data):

        return APIResponse(raw_data=raw_data)

    def build_note_object(self, raw_data):

        return Note(
            raw_data=raw_data,
            notes=raw_data.get("notes"),
            note_ids=[note_data.get("id") for note_data in raw_data.get("notes", [])],
        )

    def build_request_object(self, raw_data):

        return Request(
            raw_data=raw_data,
            status=raw_data.get("request", {}).get("status", {}).get("name"),
            orig_request=raw_data.get("request", {}),
        )
